/**
 * PromoClip Fly.io FFmpeg Server
 * Version: 1.0.1 — Split from subwhisper-ffmpeg (2026-04-11)
 *            v1.0.1 — Preserve aspect ratio for non-9:16 clip images (letterbox + static zoom)
 *            v1.0.2 — Asymmetric ratio tolerance [0.394, 0.619] to accept modern smartphones (19.5:9, 20:9, 21:9)
 *            v1.0.3 — Retrait -shortest dans mix audio /promo-assembly (fixait la truncation video a la duree TTS court)
 *            v1.0.4 — Xfade Pro timeout 60s -> 180s (crash sur full re-encode intro+main+outro avec avatar)
 *            v1.0.5 — Symmetric tpad: freeze avatar last frame when recording > avatar (vstack stall fix)
 *            v1.0.6 — Hero intro timeouts 60s → 120-180s (shared-cpu too slow for re-encode)
 *            v1.0.7 — Main trim: stream copy (cut only, no re-encode needed — instant vs 3min)
 *            v1.0.8 — Hero intro pipeline: fps=30 norm + concat -c copy + ultrafast intro build
 *            v1.0.9 — force_key_frames at intro cut point (eliminates frame skip at intro→split transition)
 *            v1.0.10 — Fix outro truncated: remove fps=30 normalization on main video in xfade
 *
 * Heberge UNIQUEMENT /health + /promo-assembly + /promo-assembly-pro.
 * Le reste des routes (slideshow, merge, ken-burns, smart-zoom, etc) reste
 * dans subwhisper-ffmpeg pour ne pas casser les workflows n8n existants.
 *
 * But du split : isoler les deploys PromoClip des jobs Whisper longue duree
 * de SubWhisper (chaque fly deploy recycle les machines -> tuait des jobs).
 *
 * Differences avec subwhisper-ffmpeg/server.js :
 *  - Pas de volume persistant (aucun /data, pas de HLS)
 *  - Pas de cleanupOrphanDirs HLS
 *  - requireAnySecret DURCI : pas de fallback dev mode (401 si secrets absents)
 *  - TMP_JOB_PREFIXES limite a ['pa-', 'pro-']
 *  - Pas de routes /deepgram, /extract, /slideshow, /merge, /resize, /slideshow-pip,
 *    /extract-frames, /ken-burns, /smart-zoom, /speed-ramp, /gemini-upload, /hls2mp4*,
 *    /webproxy
 */

'use strict';

const express = require('express');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const PORT = parseInt(process.env.PORT || '3000', 10);
const FLY_SECRET = process.env.FLY_SECRET || '';
const WORKER_SECRET = process.env.WORKER_SECRET || '';
const MAX_CONCURRENT_JOBS = parseInt(process.env.MAX_CONCURRENT_JOBS || '2', 10);
const VERSION = '1.0.10';

// ---------------------------------------------------------------------------
// Etat global
// ---------------------------------------------------------------------------

let activeJobs = 0;
const startTime = Date.now();

// ---------------------------------------------------------------------------
// Auto-shutdown : eteindre la machine apres IDLE_SHUTDOWN_MS sans jobs actifs.
// Necessaire car auto_stop_machines = "off" (empeche Fly.io de tuer les jobs).
// Fly redemarrera la machine a la prochaine requete (auto_start_machines=true).
// ---------------------------------------------------------------------------
const IDLE_SHUTDOWN_MS = 30 * 60 * 1000; // 30 minutes
let idleTimer = null;

function resetIdleTimer() {
  if (idleTimer) clearTimeout(idleTimer);
  if (activeJobs > 0) return;
  idleTimer = setTimeout(() => {
    if (activeJobs === 0) {
      console.log(`[AUTO-SHUTDOWN] Aucun job depuis ${IDLE_SHUTDOWN_MS / 60000}min — arret du serveur.`);
      process.exit(0);
    }
  }, IDLE_SHUTDOWN_MS);
}
resetIdleTimer();

// ---------------------------------------------------------------------------
// Auto-cleanup des tmpDir orphelins (jobs crashes, streams coupes, timeouts)
// Scanne os.tmpdir() + /app/tmp pour les prefixes PromoClip et supprime
// ceux dont la modification time est > MAX_AGE.
// ---------------------------------------------------------------------------
const TMP_JOB_PREFIXES = ['pa-', 'pro-'];
const TMP_MAX_AGE_MS = 30 * 60 * 1000;

function cleanupOrphanTmpDirs() {
  const bases = [];
  const prodTmp = '/app/tmp';
  if (fs.existsSync(prodTmp)) bases.push(prodTmp);
  try {
    const sysT = os.tmpdir();
    if (sysT && sysT !== prodTmp && fs.existsSync(sysT)) bases.push(sysT);
  } catch (_) {}

  const now = Date.now();
  let totalCleaned = 0;
  let totalBytes = 0;

  for (const base of bases) {
    let entries;
    try { entries = fs.readdirSync(base); } catch (_) { continue; }
    for (const entry of entries) {
      if (!TMP_JOB_PREFIXES.some(p => entry.startsWith(p))) continue;
      const fullPath = path.join(base, entry);
      try {
        const stats = fs.statSync(fullPath);
        if (!stats.isDirectory()) continue;
        const age = now - stats.mtimeMs;
        if (age < TMP_MAX_AGE_MS) continue;
        let size = 0;
        try {
          const walk = (p) => {
            const st = fs.statSync(p);
            if (st.isDirectory()) {
              for (const f of fs.readdirSync(p)) walk(path.join(p, f));
            } else {
              size += st.size;
            }
          };
          walk(fullPath);
        } catch (_) {}
        fs.rmSync(fullPath, { recursive: true, force: true });
        totalCleaned++;
        totalBytes += size;
      } catch (_) {}
    }
  }

  if (totalCleaned > 0) {
    console.log(`[TMP-CLEANUP] ${totalCleaned} dossier(s) orphelin(s) > 30min nettoye(s) (${(totalBytes / 1048576).toFixed(1)} MB liberes)`);
  }
}

cleanupOrphanTmpDirs();
setInterval(cleanupOrphanTmpDirs, 15 * 60 * 1000);

// ---------------------------------------------------------------------------
// App Express
// ---------------------------------------------------------------------------

const app = express();

// CORS global — AVANT toutes les routes
app.use((req, res, next) => {
  res.set({
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS, DELETE',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  });
  if (req.method === 'OPTIONS') return res.status(204).end();
  next();
});

// IMPORTANT : pas de parser JSON global — on met un parser par route pour avoir
// des limits differentes. Bug existant dans subwhisper-ffmpeg : un app.use(json({limit:'50mb'}))
// global ecrasait le route-level 200mb de /promo-assembly-pro (consommait le body avant
// que le middleware route-specific puisse agir). Corrige ici dans la nouvelle app.
const jsonSmall = express.json({ limit: '50mb' });
const jsonLarge = express.json({ limit: '200mb' });

// Auth middleware : accepte FLY_SECRET ou WORKER_SECRET (header Authorization: Bearer X ou query ?s=X)
// DURCI vs subwhisper-ffmpeg : pas de fallback dev mode. Si aucun secret configure,
// on REFUSE toutes les requetes (500) pour eviter une exposition publique accidentelle.
function requireAnySecret(req, res, next) {
  const flySecret = process.env.FLY_SECRET || '';
  const workerSecret = process.env.WORKER_SECRET || '';
  if (!flySecret && !workerSecret) {
    console.error('[AUTH] Aucun secret configure — refus de toutes les requetes');
    return res.status(500).json({ error: 'Server misconfigured: no secret set' });
  }
  const auth = req.headers['authorization'] || '';
  const token = auth.startsWith('Bearer ') ? auth.slice(7) : (req.query.s || '');
  if (!token) return res.status(401).json({ error: 'Missing Authorization' });
  if ((flySecret && token === flySecret) || (workerSecret && token === workerSecret)) return next();
  return res.status(401).json({ error: 'Unauthorized' });
}

// ---------------------------------------------------------------------------
// GET /health
// ---------------------------------------------------------------------------

app.get('/health', (req, res) => {
  res.json({
    ok: true,
    app: 'promoclip-ffmpeg',
    activeJobs,
    uptime: Math.floor((Date.now() - startTime) / 1000),
    maxConcurrentJobs: MAX_CONCURRENT_JOBS,
    version: VERSION
  });
});

// ---------------------------------------------------------------------------
// POST /promo-assembly — Assemble captures + audio + avatar + subtitles en MP4
// ---------------------------------------------------------------------------

app.post('/promo-assembly', jsonSmall, requireAnySecret, async (req, res) => {
  const {
    clips, audio, music, subtitles,
    hookText, ctaText,
    avatarUrl, avatarVideo, avatarMode, avatarPosition,
    width = 1080, height = 1920,
    musicVolume = 0.3
  } = req.body;

  if (!clips || !Array.isArray(clips) || clips.length === 0) {
    return res.status(400).json({ error: 'clips required: [{image, bbox?, effect?, duration?}]' });
  }

  const jobId = `pa-${Date.now().toString(36)}`;
  const tmpDir = path.join(os.tmpdir(), jobId);

  console.log(`[${jobId}] Promo-assembly: ${clips.length} clips, audio=${!!audio}, music=${!!music}, subs=${!!subtitles}`);

  let jobCounted = false;
  try {
    fs.mkdirSync(tmpDir, { recursive: true });
    activeJobs++;
    jobCounted = true;
    resetIdleTimer();

    // 1. Write all clip images to disk
    const clipPaths = [];
    for (let i = 0; i < clips.length; i++) {
      const clipPath = path.join(tmpDir, `clip-${i}.png`);
      fs.writeFileSync(clipPath, Buffer.from(clips[i].image, 'base64'));
      clipPaths.push(clipPath);
    }

    // 2. Generate individual clip videos (ken-burns or smart-zoom)
    // Aspect ratio handling (asymmetric tolerance):
    //   - Accepts native smartphone ratios (9:16, 19.5:9, 20:9, 21:9) for full cover + ken-burns
    //   - Letterboxes images that are WIDER than 9:16+10% (true landscape, square, 4:3, 4:5)
    //   - Also letterboxes images that are MUCH TALLER than 9:16 (very elongated screenshots)
    //   - Letterbox uses a STATIC zoompan to avoid revealing the padded bars while zooming
    const TARGET_RATIO = width / height; // 1080/1920 = 0.5625
    const RATIO_MAX = TARGET_RATIO * 1.10; // 0.619 — anything wider is letterboxed
    const RATIO_MIN = TARGET_RATIO * 0.70; // 0.394 — anything narrower is letterboxed
    // Accepted range [0.394, 0.619] → 9:16, 19.5:9, 20:9, 21:9 all pass as native
    const clipVideos = [];
    for (let i = 0; i < clips.length; i++) {
      const clip = clips[i];
      const dur = Math.min(10, Math.max(1, clip.duration || 4));
      const fps = 15;
      const d = Math.round(fps * dur);
      const clipOutPath = path.join(tmpDir, `clip-${i}.mp4`);

      // Decide whether this clip needs letterboxing based on its original aspect ratio.
      // If the client provided width+height, compare to the target (9:16). Otherwise assume native.
      let needsLetterbox = false;
      if (clip.width > 0 && clip.height > 0) {
        const srcRatio = clip.width / clip.height;
        needsLetterbox = (srcRatio > RATIO_MAX) || (srcRatio < RATIO_MIN);
      }

      let zoompanFilter;
      const effect = clip.effect || 'zoom_in';
      // When letterboxing, force a STATIC zoompan regardless of user effect,
      // otherwise the zoom would reveal the dark padding bars during animation.
      const effectiveEffect = needsLetterbox ? 'none' : effect;

      if (effectiveEffect === 'none') {
        zoompanFilter = `zoompan=z=1:d=${d}:x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s=${width}x${height}:fps=${fps}`;
      } else if (effectiveEffect === 'subtle') {
        zoompanFilter = `zoompan=z='min(zoom+0.0003,1.05)':d=${d}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${width}x${height}:fps=${fps}`;
      } else if (clip.bbox && clip.bbox.x1 != null) {
        const cx = ((clip.bbox.x1 + clip.bbox.x2) / 2) / 1000;
        const cy = ((clip.bbox.y1 + clip.bbox.y2) / 2) / 1000;
        const bboxW = Math.abs(clip.bbox.x2 - clip.bbox.x1) / 1000;
        const bboxH = Math.abs(clip.bbox.y2 - clip.bbox.y1) / 1000;
        const zoomTarget = Math.min(3.0, Math.max(1.3, 1 / Math.max(bboxW, bboxH)));
        zoompanFilter = `zoompan=z='min(zoom+${((zoomTarget - 1) / d).toFixed(6)},${zoomTarget.toFixed(2)})':d=${d}:x='${cx}*iw-iw/zoom/2':y='${cy}*ih-ih/zoom/2':s=${width}x${height}:fps=${fps}`;
      } else {
        switch (effectiveEffect) {
          case 'zoom_out':
            zoompanFilter = `zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.001))':d=${d}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${width}x${height}:fps=${fps}`;
            break;
          case 'pan_down':
            zoompanFilter = `zoompan=z=1.3:d=${d}:x='(iw-iw/zoom)/2':y='min((ih-ih/zoom),on*2)':s=${width}x${height}:fps=${fps}`;
            break;
          case 'pan_right':
            zoompanFilter = `zoompan=z=1.2:d=${d}:x='min(on*3,(iw-iw/zoom))':y='(ih-ih/zoom)/2':s=${width}x${height}:fps=${fps}`;
            break;
          default: // zoom_in
            zoompanFilter = `zoompan=z='min(zoom+0.001,1.5)':d=${d}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${width}x${height}:fps=${fps}`;
        }
      }

      // Pre-filter: letterbox (contain) for non-9:16 images, legacy cover for native.
      // - Letterbox: scale-fit to target + pad dark to preserve aspect ratio (no stretch, no crop)
      // - Cover: scale width 2000 (legacy) → zoompan fills canvas by cropping (fine for 9:16)
      const preFilter = needsLetterbox
        ? `scale=${width}:${height}:force_original_aspect_ratio=decrease,pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1`
        : `scale=2000:-1`;

      if (needsLetterbox) {
        console.log(`[${jobId}] Clip ${i}: letterbox (src ${clip.width}x${clip.height}, ratio ${(clip.width / clip.height).toFixed(3)} vs target ${TARGET_RATIO.toFixed(3)})`);
      }

      const ffArgs = [
        '-loop', '1',
        '-i', clipPaths[i],
        '-vf', `${preFilter},${zoompanFilter}`,
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
        '-pix_fmt', 'yuv420p',
        '-t', String(dur),
        '-y', clipOutPath
      ];

      await new Promise((resolve, reject) => {
        const ff = spawn('ffmpeg', ffArgs, { stdio: ['ignore', 'pipe', 'pipe'] });
        let stderr = '';
        ff.stderr.on('data', d => { stderr += d.toString(); });
        ff.on('close', code => {
          if (code === 0) resolve();
          else reject(new Error(`FFmpeg clip ${i} exit ${code}: ${stderr.slice(-300)}`));
        });
        ff.on('error', reject);
        setTimeout(() => {
          try { ff.kill('SIGKILL'); } catch (_) {}
          reject(new Error(`FFmpeg clip ${i} timeout 60s`));
        }, 60000);
      });

      clipVideos.push(clipOutPath);
      console.log(`[${jobId}] Clip ${i}/${clips.length - 1} OK`);
    }

    // 3. Concat clips with xfade transitions (0.3s fade between each)
    const concatOut = path.join(tmpDir, 'concat.mp4');
    const XFADE_DUR = 0.3;

    if (clipVideos.length === 1) {
      fs.renameSync(clipVideos[0], concatOut);
    } else {
      const xfadeInputs = clipVideos.map((p, i) => ['-i', p]).flat();
      const xfadeFilters = [];
      let prevLabel = '[0:v]';
      for (let i = 1; i < clipVideos.length; i++) {
        let offset = 0;
        for (let j = 0; j < i; j++) {
          offset += Math.min(10, Math.max(1, (clips[j] && clips[j].duration) || 4));
        }
        offset -= i * XFADE_DUR;
        const outLabel = i < clipVideos.length - 1 ? `[x${i}]` : '[outv]';
        xfadeFilters.push(`${prevLabel}[${i}:v]xfade=transition=fade:duration=${XFADE_DUR}:offset=${Math.max(0, offset).toFixed(2)}${outLabel}`);
        prevLabel = outLabel;
      }

      const xfadeArgs = [
        ...xfadeInputs,
        '-filter_complex', xfadeFilters.join(';'),
        '-map', '[outv]',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        '-y', concatOut
      ];

      await new Promise((resolve, reject) => {
        const ff = spawn('ffmpeg', xfadeArgs, { stdio: ['ignore', 'pipe', 'pipe'] });
        let stderr = '';
        ff.stderr.on('data', d => { stderr += d.toString(); });
        ff.on('close', code => {
          if (code === 0) resolve();
          else reject(new Error(`FFmpeg xfade exit ${code}: ${stderr.slice(-500)}`));
        });
        ff.on('error', reject);
        setTimeout(() => {
          try { ff.kill('SIGKILL'); } catch (_) {}
          reject(new Error('FFmpeg xfade timeout 60s'));
        }, 60000);
      });
    }

    console.log(`[${jobId}] Concat+xfade OK`);

    // Avatar overlay (optional)
    let videoForMix = concatOut;
    if (avatarVideo || avatarUrl) {
      const avatarPath = path.join(tmpDir, 'avatar.mp4');
      if (avatarVideo) {
        fs.writeFileSync(avatarPath, Buffer.from(avatarVideo, 'base64'));
      } else if (avatarUrl) {
        await new Promise((resolve, reject) => {
          const file = fs.createWriteStream(avatarPath);
          const proto = avatarUrl.startsWith('https') ? require('https') : require('http');
          proto.get(avatarUrl, (response) => {
            if (response.statusCode === 301 || response.statusCode === 302) {
              proto.get(response.headers.location, (r2) => { r2.pipe(file); file.on('finish', () => { file.close(); resolve(); }); }).on('error', reject);
            } else {
              response.pipe(file);
              file.on('finish', () => { file.close(); resolve(); });
            }
          }).on('error', reject);
        });
      }

      const mode = avatarMode || 'bubble';
      const avatarOutPath = path.join(tmpDir, 'with-avatar.mp4');
      console.log(`[${jobId}] Avatar: mode=${mode}, has avatar=${!!(avatarVideo||avatarUrl)}`);

      if (mode === 'bubble') {
        const pipPx = Math.round(height * 0.25);
        const margin = Math.round(height * 0.03);
        const pos = avatarPosition || 'bottom-right';
        let pipX, pipY;
        if (pos === 'bottom-right') { pipX = `W-${pipPx}-${margin}`; pipY = `H-${pipPx}-${margin}`; }
        else if (pos === 'bottom-left') { pipX = `${margin}`; pipY = `H-${pipPx}-${margin}`; }
        else { pipX = `W-${pipPx}-${margin}`; pipY = `H-${pipPx}-${margin}`; }

        const circleFilter = `[1:v]scale=${pipPx}:${pipPx}:force_original_aspect_ratio=decrease,pad=${pipPx}:${pipPx}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuva420p,geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':a='if(gt(pow(X-${pipPx}/2,2)+pow(Y-${pipPx}/2,2),pow(${pipPx}/2-4,2)),0,255)'[pip];[0:v][pip]overlay=${pipX}:${pipY}:shortest=1[outv]`;

        const ffArgs = [
          '-i', videoForMix,
          '-i', avatarPath,
          '-filter_complex', circleFilter,
          '-map', '[outv]',
          '-map', '1:a?',
          '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
          '-c:a', 'aac', '-b:a', '128k',
          '-pix_fmt', 'yuv420p',
          '-y', avatarOutPath
        ];

        await new Promise((resolve, reject) => {
          const ff = spawn('ffmpeg', ffArgs, { stdio: ['ignore', 'pipe', 'pipe'] });
          let stderr = '';
          ff.stderr.on('data', d => { stderr += d.toString(); });
          ff.on('close', code => {
            if (code === 0) resolve();
            else reject(new Error(`FFmpeg avatar-pip exit ${code}: ${stderr.slice(-300)}`));
          });
          ff.on('error', reject);
          setTimeout(() => {
            try { ff.kill('SIGKILL'); } catch (_) {}
            reject(new Error('FFmpeg avatar-pip timeout 120s'));
          }, 120000);
        });

        console.log(`[${jobId}] Avatar bubble overlay done`);

      } else if (mode === 'split-top' || mode === 'split-bottom') {
        const halfH = Math.round(height / 2);
        let filterComplex;
        if (mode === 'split-top') {
          filterComplex = `[1:v]scale=${width}:${halfH}:force_original_aspect_ratio=increase,crop=${width}:${halfH}:0:(ih-${halfH})*0.30,setsar=1[av];[0:v]scale=${width}:${halfH}:force_original_aspect_ratio=increase,crop=${width}:${halfH},setsar=1[cl];[av][cl]vstack=inputs=2[outv]`;
        } else {
          filterComplex = `[0:v]scale=${width}:${halfH}:force_original_aspect_ratio=increase,crop=${width}:${halfH},setsar=1[cl];[1:v]scale=${width}:${halfH}:force_original_aspect_ratio=increase,crop=${width}:${halfH}:0:(ih-${halfH})*0.30,setsar=1[av];[cl][av]vstack=inputs=2[outv]`;
        }

        const ffArgs = [
          '-i', videoForMix,
          '-i', avatarPath,
          '-filter_complex', filterComplex,
          '-map', '[outv]',
          '-map', '1:a?',
          '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
          '-c:a', 'aac', '-b:a', '128k',
          '-pix_fmt', 'yuv420p',
          '-t', String(Math.min(30, clips.length * 10)),
          '-y', avatarOutPath
        ];

        await new Promise((resolve, reject) => {
          const ff = spawn('ffmpeg', ffArgs, { stdio: ['ignore', 'pipe', 'pipe'] });
          let stderr = '';
          ff.stderr.on('data', d => { stderr += d.toString(); });
          ff.on('close', code => {
            if (code === 0) resolve();
            else reject(new Error(`FFmpeg avatar-split exit ${code}: ${stderr.slice(-300)}`));
          });
          ff.on('error', reject);
          setTimeout(() => {
            try { ff.kill('SIGKILL'); } catch (_) {}
            reject(new Error('FFmpeg avatar-split timeout 120s'));
          }, 120000);
        });

        console.log(`[${jobId}] Avatar split (${mode}) done`);
      }

      if (fs.existsSync(avatarOutPath)) {
        videoForMix = avatarOutPath;
      }
    }

    // 5. Mix audio layers (voiceover + music) if provided
    let finalOut = videoForMix;

    if (audio || music) {
      finalOut = path.join(tmpDir, 'final.mp4');
      const mixArgs = ['-i', videoForMix];

      if (audio) {
        const audioPath = path.join(tmpDir, 'voice.mp3');
        fs.writeFileSync(audioPath, Buffer.from(audio, 'base64'));
        mixArgs.push('-i', audioPath);
      }
      if (music) {
        const musicPath = path.join(tmpDir, 'music.mp3');
        fs.writeFileSync(musicPath, Buffer.from(music, 'base64'));
        mixArgs.push('-i', musicPath);
      }

      let filterComplex = '';
      let audioInputIdx = 1;

      if (audio && music) {
        filterComplex = `[${audioInputIdx}:a]aformat=fltp:44100:stereo[voice]; [${audioInputIdx + 1}:a]aformat=fltp:44100:stereo,volume=${musicVolume}[mus]; [voice][mus]amix=inputs=2:duration=longest[aout]`;
        mixArgs.push('-filter_complex', filterComplex, '-map', '0:v', '-map', '[aout]');
      } else if (audio) {
        mixArgs.push('-map', '0:v', '-map', `${audioInputIdx}:a`);
      } else if (music) {
        filterComplex = `[${audioInputIdx}:a]volume=${musicVolume}[aout]`;
        mixArgs.push('-filter_complex', filterComplex, '-map', '0:v', '-map', '[aout]');
      }

      // NO -shortest: we want the video to keep its full concat duration even if the
      // voiceover finishes earlier. The client-side design says "small silence at the
      // end is OK" (cf wordsTargetForDuration comment) but -shortest was contradicting it
      // by truncating the whole MP4 to the audio length. FFmpeg falls back to the longest
      // stream when -shortest is absent, producing a valid MP4 with trailing silence.
      mixArgs.push(
        '-c:v', 'copy',
        '-c:a', 'aac', '-b:a', '256k',
        '-movflags', '+faststart',
        '-y', finalOut
      );

      await new Promise((resolve, reject) => {
        const ff = spawn('ffmpeg', mixArgs, { stdio: ['ignore', 'pipe', 'pipe'] });
        let stderr = '';
        ff.stderr.on('data', d => { stderr += d.toString(); });
        ff.on('close', code => {
          if (code === 0) resolve();
          else reject(new Error(`FFmpeg mix exit ${code}: ${stderr.slice(-500)}`));
        });
        ff.on('error', reject);
        setTimeout(() => {
          try { ff.kill('SIGKILL'); } catch (_) {}
          reject(new Error('FFmpeg audio mix timeout 60s'));
        }, 60000);
      });

      console.log(`[${jobId}] Audio mix OK`);
    }

    // 6. Add subtitles if provided
    if (subtitles) {
      const subsPath = path.join(tmpDir, 'subs.ass');
      fs.writeFileSync(subsPath, subtitles);
      const subsOut = path.join(tmpDir, 'final-subs.mp4');

      const subsArgs = [
        '-i', finalOut,
        '-vf', `ass=${subsPath}`,
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '20',
        '-c:a', 'copy',
        '-movflags', '+faststart',
        '-y', subsOut
      ];

      await new Promise((resolve, reject) => {
        const ff = spawn('ffmpeg', subsArgs, { stdio: ['ignore', 'pipe', 'pipe'] });
        let stderr = '';
        ff.stderr.on('data', d => { stderr += d.toString(); });
        ff.on('close', code => {
          if (code === 0) resolve();
          else reject(new Error(`FFmpeg subs exit ${code}: ${stderr.slice(-500)}`));
        });
        ff.on('error', reject);
        setTimeout(() => {
          try { ff.kill('SIGKILL'); } catch (_) {}
          reject(new Error('FFmpeg subs timeout 120s'));
        }, 120000);
      });

      finalOut = subsOut;
      console.log(`[${jobId}] Subtitles OK`);
    }

    const mp4Stat = fs.statSync(finalOut);
    console.log(`[${jobId}] Promo-assembly COMPLETE: ${(mp4Stat.size / 1048576).toFixed(1)} MB, ${clips.length} clips`);

    res.setHeader('Content-Type', 'video/mp4');
    res.setHeader('Content-Length', mp4Stat.size);
    res.setHeader('Content-Disposition', `attachment; filename="promo-${jobId}.mp4"`);

    const stream = fs.createReadStream(finalOut);
    stream.pipe(res);
    stream.on('end', () => {
      try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    });
    stream.on('error', err => {
      console.error(`[${jobId}] Stream error:`, err.message);
      try { res.end(); } catch (_) {}
      try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    });

  } catch (err) {
    console.error(`[${jobId}] Promo-assembly error:`, err.message);
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    if (!res.headersSent) {
      res.status(500).json({ error: err.message });
    }
  } finally {
    if (jobCounted) {
      activeJobs--;
      resetIdleTimer();
    }
  }
});

// ---------------------------------------------------------------------------
// POST /promo-assembly-pro — Mode Pro : screen recording + avatar split-screen
// ---------------------------------------------------------------------------
app.post('/promo-assembly-pro', jsonLarge, requireAnySecret, async (req, res) => {
  const jobId = `pro-${Date.now().toString(36)}`;
  console.log(`[${jobId}] /promo-assembly-pro start`);

  if (activeJobs >= MAX_CONCURRENT_JOBS) {
    return res.status(503).json({ error: 'Server busy, try again later' });
  }

  const { video, videoMime, moments, avatarVideo, avatarMode, subtitles, width, height, outroClip, outroDuration, avatarIntroFullscreen, avatarIntroDuration } = req.body;
  if (!video) return res.status(400).json({ error: 'Missing video (base64)' });

  const tmpDir = path.join(os.tmpdir(), jobId);

  let jobCounted = false;
  try {
    fs.mkdirSync(tmpDir, { recursive: true });
    activeJobs++;
    jobCounted = true;
    resetIdleTimer();

    const outWidth = width || 1080;
    const outHeight = height || 1920;

    // 1. Write screen recording to disk
    const ext = (videoMime || 'video/mp4').includes('webm') ? 'webm' : 'mp4';
    const recordingPath = path.join(tmpDir, `recording.${ext}`);
    fs.writeFileSync(recordingPath, Buffer.from(video, 'base64'));
    console.log(`[${jobId}] Recording: ${(fs.statSync(recordingPath).size / 1048576).toFixed(1)} MB`);

    // 2. Get recording duration via ffprobe
    const probeDur = await new Promise((resolve, reject) => {
      const ff = spawn('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', recordingPath], { stdio: ['ignore', 'pipe', 'pipe'] });
      let out = '';
      ff.stdout.on('data', d => { out += d.toString(); });
      ff.on('close', code => {
        if (code === 0) resolve(parseFloat(out.trim()) || 30);
        else resolve(30);
      });
      ff.on('error', () => resolve(30));
      setTimeout(() => { try { ff.kill(); } catch(_){} resolve(30); }, 10000);
    });
    console.log(`[${jobId}] Recording duration: ${probeDur.toFixed(1)}s`);

    // 3. Write avatar video if provided + probe its duration
    let avatarPath = null;
    let avatarDur = 0;
    if (avatarVideo) {
      avatarPath = path.join(tmpDir, 'avatar.mp4');
      fs.writeFileSync(avatarPath, Buffer.from(avatarVideo, 'base64'));
      console.log(`[${jobId}] Avatar: ${(fs.statSync(avatarPath).size / 1048576).toFixed(1)} MB`);
      avatarDur = await new Promise((resolve) => {
        const ff = spawn('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', avatarPath], { stdio: ['ignore', 'pipe', 'pipe'] });
        let out = '';
        ff.stdout.on('data', d => { out += d.toString(); });
        ff.on('close', code => {
          if (code === 0) resolve(parseFloat(out.trim()) || 0);
          else resolve(0);
        });
        ff.on('error', () => resolve(0));
        setTimeout(() => { try { ff.kill(); } catch(_){} resolve(0); }, 5000);
      });
      console.log(`[${jobId}] Avatar duration: ${avatarDur.toFixed(2)}s (recording: ${probeDur.toFixed(2)}s)`);
    }

    // Computed max duration for the main video assembly
    const maxMainDur = Math.min(60, Math.max(probeDur, avatarDur || probeDur));
    // Symmetric tpad: freeze last frame of whichever stream is shorter
    // so that vstack/overlay always has both inputs for the full duration
    const needsFreezeRecord = avatarDur > probeDur + 0.1;
    const freezeRecordExtra = needsFreezeRecord ? (avatarDur - probeDur) : 0;
    const needsFreezeAvatar = avatarDur > 0 && probeDur > avatarDur + 0.1;
    const freezeAvatarExtra = needsFreezeAvatar ? (Math.min(probeDur, 60) - avatarDur) : 0;
    if (needsFreezeRecord) {
      console.log(`[${jobId}] Freeze last frame of RECORDING for ${freezeRecordExtra.toFixed(2)}s (avatar outlasts recording)`);
    }
    if (needsFreezeAvatar) {
      console.log(`[${jobId}] Freeze last frame of AVATAR for ${freezeAvatarExtra.toFixed(2)}s (recording outlasts avatar)`);
    }

    // 4. Build FFmpeg command for split-screen assembly
    const mode = avatarMode || 'split-top';
    const outputPath = path.join(tmpDir, 'output.mp4');
    let ffArgs;

    // Write subtitles file ONCE at job level — reused by both main assembly AND hero intro
    let subPath = null;
    if (subtitles) {
      subPath = path.join(tmpDir, 'subs.ass');
      fs.writeFileSync(subPath, subtitles, 'utf8');
    }

    if (avatarPath) {
      const recordPrefilter = needsFreezeRecord
        ? `tpad=stop_mode=clone:stop_duration=${freezeRecordExtra.toFixed(2)},`
        : '';
      const avatarPrefilter = needsFreezeAvatar
        ? `tpad=stop_mode=clone:stop_duration=${freezeAvatarExtra.toFixed(2)},`
        : '';
      // Normalize fps to 30 when hero intro is enabled — required for -c copy concat later
      // (intro-fs.mp4 is encoded at fps=30, output.mp4 must match exactly)
      const fpsNorm = avatarIntroFullscreen ? ',fps=30' : '';
      let filterComplex;
      if (mode === 'split-top') {
        const avatarH = Math.round(outHeight * 0.3);
        const recordH = outHeight - avatarH;
        filterComplex = [
          `[0:v]${avatarPrefilter}scale=${outWidth}:${avatarH}:force_original_aspect_ratio=increase,crop=${outWidth}:${avatarH}:0:(ih-${avatarH})*0.30,setsar=1${fpsNorm}[avatar]`,
          `[1:v]${recordPrefilter}scale=${outWidth}:${recordH}:force_original_aspect_ratio=decrease,pad=${outWidth}:${recordH}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1${fpsNorm}[record]`,
          `[avatar][record]vstack=inputs=2[outv]`
        ].join(';');
      } else if (mode === 'split-bottom') {
        const avatarH = Math.round(outHeight * 0.3);
        const recordH = outHeight - avatarH;
        filterComplex = [
          `[1:v]${recordPrefilter}scale=${outWidth}:${recordH}:force_original_aspect_ratio=decrease,pad=${outWidth}:${recordH}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1${fpsNorm}[record]`,
          `[0:v]${avatarPrefilter}scale=${outWidth}:${avatarH}:force_original_aspect_ratio=increase,crop=${outWidth}:${avatarH}:0:(ih-${avatarH})*0.30,setsar=1${fpsNorm}[avatar]`,
          `[record][avatar]vstack=inputs=2[outv]`
        ].join(';');
      } else {
        const pipSize = Math.round(outWidth * 0.28);
        const pipX = outWidth - pipSize - 20;
        const pipY = outHeight - pipSize - 120;
        filterComplex = [
          `[1:v]${recordPrefilter}scale=${outWidth}:${outHeight}:force_original_aspect_ratio=decrease,pad=${outWidth}:${outHeight}:(ow-iw)/2:(oh-ih)/2,setsar=1${fpsNorm}[record]`,
          `[0:v]${avatarPrefilter}scale=${pipSize}:${pipSize}:force_original_aspect_ratio=decrease,pad=${pipSize}:${pipSize}:(ow-iw)/2:(oh-ih)/2,setsar=1${fpsNorm},format=yuva420p,geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':a='if(gt(pow(X-${pipSize}/2,2)+pow(Y-${pipSize}/2,2),pow(${pipSize}/2-4,2)),0,255)'[pip]`,
          `[record][pip]overlay=${pipX}:${pipY}[outv]`
        ].join(';');
      }

      const subFilter = subPath ? `,ass=${subPath}` : '';

      ffArgs = [
        '-i', avatarPath,
        '-i', recordingPath,
        '-filter_complex', filterComplex + (subFilter ? `;[outv]${subFilter.slice(1)}[final]` : ''),
        '-map', subFilter ? '[final]' : '[outv]',
        '-map', '0:a?',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
        // Force keyframe at exact intro cut point so -c copy trim lands precisely (no frame skip)
        ...(avatarIntroFullscreen ? ['-force_key_frames', String(Math.max(1, Math.min(5, Number(avatarIntroDuration) || 2)))] : []),
        '-c:a', 'aac', '-b:a', '128k', ...(avatarIntroFullscreen ? ['-ar', '44100'] : []),
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        '-t', String(maxMainDur),
        '-y', outputPath
      ];
    } else {
      const subFilter = subPath ? `,ass=${subPath}` : '';
      ffArgs = [
        '-i', recordingPath,
        '-vf', `scale=${outWidth}:${outHeight}:force_original_aspect_ratio=decrease,pad=${outWidth}:${outHeight}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1${subFilter}`,
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        '-t', String(Math.min(probeDur, 60)),
        '-y', outputPath
      ];
    }

    console.log(`[${jobId}] FFmpeg Pro start (mode: ${mode}, avatar: ${!!avatarPath})...`);
    await new Promise((resolve, reject) => {
      const ff = spawn('ffmpeg', ffArgs, { stdio: ['ignore', 'pipe', 'pipe'] });
      let stderr = '';
      ff.stderr.on('data', d => { stderr += d.toString(); });
      ff.on('close', code => {
        if (code === 0) resolve();
        else reject(new Error(`FFmpeg Pro exit ${code}: ${stderr.slice(-500)}`));
      });
      ff.on('error', reject);
      setTimeout(() => {
        try { ff.kill('SIGKILL'); } catch (_) {}
        reject(new Error('FFmpeg Pro timeout 120s'));
      }, 120000);
    });

    // Hero intro avatar fullscreen (optional)
    if (avatarPath && avatarIntroFullscreen) {
      const introDur = Math.max(1, Math.min(5, Number(avatarIntroDuration) || 2));
      const introPath = path.join(tmpDir, 'intro-fs.mp4');
      const mainTrimPath = path.join(tmpDir, 'main-trim.mp4');
      const withIntroPath = path.join(tmpDir, 'with-intro.mp4');

      console.log(`[${jobId}] Hero intro: avatar fullscreen ${introDur}s`);

      const introSubFilter = subPath ? `,ass=${subPath}` : '';
      await new Promise((resolve, reject) => {
        const ff = spawn('ffmpeg', [
          '-t', String(introDur),          // input-level: limit decoding to introDur (skip rest of avatar)
          '-i', avatarPath,
          '-vf', `scale=${outWidth}:${outHeight}:force_original_aspect_ratio=increase,crop=${outWidth}:${outHeight}:(iw-${outWidth})/2:(ih-${outHeight})/2,setsar=1,fps=30,format=yuv420p${introSubFilter}`,
          '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
          '-c:a', 'aac', '-b:a', '128k', '-ar', '44100',
          '-movflags', '+faststart',
          '-y', introPath
        ], { stdio: ['ignore', 'pipe', 'pipe'] });
        let stderr = '';
        ff.stderr.on('data', d => { stderr += d.toString(); });
        ff.on('close', code => code === 0 ? resolve() : reject(new Error('Intro build: ' + stderr.slice(-200))));
        ff.on('error', reject);
        setTimeout(() => { try { ff.kill('SIGKILL'); } catch(_){} reject(new Error('Intro build timeout')); }, 120000);
      });

      await new Promise((resolve, reject) => {
        // Stream copy for trim: output.mp4 is already H264/AAC, no need to re-encode just to cut 2s
        // This is instant vs 3+ min re-encode on shared-cpu
        const ff = spawn('ffmpeg', [
          '-ss', String(introDur),
          '-i', outputPath,
          '-c', 'copy',
          '-fflags', '+genpts',
          '-movflags', '+faststart',
          '-y', mainTrimPath
        ], { stdio: ['ignore', 'pipe', 'pipe'] });
        let stderr = '';
        ff.stderr.on('data', d => { stderr += d.toString(); });
        ff.on('close', code => code === 0 ? resolve() : reject(new Error('Main trim: ' + stderr.slice(-200))));
        ff.on('error', reject);
        setTimeout(() => { try { ff.kill('SIGKILL'); } catch(_){} reject(new Error('Main trim timeout')); }, 60000);
      });

      const concatListPath = path.join(tmpDir, 'concat-intro.txt');
      fs.writeFileSync(concatListPath, `file '${introPath.replace(/'/g, "'\\''")}'\nfile '${mainTrimPath.replace(/'/g, "'\\''")}'\n`);
      console.log(`[${jobId}] Intro concat: -c copy (both segments already H264/AAC@30fps)`);
      await new Promise((resolve, reject) => {
        // Stream copy: both intro-fs.mp4 and main-trim.mp4 are H264/AAC with same params
        // (fps=30 normalized in assembly, same encoder/crf/preset)
        // This takes ~1-2s instead of 180s+ re-encode
        const ff = spawn('ffmpeg', [
          '-f', 'concat', '-safe', '0', '-i', concatListPath,
          '-c', 'copy',
          '-fflags', '+genpts',
          '-avoid_negative_ts', 'make_zero',
          '-movflags', '+faststart',
          '-y', withIntroPath
        ], { stdio: ['ignore', 'pipe', 'pipe'] });
        let stderr = '';
        ff.stderr.on('data', d => { stderr += d.toString(); });
        ff.on('close', code => code === 0 ? resolve() : reject(new Error('Intro concat: ' + stderr.slice(-200))));
        ff.on('error', reject);
        setTimeout(() => { try { ff.kill('SIGKILL'); } catch(_){} reject(new Error('Intro concat timeout')); }, 30000);
      });

      fs.renameSync(withIntroPath, outputPath);
      console.log(`[${jobId}] Hero intro applied`);
    }

    // Outro image assembly (optional)
    if (outroClip) {
      const XFADE_DUR = 0.3;
      const clips = [];

      const actualMainDur = await new Promise((resolve) => {
        const ff = spawn('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', outputPath], { stdio: ['ignore', 'pipe', 'pipe'] });
        let out = '';
        ff.stdout.on('data', d => { out += d.toString(); });
        ff.on('close', code => {
          if (code === 0) resolve(parseFloat(out.trim()) || probeDur);
          else resolve(probeDur);
        });
        ff.on('error', () => resolve(probeDur));
        setTimeout(() => { try { ff.kill(); } catch(_){} resolve(probeDur); }, 5000);
      });
      console.log(`[${jobId}] Main video actual duration: ${actualMainDur.toFixed(2)}s (probeDur was ${probeDur.toFixed(2)}s)`);

      const mainDur = Math.min(actualMainDur, 60);
      clips.push({ path: outputPath, duration: mainDur });

      if (outroClip) {
        const outroImgPath = path.join(tmpDir, 'outro.png');
        fs.writeFileSync(outroImgPath, Buffer.from(outroClip, 'base64'));
        const outroVidPath = path.join(tmpDir, 'outro.mp4');
        const oDur = outroDuration || 3;
        await new Promise((resolve, reject) => {
          const ff = spawn('ffmpeg', [
            '-loop', '1', '-i', outroImgPath,
            '-vf', `scale=${outWidth}:${outHeight}:force_original_aspect_ratio=decrease,pad=${outWidth}:${outHeight}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1,zoompan=z=1:d=${oDur * 15}:x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':s=${outWidth}x${outHeight}:fps=15`,
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-pix_fmt', 'yuv420p',
            '-t', String(oDur), '-y', outroVidPath
          ], { stdio: ['ignore', 'pipe', 'pipe'] });
          let stderr = '';
          ff.stderr.on('data', d => { stderr += d.toString(); });
          ff.on('close', code => code === 0 ? resolve() : reject(new Error('Outro clip: ' + stderr.slice(-200))));
          ff.on('error', reject);
          setTimeout(() => { try { ff.kill('SIGKILL'); } catch(_){} reject(new Error('Outro timeout')); }, 30000);
        });
        clips.push({ path: outroVidPath, duration: oDur });
        console.log(`[${jobId}] Outro clip OK`);
      }

      if (clips.length > 1) {
        const finalPath = path.join(tmpDir, 'final.mp4');
        const xInputs = clips.map(c => ['-i', c.path]).flat();
        const mainIdx = 0;

        // Probe main video frame count to compute duration at normalized 30fps
        // (fps normalization can change effective duration vs file duration)
        const mainFrameCount = await new Promise((resolve) => {
          const ff = spawn('ffprobe', ['-v', 'error', '-count_frames', '-select_streams', 'v:0',
            '-show_entries', 'stream=nb_read_frames', '-of', 'csv=p=0', clips[0].path],
            { stdio: ['ignore', 'pipe', 'pipe'] });
          let out = '';
          ff.stdout.on('data', d => { out += d.toString(); });
          ff.on('close', () => resolve(parseInt(out.trim()) || Math.round(clips[0].duration * 30)));
          ff.on('error', () => resolve(Math.round(clips[0].duration * 30)));
          setTimeout(() => { try { ff.kill(); } catch(_){} resolve(Math.round(clips[0].duration * 30)); }, 10000);
        });
        // Use frame-accurate duration at 30fps for xfade offset calculation
        clips[0].duration = mainFrameCount / 30;
        console.log(`[${jobId}] Main video: ${mainFrameCount} frames → ${clips[0].duration.toFixed(2)}s at 30fps`);

        const normFilters = [];
        for (let i = 0; i < clips.length; i++) {
          normFilters.push(`[${i}:v]scale=${outWidth}:${outHeight}:force_original_aspect_ratio=decrease,pad=${outWidth}:${outHeight}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,fps=30,format=yuv420p,setsar=1[n${i}]`);
        }

        const xFilters = [];
        let prevLabel = '[n0]';
        for (let i = 1; i < clips.length; i++) {
          let offset = 0;
          for (let j = 0; j < i; j++) offset += clips[j].duration;
          offset -= i * XFADE_DUR;
          const outLabel = i < clips.length - 1 ? `[x${i}]` : '[outv]';
          xFilters.push(`${prevLabel}[n${i}]xfade=transition=fade:duration=${XFADE_DUR}:offset=${Math.max(0, offset).toFixed(2)}${outLabel}`);
          prevLabel = outLabel;
        }

        const fullFilter = [...normFilters, ...xFilters].join(';');
        await new Promise((resolve, reject) => {
          const ff = spawn('ffmpeg', [
            ...xInputs,
            '-filter_complex', fullFilter,
            '-map', '[outv]', '-map', `${mainIdx}:a?`,
            '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
            '-c:a', 'aac', '-b:a', '128k', '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart', '-y', finalPath
          ], { stdio: ['ignore', 'pipe', 'pipe'] });
          let stderr = '';
          ff.stderr.on('data', d => { stderr += d.toString(); });
          ff.on('close', code => code === 0 ? resolve() : reject(new Error('Xfade Pro: ' + stderr.slice(-300))));
          ff.on('error', reject);
          setTimeout(() => { try { ff.kill('SIGKILL'); } catch(_){} reject(new Error('Xfade Pro timeout 300s')); }, 300000);
        });
        fs.renameSync(finalPath, outputPath);
        console.log(`[${jobId}] Intro/Outro xfade OK`);
      }
    }

    const mp4Stat = fs.statSync(outputPath);
    console.log(`[${jobId}] Pro output: ${(mp4Stat.size / 1048576).toFixed(1)} MB`);

    res.setHeader('Content-Type', 'video/mp4');
    res.setHeader('Content-Length', mp4Stat.size);
    res.setHeader('Content-Disposition', `attachment; filename="promo-pro-${jobId}.mp4"`);

    const stream = fs.createReadStream(outputPath);
    stream.pipe(res);
    stream.on('end', () => {
      try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    });
    stream.on('error', err => {
      console.error(`[${jobId}] Stream error:`, err.message);
      try { res.end(); } catch (_) {}
      try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    });

  } catch (err) {
    console.error(`[${jobId}] Promo-assembly-pro error:`, err.message);
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    if (!res.headersSent) {
      res.status(500).json({ error: err.message });
    }
  } finally {
    if (jobCounted) {
      activeJobs--;
      resetIdleTimer();
    }
  }
});

// ---------------------------------------------------------------------------
// Demarrage du serveur
// ---------------------------------------------------------------------------

app.listen(PORT, () => {
  console.log(`[PromoClip FFmpeg Server v${VERSION}] Demarre sur le port ${PORT}`);
  console.log(`  MAX_CONCURRENT_JOBS = ${MAX_CONCURRENT_JOBS}`);
  console.log(`  FLY_SECRET configure: ${FLY_SECRET ? 'OUI' : 'NON'}`);
  console.log(`  WORKER_SECRET configure: ${WORKER_SECRET ? 'OUI' : 'NON'}`);
  if (!FLY_SECRET && !WORKER_SECRET) {
    console.error('  [WARN] Aucun secret configure — toutes les requetes seront refusees (500)');
  }
  console.log(`  Node.js: ${process.version}`);
});

process.on('SIGTERM', () => {
  console.log('[SIGTERM] Arret demande. Jobs actifs restants:', activeJobs);
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('[SIGINT] Arret. Jobs actifs restants:', activeJobs);
  process.exit(0);
});
