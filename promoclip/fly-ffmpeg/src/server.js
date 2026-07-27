/**
 * PromoClip Fly.io FFmpeg Server
 * Version: 1.0.1 — Split from subwhisper-ffmpeg (2026-04-11)
 *            v1.0.1 — Preserve aspect ratio for non-9:16 clip images (letterbox + static zoom)
 *            v1.0.2 — Asymmetric ratio tolerance [0.394, 0.619] to accept modern smartphones (19.5:9, 20:9, 21:9)
 *            v1.0.3 — Retrait -shortest dans mix audio /promo-assembly (fixait la truncation video a la duree TTS court)
 *            v1.0.4 — Xfade Pro timeout 60s -> 180s (crash sur full re-encode intro+main+outro avec avatar)
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
const VERSION = '1.1.27';  // v1.1.27 (17/05) - Contour bulle PiP : double drawbox (noir 2px outer + blanc 2px inner) autour de l'overlay bubble = look video-call pro. Inject 3 sites bubble (no-intro + with-intro + phaseB combo postSpeech). Toggle bubbleBorderEnabled default OFF. v1.1.26 Ken Burns + Vignette preserved.

// v1.1.0 — Hardware-accelerated H.264 encoding via NVENC (NVIDIA GPU) for local PromoClip Local
// PC backend (zero cloud). Toggle via env USE_NVENC=true. Fallback libx264 si absent.
const USE_NVENC = process.env.USE_NVENC === 'true';
// Presets NVENC : p1 (fastest) ... p7 (slowest, best quality). p4 = balanced.
// libx264 presets : ultrafast | fast (used for higher quality finals).
const ENCODER_FAST = USE_NVENC
  ? ['-c:v', 'h264_nvenc', '-preset', 'p3', '-rc', 'vbr', '-cq', '23', '-b:v', '0']
  : ['-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23'];
const ENCODER_QUALITY = USE_NVENC
  ? ['-c:v', 'h264_nvenc', '-preset', 'p5', '-rc', 'vbr', '-cq', '20', '-b:v', '0']
  : ['-c:v', 'libx264', '-preset', 'fast', '-crf', '20'];
const ENCODER_FINAL = USE_NVENC
  ? ['-c:v', 'h264_nvenc', '-preset', 'p5', '-rc', 'vbr', '-cq', '23', '-b:v', '0']
  : ['-c:v', 'libx264', '-preset', 'fast', '-crf', '23'];
console.log('[encoder] ' + (USE_NVENC ? 'NVENC GPU (h264_nvenc)' : 'libx264 CPU') + ' — set USE_NVENC=true env to toggle.');

// ---------------------------------------------------------------------------
// Etat global
// ---------------------------------------------------------------------------

let activeJobs = 0;
const startTime = Date.now();

// v1.1.15 — SFX paths : 2 fichiers synthétiques générés au boot via ffmpeg (idempotent).
// whoosh.wav (150ms) = sweep filtré → transition intro→split. Anticipation visuelle (-0.2s avant cut).
// ding.wav (350ms) = sine 880Hz + decay → outro final. Sensation de "fini propre", boost partage.
const SFX_DIR = path.join(__dirname, '..', 'sfx');
const SFX_WHOOSH = path.join(SFX_DIR, 'whoosh.wav');
const SFX_DING = path.join(SFX_DIR, 'ding.wav');

function ensureSfxFiles() {
  try { fs.mkdirSync(SFX_DIR, { recursive: true }); } catch (_) {}

  if (!fs.existsSync(SFX_WHOOSH)) {
    // Whoosh = bandpass filtered noise + sweep + fade in/out
    const r = spawnSync('ffmpeg', [
      '-y',
      '-f', 'lavfi',
      '-i', 'anoisesrc=duration=0.15:color=brown:amplitude=0.5',
      '-af', 'bandpass=f=1200:w=2400,afade=t=in:st=0:d=0.02,afade=t=out:st=0.10:d=0.05,volume=2.0',
      '-ar', '44100', '-ac', '1',
      SFX_WHOOSH
    ], { stdio: 'pipe', windowsHide: true });
    if (r.status === 0) console.log(`[SFX] generated whoosh.wav (${fs.statSync(SFX_WHOOSH).size}B)`);
    else console.warn(`[SFX] whoosh generation failed: ${(r.stderr||'').toString().slice(-200)}`);
  }
  if (!fs.existsSync(SFX_DING)) {
    // Ding = sine 880Hz + 660Hz harmonic + exp decay
    const r = spawnSync('ffmpeg', [
      '-y',
      '-f', 'lavfi',
      '-i', 'sine=frequency=880:duration=0.35',
      '-f', 'lavfi',
      '-i', 'sine=frequency=1320:duration=0.35',
      '-filter_complex', '[0:a]volume=0.7[a1];[1:a]volume=0.3[a2];[a1][a2]amix=inputs=2:normalize=0,afade=t=out:st=0.05:d=0.30,volume=1.5[aout]',
      '-map', '[aout]',
      '-ar', '44100', '-ac', '1',
      SFX_DING
    ], { stdio: 'pipe', windowsHide: true });
    if (r.status === 0) console.log(`[SFX] generated ding.wav (${fs.statSync(SFX_DING).size}B)`);
    else console.warn(`[SFX] ding generation failed: ${(r.stderr||'').toString().slice(-200)}`);
  }
}
const { spawnSync } = require('child_process');
ensureSfxFiles();

// ---------------------------------------------------------------------------
// Auto-shutdown : eteindre la machine apres IDLE_SHUTDOWN_MS sans jobs actifs.
// Necessaire car auto_stop_machines = "off" (empeche Fly.io de tuer les jobs).
// Fly redemarrera la machine a la prochaine requete (auto_start_machines=true).
// ---------------------------------------------------------------------------
// v1.1.4 — IDLE_SHUTDOWN désactivable via env (NO_IDLE_SHUTDOWN=true en mode local PC).
// Sur Fly.io cloud : 30min idle → exit pour économiser ressources / coûts.
// Sur PC local : on veut que ça tourne en continu → set NO_IDLE_SHUTDOWN=true.
const IDLE_SHUTDOWN_MS = 30 * 60 * 1000; // 30 minutes
const IDLE_SHUTDOWN_DISABLED = process.env.NO_IDLE_SHUTDOWN === 'true';
let idleTimer = null;

function resetIdleTimer() {
  if (IDLE_SHUTDOWN_DISABLED) return;
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
if (IDLE_SHUTDOWN_DISABLED) console.log('[idle] AUTO-SHUTDOWN désactivé (NO_IDLE_SHUTDOWN=true)');

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
        ...ENCODER_FAST,
        '-pix_fmt', 'yuv420p',
        '-t', String(dur),
        '-y', clipOutPath
      ];

      await new Promise((resolve, reject) => {
        const ff = spawn('ffmpeg', ffArgs, { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
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
        ...ENCODER_FAST,
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        '-y', concatOut
      ];

      await new Promise((resolve, reject) => {
        const ff = spawn('ffmpeg', xfadeArgs, { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
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
          ...ENCODER_FAST,
          '-c:a', 'aac', '-b:a', '128k',
          '-pix_fmt', 'yuv420p',
          '-y', avatarOutPath
        ];

        await new Promise((resolve, reject) => {
          const ff = spawn('ffmpeg', ffArgs, { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
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
          ...ENCODER_FAST,
          '-c:a', 'aac', '-b:a', '128k',
          '-pix_fmt', 'yuv420p',
          '-t', String(Math.min(30, clips.length * 10)),
          '-y', avatarOutPath
        ];

        await new Promise((resolve, reject) => {
          const ff = spawn('ffmpeg', ffArgs, { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
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
        const ff = spawn('ffmpeg', mixArgs, { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
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
      // v1.1.2 — utilise path relatif + cwd=tmpDir au spawn (cf comment plus haut promo-assembly-pro)
      const subsPathFF = 'subs.ass';
      const subsOut = path.join(tmpDir, 'final-subs.mp4');

      const subsArgs = [
        '-i', finalOut,
        '-vf', `ass=${subsPathFF}`,
        ...ENCODER_QUALITY,
        '-c:a', 'copy',
        '-movflags', '+faststart',
        '-y', subsOut
      ];

      await new Promise((resolve, reject) => {
        // v1.1.2 — cwd=tmpDir pour que `ass=subs.ass` (relative) marche sur Windows.
        const ff = spawn('ffmpeg', subsArgs, { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true, cwd: tmpDir });
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

  const { video, videoMime, moments, avatarVideo, avatarMode, subtitles, width, height, outroClip, outroDuration, avatarIntroFullscreen, avatarIntroDuration, avatarPostSpeechFullscreen, jumpCutsEnabled, hookText, sfxEnabled, safeZonesEnabled, lutBrandEnabled, loopHookEnabled, kenBurnsEnabled, vignetteEnabled, bubbleBorderEnabled, avatarBubblePosition, avatarBubbleSize, subtitleKaraokeColor } = req.body;

  // v1.1.24 — Cropdetect dynamique : helper qui lance ffmpeg cropdetect=30:2:0 sur l'avatar
  // post-chromakey et retourne {w, h, x, y} de la bbox du contenu réel (pas de bandes dark).
  // Test scientifique 17/05 : limit=30 capture le dark #0F0F13 (luma~17) comme bord, retourne
  // crop=500:776:110:310 sur avatar Lumen 720×1280 (= contenu réel visage SadTalker).
  async function cropdetectBands(videoPath, limit) {
    const lim = limit || 30;
    return new Promise((resolve) => {
      const ff = spawn('ffmpeg', ['-i', videoPath, '-vf', `cropdetect=${lim}:2:0`, '-t', '1', '-f', 'null', '-'], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
      let stderr = '';
      ff.stderr.on('data', d => { stderr += d.toString(); });
      ff.on('close', () => {
        const matches = [...stderr.matchAll(/crop=(\d+):(\d+):(\d+):(\d+)/g)];
        if (matches.length === 0) return resolve(null);
        const last = matches[matches.length - 1];
        resolve({ w: parseInt(last[1]), h: parseInt(last[2]), x: parseInt(last[3]), y: parseInt(last[4]) });
      });
      ff.on('error', () => resolve(null));
      setTimeout(() => { try { ff.kill(); } catch(_){} resolve(null); }, 15000);
    });
  }

  // v1.1.24 — Helper bubble PiP étendu avec ratio détecté dynamiquement (cropParams).
  // Si cropParams fourni (cropdetect réussi) : pipHeight adapté = pipWidth × (h/w) du contenu réel.
  // Sinon fallback ratio 1:1 (carré) comme v1.1.23.
  function computeBubbleGeom(outWidth, outHeight, position, size, cropParams) {
    const sz = (size === 3) ? 0.56 : (size === 2 ? 0.42 : 0.28);
    const pipWidth = Math.round(outWidth * sz);
    // Ratio detected : si cropParams valide → utiliser ratio h/w du contenu réel, sinon carré 1:1
    const sourceRatio = (cropParams && cropParams.w > 0 && cropParams.h > 0) ? (cropParams.h / cropParams.w) : 1.0;
    const pipHeight = Math.round(pipWidth * sourceRatio);
    const margin = 20;
    const topMargin = 80;
    const bottomMargin = 120;
    let pipX, pipY;
    switch ((position || 'br').toLowerCase()) {
      case 'tl': pipX = margin; pipY = topMargin; break;
      case 'tr': pipX = outWidth - pipWidth - margin; pipY = topMargin; break;
      case 'bl': pipX = margin; pipY = outHeight - pipHeight - bottomMargin; break;
      case 'br': default: pipX = outWidth - pipWidth - margin; pipY = outHeight - pipHeight - bottomMargin; break;
    }
    return { pipSize: pipWidth, pipWidth, pipHeight, pipX, pipY };
  }
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
      const ff = spawn('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', recordingPath], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
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

      // v1.1.3 — Preprocess chromakey si avatar Lumen greenscreen (body.avatarMatteColor).
      // Sans ça, le fond vert reste visible dans le split-screen final (visuellement moche).
      // Pipeline : chromakey + despill anti-bleed + composer sur fond dark cohérent #0F0F13.
      const matteColor = req.body.avatarMatteColor;
      if (matteColor && /^0x[0-9a-fA-F]{6}$/.test(matteColor)) {
        const cleanPath = path.join(tmpDir, 'avatar_clean.mp4');
        console.log(`[${jobId}] Pre-chromakey avatar matteColor=${matteColor}...`);
        await new Promise((resolve, reject) => {
          // v1.1.5 — fix : `overlay` accepte `format=yuv420` (sans 'p'), pas `yuv420p`.
          // Pour garantir un yuv420p final pour libx264, ajouter `,format=yuv420p` après overlay.
          const fc = (
            `[0:v]split=2[a_src][bg_src];` +
            `[a_src]chromakey=${matteColor}:0.30:0.10,despill=type=green:mix=0.5,format=yuva420p[a_clean];` +
            `[bg_src]drawbox=color=0x0F0F13:t=fill,format=yuv420p[bg];` +
            `[bg][a_clean]overlay=shortest=1,format=yuv420p[outv]`
          );
          const ff = spawn('ffmpeg', [
            '-i', avatarPath,
            '-filter_complex', fc,
            '-map', '[outv]', '-map', '0:a?',
            ...ENCODER_FAST, '-pix_fmt', 'yuv420p',
            '-c:a', 'copy',
            '-movflags', '+faststart',
            '-y', cleanPath
          ], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true, cwd: tmpDir });
          let stderr = '';
          ff.stderr.on('data', d => { stderr += d.toString(); });
          ff.on('close', code => code === 0 ? resolve() : reject(new Error(`Pre-chromakey exit ${code}: ${stderr.slice(-300)}`)));
          ff.on('error', reject);
          setTimeout(() => { try { ff.kill('SIGKILL'); } catch (_) {} reject(new Error('Pre-chromakey timeout 60s')); }, 60000);
        });
        avatarPath = cleanPath;
        console.log(`[${jobId}] Pre-chromakey OK → avatar matte extracted + composed on #0F0F13`);
      }
      avatarDur = await new Promise((resolve) => {
        const ff = spawn('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', avatarPath], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
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

    // v1.1.24 — Cropdetect dynamique avatar pour mode bubble (1 fois par job, après pre-chromakey).
    // Détecte la bbox du contenu visage SadTalker (post-chromakey dark fond), élimine bandes dark.
    let avatarCropParams = null;
    if (avatarMode === 'bubble' && avatarPath) {
      try {
        avatarCropParams = await cropdetectBands(avatarPath, 30);
        if (avatarCropParams) {
          console.log(`[${jobId}] Avatar cropdetect bbox : w=${avatarCropParams.w} h=${avatarCropParams.h} x=${avatarCropParams.x} y=${avatarCropParams.y} (ratio ${(avatarCropParams.h / avatarCropParams.w).toFixed(3)})`);
        } else {
          console.log(`[${jobId}] Avatar cropdetect : aucun bord détecté, fallback crop min(iw,ih) carré`);
        }
      } catch (e) { console.log(`[${jobId}] Avatar cropdetect FAIL: ${e.message}`); }
    }

    // Computed max duration for the main video assembly
    const maxMainDur = Math.min(60, Math.max(probeDur, avatarDur || probeDur));
    // Symmetric tpad: freeze last frame of whichever stream is shorter
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
      // v1.1.2 — Sur Windows, le filter ffmpeg `ass=PATH` ne parse pas correctement les paths
      // absolus avec drive letter (le `:` de `C:` est interprété comme option separator).
      // Solution robuste : passer cwd=tmpDir au spawn ffmpeg et utiliser le filename relatif 'subs.ass'.
      // Les `-i` arguments (paths abs) restent intacts car ne traversent pas le filter parser.
      var subPathFF = 'subs.ass';
      let subsContent = subtitles;
      // v1.1.16 — Safe zones TikTok : patch MarginV pour faire remonter les subs au-dessus de la zone
      // caption native TikTok (~220px du bas). Regex sur les lignes Style: ou Dialogue: \r? \N MarginV.
      // Pattern ASS standard : Style: Default,Arial Black,42,...,2.5,1,1,2,10,10,MARGINV,1
      //                        Dialogue: 0,...,Default,,LMargin,RMargin,MarginV,,Text
      if (safeZonesEnabled) {
        const SAFE_MARGIN_V = 220;
        try {
          // Style lines : 16e champ = MarginV (séparateur ,)
          subsContent = subsContent.replace(/^(Style: [^\r\n]+)$/gm, (line) => {
            const parts = line.split(',');
            if (parts.length >= 21) {  // ASS v4+ Style a 23 fields
              parts[parts.length - 2] = String(SAFE_MARGIN_V);  // avant-dernier = MarginV
              return parts.join(',');
            }
            return line;
          });
          // Dialogue lines : champ MarginV (9e après Dialogue:) - mais souvent =0 (utilise Style MarginV)
          // On laisse les Dialogue tels quels (la modif Style suffit dans 99% cas).
          console.log(`[ass] safeZones : Style MarginV patched to ${SAFE_MARGIN_V}px`);
        } catch (e) { console.log(`[ass] safeZones patch failed: ${e.message}`); }
      }

      // v1.1.23 (vote 3-LLM Q2 = B Kimi + C DeepSeek combinés) — Karaoké couleur dynamique.
      // Spec ASS : PrimaryColour = couleur APRÈS highlight (= mot lu), SecondaryColour = AVANT.
      // Tag \k<dur> dans Dialogue fait transition Secondary → Primary au passage temporel.
      // Diagnostic v1.1.21 sans-effet : Lumen injecte overrides inline `\1c&Hxxx` ou `\c&Hxxx`
      // dans le texte de chaque syllabe qui figent la couleur (cassent la transition \k).
      // Fix v1.1.23 : (1) patch Style global Primary+Secondary, (2) STRIPPER les overrides
      // inline (les retirer, pas les remplacer) pour laisser ma Style Primary s'appliquer.
      if (subtitleKaraokeColor && /^#[0-9a-fA-F]{6}$/.test(subtitleKaraokeColor)) {
        const hex = subtitleKaraokeColor.slice(1);
        const r = hex.slice(0, 2), g = hex.slice(2, 4), b = hex.slice(4, 6);
        const assBgr = '&H00' + b.toUpperCase() + g.toUpperCase() + r.toUpperCase();
        try {
          // (1) Patch Style global PrimaryColour + SecondaryColour
          subsContent = subsContent.replace(/^(Style: [^\r\n]+)$/gm, (line) => {
            const parts = line.split(',');
            if (parts.length >= 21) {
              parts[3] = assBgr;  // PrimaryColour
              if (parts[4] && parts[4].startsWith('&H')) parts[4] = '&H00FFFFFF';  // SecondaryColour blanc
              return parts.join(',');
            }
            return line;
          });
          // (2) Strip overrides inline qui figent la couleur : \1c, \c, \2c
          // \1c = primary color override, \c = primary alias, \2c = secondary
          // Replace ces tags par chaîne vide → renderer utilise les Style Primary/Secondary
          const beforeStripLen = subsContent.length;
          subsContent = subsContent.replace(/\\1c&H[0-9a-fA-F]+&?/g, '');
          subsContent = subsContent.replace(/\\c&H[0-9a-fA-F]+&?/g, '');
          subsContent = subsContent.replace(/\\2c&H[0-9a-fA-F]+&?/g, '');
          const afterStripLen = subsContent.length;
          const strippedChars = beforeStripLen - afterStripLen;
          console.log(`[ass] karaoke : PrimaryColour=${assBgr} + stripped ${strippedChars} chars inline color overrides`);

          // (3) Debug dump : sauve un sample des 2000 premiers chars dans le log pour analyse
          const sampleHead = subsContent.slice(0, 2000).replace(/\r?\n/g, ' | ');
          console.log(`[ass] DEBUG sample (post-patch first 2KB): ${sampleHead}`);
        } catch (e) { console.log(`[ass] karaoke color patch failed: ${e.message}`); }
      }

      // v1.1.20 — MarginL/MarginR anti-débordement subs L/R. Default 60px chaque côté.
      // Style fields ASS v4+ : MarginL=index 19, MarginR=index 20 (avant MarginV=21, Encoding=22).
      // Wait, structure exacte ASS Style :
      // Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,
      // Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,
      // Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
      // → index 19=MarginL, 20=MarginR, 21=MarginV, 22=Encoding (23 fields total v4+)
      try {
        subsContent = subsContent.replace(/^(Style: [^\r\n]+)$/gm, (line) => {
          const parts = line.split(',');
          if (parts.length >= 23) {
            parts[19] = '60';  // MarginL
            parts[20] = '60';  // MarginR
            return parts.join(',');
          }
          return line;
        });
        console.log(`[ass] MarginL/R set to 60px (anti-débordement)`);
      } catch (e) { console.log(`[ass] margin L/R patch failed: ${e.message}`); }
      fs.writeFileSync(subPath, subsContent, 'utf8');
    }

    if (avatarPath) {
      const recordPrefilter = needsFreezeRecord
        ? `tpad=stop_mode=clone:stop_duration=${freezeRecordExtra.toFixed(2)},`
        : '';
      const avatarPrefilter = needsFreezeAvatar
        ? `tpad=stop_mode=clone:stop_duration=${freezeAvatarExtra.toFixed(2)},`
        : '';

      // v1.1.26 — Ken Burns deplace en POST-PROCESS (apres assembly, avant outro).
      // Raison : zoompan dans filter_complex avec d=1 a un comportement instable selon
      // l'input video (reset zoom potentiel par input frame). En post-process sur 1 input
      // unique, zoompan est fiable et le code reste simple. Helper conserve mais retourne ''.
      const kenBurnsChain = (w, h, dur) => '';

      // v1.1.27 — Contour bulle PiP : double drawbox (black 2px outer + white 2px inner)
      // autour de l'overlay bubble = look video-call pro qui separe nettement avatar du
      // recording. Inject IN-LINE apres overlay dans 3 sites bubble. Default OFF (toggle).
      // Safe : drawbox accepte coords negatives (clip auto si pip pres du bord).
      const bubbleBorderChain = (px, py, pw, ph) => {
        if (!bubbleBorderEnabled) return '';
        return `,drawbox=x=${px-3}:y=${py-3}:w=${pw+6}:h=${ph+6}:color=black@0.4:t=2,drawbox=x=${px-1}:y=${py-1}:w=${pw+2}:h=${ph+2}:color=white@0.8:t=2`;
      };

      const introDur = avatarIntroFullscreen
        ? Math.max(1, Math.min(5, Number(avatarIntroDuration) || 2))
        : 0;

      // v1.1.6 — Mode Pro pro-grade : switch fullscreen quand avatar fini de parler.
      // S'active si toggle ON ET recording > avatar + 0.5s. Désactive le tpad freeze avatar
      // (l'avatar termine sa parole, puis recording prend tout l'écran). Plus pro qu'un
      // avatar figé pendant que la vidéo continue à défiler. Premier chantier de la roadmap
      // viralité vote 3-LLM 16/05 (item #8).
      const postSpeechActive = !!avatarPostSpeechFullscreen && avatarDur > 0 && probeDur > avatarDur + 0.5;
      if (postSpeechActive) {
        console.log(`[${jobId}] Post-speech fullscreen ACTIVE : split 0-${avatarDur.toFixed(1)}s + fullscreen ${avatarDur.toFixed(1)}-${probeDur.toFixed(1)}s`);
      }

      let filterComplex;
      let mapVideo;
      let totalDur;

      if (postSpeechActive && introDur > 0) {
        // ── PHASE 2b : Hero intro + split + post-speech fullscreen-trail (3 segments concat) ──
        // Filter graph 3 phases :
        //   Phase A (0 → introDur)       : intro fullscreen avatar (avatar[0:introDur])
        //   Phase B (introDur → introDur+avatarDur) : split avatar+recording (avatar[0:avatarDur] + recording[0:avatarDur])
        //   Phase C (introDur+avatarDur → introDur+probeDur) : fullscreen recording (recording[avatarDur:probeDur])
        // Pas de tpad freeze (postSpeechActive prend précédence sur le freeze) — l'avatar
        // termine naturellement à avatarDur puis recording prend tout l'écran.
        const introClamped = Math.max(1, Math.min(5, introDur));
        const avd = avatarDur;
        totalDur = introClamped + Math.min(60, probeDur);
        console.log(`[${jobId}] Phase 2b combo: intro ${introClamped}s + split 0-${avd.toFixed(1)}s + fullscreen-trail ${avd.toFixed(1)}-${probeDur.toFixed(1)}s, total ${totalDur.toFixed(1)}s`);

        // Avatar split en 2 : intro fullscreen + split-zone
        const avSplit = `[0:v]split=2[av_intro_src][av_split_src]`;
        const avIntro = `[av_intro_src]trim=0:${introClamped},setpts=PTS-STARTPTS,fps=30,scale=${outWidth}:${outHeight}:force_original_aspect_ratio=increase,crop=${outWidth}:${outHeight}:(iw-${outWidth})/2:(ih-${outHeight})/2,setsar=1[phaseA]`;
        const avZone = `[av_split_src]trim=0:${avd.toFixed(2)},setpts=PTS-STARTPTS,fps=30`;

        // Recording split en 2 : split-zone + fullscreen-trail
        const recSplit = `[1:v]split=2[rec_split_src][rec_full_src]`;
        const recSplitPart = `[rec_split_src]trim=0:${avd.toFixed(2)},setpts=PTS-STARTPTS,fps=30`;
        const recFullPart = `[rec_full_src]trim=${avd.toFixed(2)}:${probeDur.toFixed(2)},setpts=PTS-STARTPTS,fps=30,scale=${outWidth}:${outHeight}:force_original_aspect_ratio=decrease,pad=${outWidth}:${outHeight}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1[phaseC]`;

        // Split phase B (mode-dependent)
        let phaseB;
        if (mode === 'split-top') {
          const avatarH = Math.round(outHeight * 0.35);
          const recordH = outHeight - avatarH;
          phaseB = [
            `${avZone},split=2[avM_av_zone][avB_av_zone];[avB_av_zone]scale=${outWidth}:${avatarH}:force_original_aspect_ratio=increase,crop=${outWidth}:${avatarH},boxblur=30:8,eq=brightness=-0.15,setsar=1[avBf_av_zone];[avM_av_zone]scale=${outWidth}:${avatarH}:force_original_aspect_ratio=decrease,setsar=1[avMf_av_zone];[avBf_av_zone][avMf_av_zone]overlay=(W-w)/2:(H-h)/2[av_zone]`,
            `${recSplitPart},scale=${outWidth}:${recordH}:force_original_aspect_ratio=decrease,pad=${outWidth}:${recordH}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1[rec_zone]`,
            `[av_zone][rec_zone]vstack=inputs=2[phaseB]`
          ].join(';');
        } else if (mode === 'split-bottom') {
          const avatarH = Math.round(outHeight * 0.35);
          const recordH = outHeight - avatarH;
          phaseB = [
            `${recSplitPart},scale=${outWidth}:${recordH}:force_original_aspect_ratio=decrease,pad=${outWidth}:${recordH}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1[rec_zone]`,
            `${avZone},split=2[avM_av_zone][avB_av_zone];[avB_av_zone]scale=${outWidth}:${avatarH}:force_original_aspect_ratio=increase,crop=${outWidth}:${avatarH},boxblur=30:8,eq=brightness=-0.15,setsar=1[avBf_av_zone];[avM_av_zone]scale=${outWidth}:${avatarH}:force_original_aspect_ratio=decrease,setsar=1[avMf_av_zone];[avBf_av_zone][avMf_av_zone]overlay=(W-w)/2:(H-h)/2[av_zone]`,
            `[rec_zone][av_zone]vstack=inputs=2[phaseB]`
          ].join(';');
        } else {
          // bubble PiP
          // v1.1.24 — Bulle PiP avec cropdetect dynamique + ratio adaptatif
          const _bg = computeBubbleGeom(outWidth, outHeight, avatarBubblePosition, avatarBubbleSize, avatarCropParams);
          const pipSize = _bg.pipSize, pipX = _bg.pipX, pipY = _bg.pipY;
          const pipWidth = _bg.pipWidth, pipHeight = _bg.pipHeight;
          // Crop filter dynamique : si cropParams détecté, retire les bandes dark ; sinon fallback min(iw,ih) carré
          const _cropFilter = avatarCropParams
            ? `crop=${avatarCropParams.w}:${avatarCropParams.h}:${avatarCropParams.x}:${avatarCropParams.y}`
            : `crop='min(iw\\,ih)':'min(iw\\,ih)'`;
          phaseB = [
            `${recSplitPart},scale=${outWidth}:${outHeight}:force_original_aspect_ratio=decrease,pad=${outWidth}:${outHeight}:(ow-iw)/2:(oh-ih)/2,setsar=1[rec_zone]`,
            `${avZone},${_cropFilter},scale=${pipWidth}:${pipHeight},setsar=1,fps=30,format=yuv420p[av_pip]`,
            `[rec_zone][av_pip]overlay=${pipX}:${pipY}${bubbleBorderChain(pipX, pipY, pipWidth, pipHeight)}[phaseB]`
          ].join(';');
        }

        // v1.1.9 — Crossfade 0.4s entre les 3 phases (pro look vs hard cut concat).
        // Total durée réduit de 2*XF = 0.8s mais ergonomie pro vaut largement la perte.
        const XF = 0.4;
        // 1er xfade A→B : offset = introDur - XF
        // 2e xfade (AB)→C : offset = (introDur - XF) + avd - XF
        const off1 = (introClamped - XF).toFixed(3);
        const off2 = (introClamped + avd - XF - XF).toFixed(3);
        const xfade1 = `[phaseA][phaseB]xfade=transition=fade:duration=${XF}:offset=${off1}[ab_xf]`;
        const xfade2 = `[ab_xf][phaseC]xfade=transition=fade:duration=${XF}:offset=${off2}[outv]`;
        const subFilter = subPath ? `;[outv]ass=${subPathFF}[final]` : '';
        mapVideo = subFilter ? '[final]' : '[outv]';
        filterComplex = [avSplit, avIntro, recSplit, phaseB, recFullPart, xfade1, xfade2].join(';') + subFilter;
        // Durée finale = introDur + avd + (probeDur - avd) - 2*XF = introDur + probeDur - 2*XF
        totalDur = totalDur - 2 * XF;

      } else if (postSpeechActive && introDur === 0) {
        // ── POST-SPEECH FULLSCREEN MODE (Phase 1 : without hero intro) ──
        // Phase A (0 → avatarDur)    : split-screen avatar+recording
        // Phase B (avatarDur → probeDur) : recording fullscreen
        totalDur = Math.min(60, probeDur);
        const avd = avatarDur;
        const bDur = Math.min(60, probeDur) - avd;

        // Recording split en 2 portions (avant/après avatarDur) — split=2 explicite pour clarté
        const recSplit = `[1:v]split=2[r_a][r_b]`;
        const recPartA = `[r_a]trim=0:${avd.toFixed(2)},setpts=PTS-STARTPTS,fps=30`;
        const recPartB = `[r_b]trim=${avd.toFixed(2)}:${(avd + bDur).toFixed(2)},setpts=PTS-STARTPTS,fps=30`;

        // Avatar trim (no tpad — l'avatar va finir naturellement à avatarDur, c'est OK)
        const avTrim = `[0:v]trim=0:${avd.toFixed(2)},setpts=PTS-STARTPTS,fps=30`;

        let splitGraph;
        let fullGraph;
        if (mode === 'split-top') {
          const avatarH = Math.round(outHeight * 0.35);
          const recordH = outHeight - avatarH;
          splitGraph = [
            `${avTrim},split=2[avM_av_top][avB_av_top];[avB_av_top]scale=${outWidth}:${avatarH}:force_original_aspect_ratio=increase,crop=${outWidth}:${avatarH},boxblur=30:8,eq=brightness=-0.15,setsar=1[avBf_av_top];[avM_av_top]scale=${outWidth}:${avatarH}:force_original_aspect_ratio=decrease,setsar=1[avMf_av_top];[avBf_av_top][avMf_av_top]overlay=(W-w)/2:(H-h)/2[av_top]`,
            `${recPartA},scale=${outWidth}:${recordH}:force_original_aspect_ratio=decrease,pad=${outWidth}:${recordH}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1[rec_split]`,
            `[av_top][rec_split]vstack=inputs=2[phaseA]`
          ].join(';');
          fullGraph = `${recPartB},scale=${outWidth}:${outHeight}:force_original_aspect_ratio=decrease,pad=${outWidth}:${outHeight}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1[phaseB]`;
        } else if (mode === 'split-bottom') {
          const avatarH = Math.round(outHeight * 0.35);
          const recordH = outHeight - avatarH;
          splitGraph = [
            `${recPartA},scale=${outWidth}:${recordH}:force_original_aspect_ratio=decrease,pad=${outWidth}:${recordH}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1[rec_split]`,
            `${avTrim},split=2[avM_av_bot][avB_av_bot];[avB_av_bot]scale=${outWidth}:${avatarH}:force_original_aspect_ratio=increase,crop=${outWidth}:${avatarH},boxblur=30:8,eq=brightness=-0.15,setsar=1[avBf_av_bot];[avM_av_bot]scale=${outWidth}:${avatarH}:force_original_aspect_ratio=decrease,setsar=1[avMf_av_bot];[avBf_av_bot][avMf_av_bot]overlay=(W-w)/2:(H-h)/2[av_bot]`,
            `[rec_split][av_bot]vstack=inputs=2[phaseA]`
          ].join(';');
          fullGraph = `${recPartB},scale=${outWidth}:${outHeight}:force_original_aspect_ratio=decrease,pad=${outWidth}:${outHeight}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1[phaseB]`;
        } else {
          // bubble PiP
          // v1.1.24 — Bulle PiP avec cropdetect dynamique + ratio adaptatif
          const _bg = computeBubbleGeom(outWidth, outHeight, avatarBubblePosition, avatarBubbleSize, avatarCropParams);
          const pipSize = _bg.pipSize, pipX = _bg.pipX, pipY = _bg.pipY;
          const pipWidth = _bg.pipWidth, pipHeight = _bg.pipHeight;
          // Crop filter dynamique : si cropParams détecté, retire les bandes dark ; sinon fallback min(iw,ih) carré
          const _cropFilter = avatarCropParams
            ? `crop=${avatarCropParams.w}:${avatarCropParams.h}:${avatarCropParams.x}:${avatarCropParams.y}`
            : `crop='min(iw\\,ih)':'min(iw\\,ih)'`;
          splitGraph = [
            `${recPartA},scale=${outWidth}:${outHeight}:force_original_aspect_ratio=decrease,pad=${outWidth}:${outHeight}:(ow-iw)/2:(oh-ih)/2,setsar=1[rec_split]`,
            `${avTrim},${_cropFilter},scale=${pipWidth}:${pipHeight},setsar=1,fps=30,format=yuv420p[av_pip]`,
            `[rec_split][av_pip]overlay=${pipX}:${pipY}[phaseA]`
          ].join(';');
          fullGraph = `${recPartB},scale=${outWidth}:${outHeight}:force_original_aspect_ratio=decrease,pad=${outWidth}:${outHeight}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1[phaseB]`;
        }

        // v1.1.9 — Xfade au lieu de concat brut (transition pro 0.4s entre split et fullscreen-trail)
        const XF_PS = 0.4;
        const offPS = (avd - XF_PS).toFixed(3);
        const concatGraph = `[phaseA][phaseB]xfade=transition=fade:duration=${XF_PS}:offset=${offPS}[outv]`;
        // Durée finale = avd + (probeDur - avd) - XF = probeDur - XF
        totalDur = totalDur - XF_PS;
        const subFilter = subPath ? `;[outv]ass=${subPathFF}[final]` : '';
        mapVideo = subFilter ? '[final]' : '[outv]';
        filterComplex = [recSplit, splitGraph, fullGraph, concatGraph].join(';') + subFilter;

      } else if (introDur > 0) {
        // ── SINGLE-PASS: hero intro fullscreen + split-screen via concat FILTER ──
        totalDur = introDur + maxMainDur;
        console.log(`[${jobId}] Hero intro ${introDur}s (single-pass concat filter, total ${totalDur.toFixed(1)}s)`);

        // Branch A: intro fullscreen (avatar only, trimmed to introDur)
        const introFilter = `[0:v]trim=0:${introDur},setpts=PTS-STARTPTS,scale=${outWidth}:${outHeight}:force_original_aspect_ratio=increase,crop=${outWidth}:${outHeight}:(iw-${outWidth})/2:(ih-${outHeight})/2,setsar=1,fps=30[intro]`;

        // Branch B: split-screen (mode-dependent, with tpad)
        let splitFilter;
        if (mode === 'split-top') {
          const avatarH = Math.round(outHeight * 0.35);
          const recordH = outHeight - avatarH;
          splitFilter = [
            `[0:v]${avatarPrefilter}split=2[avM_avatar][avB_avatar];[avB_avatar]scale=${outWidth}:${avatarH}:force_original_aspect_ratio=increase,crop=${outWidth}:${avatarH},boxblur=30:8,eq=brightness=-0.15,setsar=1[avBf_avatar];[avM_avatar]scale=${outWidth}:${avatarH}:force_original_aspect_ratio=decrease,setsar=1[avMf_avatar];[avBf_avatar][avMf_avatar]overlay=(W-w)/2:(H-h)/2[avatar]`,
            `[1:v]${recordPrefilter}scale=${outWidth}:${recordH}:force_original_aspect_ratio=decrease,pad=${outWidth}:${recordH}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1${kenBurnsChain(outWidth, recordH, probeDur)}[record]`,
            `[avatar][record]vstack=inputs=2[split]`
          ].join(';');
        } else if (mode === 'split-bottom') {
          const avatarH = Math.round(outHeight * 0.35);
          const recordH = outHeight - avatarH;
          splitFilter = [
            `[1:v]${recordPrefilter}scale=${outWidth}:${recordH}:force_original_aspect_ratio=decrease,pad=${outWidth}:${recordH}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1${kenBurnsChain(outWidth, recordH, probeDur)}[record]`,
            `[0:v]${avatarPrefilter}split=2[avM_avatar][avB_avatar];[avB_avatar]scale=${outWidth}:${avatarH}:force_original_aspect_ratio=increase,crop=${outWidth}:${avatarH},boxblur=30:8,eq=brightness=-0.15,setsar=1[avBf_avatar];[avM_avatar]scale=${outWidth}:${avatarH}:force_original_aspect_ratio=decrease,setsar=1[avMf_avatar];[avBf_avatar][avMf_avatar]overlay=(W-w)/2:(H-h)/2[avatar]`,
            `[record][avatar]vstack=inputs=2[split]`
          ].join(';');
        } else {
          // v1.1.24 — Bulle PiP avec cropdetect dynamique + ratio adaptatif
          const _bg = computeBubbleGeom(outWidth, outHeight, avatarBubblePosition, avatarBubbleSize, avatarCropParams);
          const pipSize = _bg.pipSize, pipX = _bg.pipX, pipY = _bg.pipY;
          const pipWidth = _bg.pipWidth, pipHeight = _bg.pipHeight;
          // Crop filter dynamique : si cropParams détecté, retire les bandes dark ; sinon fallback min(iw,ih) carré
          const _cropFilter = avatarCropParams
            ? `crop=${avatarCropParams.w}:${avatarCropParams.h}:${avatarCropParams.x}:${avatarCropParams.y}`
            : `crop='min(iw\\,ih)':'min(iw\\,ih)'`;
          // v1.1.24c — Ajout format=yuv420p après scale pour compatibilité encoder libx264 (pixfmt explicit)
          // + ajout fps=30 pour matcher [intro] qui fait setsar=1,fps=30 (xfade exige même framerate)
          splitFilter = [
            `[1:v]${recordPrefilter}scale=${outWidth}:${outHeight}:force_original_aspect_ratio=decrease,pad=${outWidth}:${outHeight}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30${kenBurnsChain(outWidth, outHeight, probeDur)}[record]`,
            `[0:v]${avatarPrefilter}${_cropFilter},scale=${pipWidth}:${pipHeight},setsar=1,fps=30,format=yuv420p[pip]`,
            `[record][pip]overlay=${pipX}:${pipY}${bubbleBorderChain(pipX, pipY, pipWidth, pipHeight)}[split]`
          ].join(';');
        }

        // v1.1.9 — Xfade au lieu de concat brut (transition pro 0.4s intro → split)
        const XF_IS = 0.4;
        const offIS = (introDur - XF_IS).toFixed(3);
        const concatF = `[intro][split]xfade=transition=fade:duration=${XF_IS}:offset=${offIS}[outv]`;
        // Durée finale = introDur + maxMainDur - XF
        totalDur = totalDur - XF_IS;
        // Subtitles applied AFTER xfade (timestamps match full audio timeline)
        const subFilter = subPath ? `;[outv]ass=${subPathFF}[final]` : '';
        mapVideo = subFilter ? '[final]' : '[outv]';
        filterComplex = [introFilter, splitFilter, concatF].join(';') + subFilter;

      } else {
        // ── NO HERO INTRO: original split-screen only ──
        totalDur = maxMainDur;

        if (mode === 'split-top') {
          const avatarH = Math.round(outHeight * 0.35);
          const recordH = outHeight - avatarH;
          filterComplex = [
            `[0:v]${avatarPrefilter}split=2[avM_avatar][avB_avatar];[avB_avatar]scale=${outWidth}:${avatarH}:force_original_aspect_ratio=increase,crop=${outWidth}:${avatarH},boxblur=30:8,eq=brightness=-0.15,setsar=1[avBf_avatar];[avM_avatar]scale=${outWidth}:${avatarH}:force_original_aspect_ratio=decrease,setsar=1[avMf_avatar];[avBf_avatar][avMf_avatar]overlay=(W-w)/2:(H-h)/2[avatar]`,
            `[1:v]${recordPrefilter}scale=${outWidth}:${recordH}:force_original_aspect_ratio=decrease,pad=${outWidth}:${recordH}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1${kenBurnsChain(outWidth, recordH, probeDur)}[record]`,
            `[avatar][record]vstack=inputs=2[outv]`
          ].join(';');
        } else if (mode === 'split-bottom') {
          const avatarH = Math.round(outHeight * 0.35);
          const recordH = outHeight - avatarH;
          filterComplex = [
            `[1:v]${recordPrefilter}scale=${outWidth}:${recordH}:force_original_aspect_ratio=decrease,pad=${outWidth}:${recordH}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1${kenBurnsChain(outWidth, recordH, probeDur)}[record]`,
            `[0:v]${avatarPrefilter}split=2[avM_avatar][avB_avatar];[avB_avatar]scale=${outWidth}:${avatarH}:force_original_aspect_ratio=increase,crop=${outWidth}:${avatarH},boxblur=30:8,eq=brightness=-0.15,setsar=1[avBf_avatar];[avM_avatar]scale=${outWidth}:${avatarH}:force_original_aspect_ratio=decrease,setsar=1[avMf_avatar];[avBf_avatar][avMf_avatar]overlay=(W-w)/2:(H-h)/2[avatar]`,
            `[record][avatar]vstack=inputs=2[outv]`
          ].join(';');
        } else {
          // v1.1.24 — Bulle PiP avec cropdetect dynamique + ratio adaptatif
          const _bg = computeBubbleGeom(outWidth, outHeight, avatarBubblePosition, avatarBubbleSize, avatarCropParams);
          const pipSize = _bg.pipSize, pipX = _bg.pipX, pipY = _bg.pipY;
          const pipWidth = _bg.pipWidth, pipHeight = _bg.pipHeight;
          // Crop filter dynamique : si cropParams détecté, retire les bandes dark ; sinon fallback min(iw,ih) carré
          const _cropFilter = avatarCropParams
            ? `crop=${avatarCropParams.w}:${avatarCropParams.h}:${avatarCropParams.x}:${avatarCropParams.y}`
            : `crop='min(iw\\,ih)':'min(iw\\,ih)'`;
          filterComplex = [
            `[1:v]${recordPrefilter}scale=${outWidth}:${outHeight}:force_original_aspect_ratio=decrease,pad=${outWidth}:${outHeight}:(ow-iw)/2:(oh-ih)/2,setsar=1${kenBurnsChain(outWidth, outHeight, probeDur)}[record]`,
            `[0:v]${avatarPrefilter}${_cropFilter},scale=${pipWidth}:${pipHeight},setsar=1,fps=30,format=yuv420p[pip]`,
            `[record][pip]overlay=${pipX}:${pipY}${bubbleBorderChain(pipX, pipY, pipWidth, pipHeight)}[outv]`
          ].join(';');
        }

        const subFilter = subPath ? `,ass=${subPathFF}` : '';
        filterComplex = filterComplex + (subFilter ? `;[outv]${subFilter.slice(1)}[final]` : '');
        mapVideo = subFilter ? '[final]' : '[outv]';
      }

      ffArgs = [
        '-i', avatarPath,
        '-i', recordingPath,
        '-filter_complex', filterComplex,
        '-map', mapVideo,
        '-map', '0:a?',
        ...ENCODER_FINAL,
        '-c:a', 'aac', '-b:a', '128k',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        '-t', String(totalDur),
        '-y', outputPath
      ];
    } else {
      const subFilter = subPath ? `,ass=${subPathFF}` : '';
      ffArgs = [
        '-i', recordingPath,
        '-vf', `scale=${outWidth}:${outHeight}:force_original_aspect_ratio=decrease,pad=${outWidth}:${outHeight}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13,setsar=1${subFilter}`,
        ...ENCODER_FINAL,
        '-c:a', 'aac', '-b:a', '128k',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        '-t', String(Math.min(probeDur, 60)),
        '-y', outputPath
      ];
    }

    console.log(`[${jobId}] FFmpeg Pro start (mode: ${mode}, avatar: ${!!avatarPath}, intro: ${avatarIntroFullscreen ? 'yes' : 'no'})...`);
    await new Promise((resolve, reject) => {
      // v1.1.2 — cwd=tmpDir pour que le filter `ass=subs.ass` (relative) marche sur Windows.
      const ff = spawn('ffmpeg', ffArgs, { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true, cwd: tmpDir });
      let stderr = '';
      ff.stderr.on('data', d => { stderr += d.toString(); });
      ff.on('close', code => {
        if (code === 0) resolve();
        else reject(new Error(`FFmpeg Pro exit ${code}: ${stderr.slice(-500)}`));
      });
      ff.on('error', reject);
      setTimeout(() => {
        try { ff.kill('SIGKILL'); } catch (_) {}
        reject(new Error('FFmpeg Pro timeout 180s'));
      }, 180000);
    });

    // v1.1.13 — Hook visuel 3s intro : drawtext anime fade-in/hold/fade-out sur 0-3s.
    // Post-process apres main ffmpeg (modulaire, n'affecte pas filter_complex existant).
    // Kimi TOP 1 vote 3-LLM 17/05 roadmap viralite TikTok 2026 (scroll-stop 80% des swipes en 3s).
    if (hookText && typeof hookText === 'string' && hookText.trim().length > 0) {
      const hookRaw = hookText.trim().slice(0, 120);  // max 120 char input

      // v1.1.14 — Auto-wrap word-boundary : pour fontsize=80px sur outWidth=1080,
      // ~22 chars/ligne tient confortablement avec marge 8% chaque cote. Max 3 lignes,
      // sinon truncate avec ellipsis. ffmpeg drawtext rend nativement le multi-ligne
      // depuis textfile (line-height auto = fontsize * 1.2).
      const MAX_CHARS_PER_LINE = Math.max(14, Math.round(outWidth / 50));  // ~22 sur 1080, ~14 sur 720
      const MAX_LINES = 3;
      function wrapHook(text, maxChars, maxLines) {
        const words = text.split(/\s+/);
        const lines = [];
        let current = '';
        for (const w of words) {
          const candidate = current ? (current + ' ' + w) : w;
          if (candidate.length <= maxChars) {
            current = candidate;
          } else {
            if (current) lines.push(current);
            current = w.length > maxChars ? w.slice(0, maxChars - 1) + '…' : w;
            if (lines.length >= maxLines) break;
          }
        }
        if (current && lines.length < maxLines) lines.push(current);
        if (lines.length === maxLines) {
          // Ellipsis si truncate
          const lastIdx = lines.length - 1;
          const allText = lines.join(' ');
          if (allText.length < text.length) {
            lines[lastIdx] = lines[lastIdx].replace(/\W*$/, '') + '…';
          }
        }
        return lines.join('\n');
      }
      const hookWrapped = wrapHook(hookRaw, MAX_CHARS_PER_LINE, MAX_LINES);
      const nLines = hookWrapped.split('\n').length;
      console.log(`[${jobId}] Hook intro 3s : "${hookRaw}" → wrapped ${nLines} lines (${MAX_CHARS_PER_LINE} chars/line max)`);

      // Copie font Arial Bold dans tmpDir (path relatif robuste cwd=tmpDir)
      const fontSrc = 'C:\\Windows\\Fonts\\arialbd.ttf';
      const fontDst = path.join(tmpDir, 'hook_font.ttf');
      try { fs.copyFileSync(fontSrc, fontDst); }
      catch (e) { console.log(`[${jobId}] WARN font copy failed: ${e.message} — fallback sans fontfile`); }
      const fontfileArg = fs.existsSync(fontDst) ? 'fontfile=hook_font.ttf:' : '';

      // Texte via fichier (textfile=) pour eviter problemes d'escape ' : , \ dans drawtext
      // v1.1.14 — Multi-ligne via \n dans hook.txt (drawtext rend natif line-height auto).
      const hookFile = path.join(tmpDir, 'hook.txt');
      fs.writeFileSync(hookFile, hookWrapped, 'utf-8');

      // Animation alpha : fade-in 0.4s, hold, fade-out 0.4s avant t=3
      const alphaExpr = 'if(lt(t,0.4),t/0.4,if(lt(t,2.6),1,if(lt(t,3),(3-t)/0.4,0)))';
      const fontsize = Math.round(outWidth * 0.075);  // ~80px sur 1080
      const drawFilter = (
        `drawtext=${fontfileArg}` +
        `textfile=hook.txt:reload=0:` +
        `fontsize=${fontsize}:fontcolor=white:` +
        `borderw=4:bordercolor=black:` +
        `x=(w-text_w)/2:y=h*0.18:` +
        `box=1:boxcolor=black@0.35:boxborderw=18:` +
        `alpha='${alphaExpr}':` +
        `enable='lt(t,3)'`
      );
      console.log(`[${jobId}] Hook drawtext filter: ${drawFilter.slice(0, 200)}...`);

      const withHookPath = path.join(tmpDir, 'with_hook.mp4');
      await new Promise((resolve, reject) => {
        const ff = spawn('ffmpeg', [
          '-i', outputPath,
          '-vf', drawFilter,
          ...ENCODER_FAST, '-pix_fmt', 'yuv420p',
          '-c:a', 'copy',
          '-movflags', '+faststart',
          '-y', withHookPath
        ], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true, cwd: tmpDir });
        let stderr = '';
        ff.stderr.on('data', d => { stderr += d.toString(); });
        ff.on('close', code => {
          if (code === 0) resolve();
          else reject(new Error(`Hook drawtext exit ${code}: ${stderr.slice(-400)}`));
        });
        ff.on('error', reject);
        setTimeout(() => { try { ff.kill('SIGKILL'); } catch(_){} reject(new Error('Hook drawtext timeout 60s')); }, 60000);
      });
      // Remplace outputPath par la version avec hook (pipeline outro continue inchange)
      fs.renameSync(withHookPath, outputPath);
      console.log(`[${jobId}] Hook intro 3s applied OK`);
    }

    // v1.1.15 — #10 Sound design SFX : whoosh transition + ding outro (post-process audio).
    // Default OFF. Body param sfxEnabled=true requis. Skip whoosh si pas d'intro avatar fullscreen.
    if (sfxEnabled && fs.existsSync(SFX_WHOOSH) && fs.existsSync(SFX_DING)) {
      // Re-probe la duree exacte du output (peut differ post hook re-encoding)
      const curDur = await new Promise((resolve) => {
        const ff = spawn('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', outputPath], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
        let out = '';
        ff.stdout.on('data', d => { out += d.toString(); });
        ff.on('close', code => resolve(code === 0 ? (parseFloat(out.trim()) || 30) : 30));
        ff.on('error', () => resolve(30));
        setTimeout(() => { try { ff.kill(); } catch(_){} resolve(30); }, 5000);
      });

      // v1.1.15 — Detect audio stream presence (en prod le mode Pro a toujours audio
      // depuis avatar + recording, mais skip propre si absent pour robustesse).
      const hasAudioStream = await new Promise((resolve) => {
        const ff = spawn('ffprobe', ['-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=codec_name', '-of', 'csv=p=0', outputPath], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
        let out = '';
        ff.stdout.on('data', d => { out += d.toString(); });
        ff.on('close', () => resolve(out.trim().length > 0));
        ff.on('error', () => resolve(false));
        setTimeout(() => { try { ff.kill(); } catch(_){} resolve(false); }, 3000);
      });
      if (!hasAudioStream) {
        console.log(`[${jobId}] SFX skip: video has no audio stream (no source to mix with)`);
      } else {

      const introDurEff = avatarIntroFullscreen ? Math.max(1, Math.min(5, parseInt(avatarIntroDuration) || 2)) : 0;
      const whooshAtMs = introDurEff > 0 ? Math.max(0, Math.round((introDurEff - 0.2) * 1000)) : -1;  // -1 = skip whoosh
      const dingAtMs = Math.max(0, Math.round((curDur - 0.32) * 1000));

      console.log(`[${jobId}] SFX : curDur=${curDur.toFixed(2)}s, whoosh@${whooshAtMs}ms (skip=${whooshAtMs<0}), ding@${dingAtMs}ms`);

      // Construction filter_complex selon whether whoosh present
      let fcParts = [];
      let amixInputs = ['[0:a]'];  // video audio
      let inputArgs = ['-i', outputPath, '-i', SFX_DING];  // ding always in
      let dingInputIdx = 1;
      if (whooshAtMs >= 0) {
        inputArgs.push('-i', SFX_WHOOSH);
        const whooshInputIdx = 2;
        fcParts.push(`[${whooshInputIdx}:a]adelay=${whooshAtMs}|${whooshAtMs},volume=0.45[w]`);
        amixInputs.push('[w]');
      }
      fcParts.push(`[${dingInputIdx}:a]adelay=${dingAtMs}|${dingAtMs},volume=0.55[d]`);
      amixInputs.push('[d]');
      fcParts.push(`${amixInputs.join('')}amix=inputs=${amixInputs.length}:normalize=0:duration=first[aout]`);
      const fcSfx = fcParts.join(';');

      const withSfxPath = path.join(tmpDir, 'with_sfx.mp4');
      await new Promise((resolve, reject) => {
        const ff = spawn('ffmpeg', [
          ...inputArgs,
          '-filter_complex', fcSfx,
          '-map', '0:v', '-map', '[aout]',
          '-c:v', 'copy',  // video inchangee (audio only modif)
          '-c:a', 'aac', '-b:a', '128k',
          '-movflags', '+faststart',
          '-y', withSfxPath
        ], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true, cwd: tmpDir });
        let stderr = '';
        ff.stderr.on('data', d => { stderr += d.toString(); });
        ff.on('close', code => {
          if (code === 0) resolve();
          else reject(new Error(`SFX mix exit ${code}: ${stderr.slice(-400)}`));
        });
        ff.on('error', reject);
        setTimeout(() => { try { ff.kill('SIGKILL'); } catch(_){} reject(new Error('SFX mix timeout 60s')); }, 60000);
      });
      fs.renameSync(withSfxPath, outputPath);
      console.log(`[${jobId}] SFX applied OK`);
      }  // end else (hasAudioStream)
    } else if (sfxEnabled) {
      console.log(`[${jobId}] WARN sfxEnabled but SFX files missing (whoosh.wav OR ding.wav)`);
    }

    // v1.1.17 — #19 Loop Hook <=5s : boomerang forward+reverse pour boucle parfaite TikTok.
    // Trim video à 2.5s max + concat avec reverse = 5s total avec last frame = first frame.
    // Audio : original 2.5s répété 2× (au lieu de reverse audio bizarre).
    if (loopHookEnabled) {
      console.log(`[${jobId}] Loop Hook <=5s : applying boomerang (trim 2.5s + reverse concat)...`);
      const loopFilter = (
        '[0:v]trim=0:2.5,setpts=PTS-STARTPTS,split=2[vf][vr_src];' +
        '[vr_src]reverse,setpts=PTS-STARTPTS[vr];' +
        '[vf][vr]concat=n=2:v=1:a=0[outv];' +
        '[0:a]atrim=0:2.5,asetpts=PTS-STARTPTS,asplit=2[af][af2];' +
        '[af][af2]concat=n=2:v=0:a=1[outa]'
      );
      const withLoopPath = path.join(tmpDir, 'with_loop.mp4');
      // Check audio presence first (skip audio chain si absent)
      const loopHasAudio = await new Promise((resolve) => {
        const ff = spawn('ffprobe', ['-v', 'error', '-select_streams', 'a:0', '-show_entries', 'stream=codec_name', '-of', 'csv=p=0', outputPath], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
        let out = '';
        ff.stdout.on('data', d => { out += d.toString(); });
        ff.on('close', () => resolve(out.trim().length > 0));
        ff.on('error', () => resolve(false));
        setTimeout(() => { try { ff.kill(); } catch(_){} resolve(false); }, 3000);
      });
      const loopFilterFinal = loopHasAudio ? loopFilter : (
        '[0:v]trim=0:2.5,setpts=PTS-STARTPTS,split=2[vf][vr_src];' +
        '[vr_src]reverse,setpts=PTS-STARTPTS[vr];' +
        '[vf][vr]concat=n=2:v=1:a=0[outv]'
      );
      const loopMaps = loopHasAudio ? ['-map', '[outv]', '-map', '[outa]'] : ['-map', '[outv]'];
      await new Promise((resolve, reject) => {
        const ff = spawn('ffmpeg', [
          '-i', outputPath,
          '-filter_complex', loopFilterFinal,
          ...loopMaps,
          ...ENCODER_FAST, '-pix_fmt', 'yuv420p',
          ...(loopHasAudio ? ['-c:a', 'aac', '-b:a', '128k'] : []),
          '-movflags', '+faststart',
          '-y', withLoopPath
        ], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true, cwd: tmpDir });
        let stderr = '';
        ff.stderr.on('data', d => { stderr += d.toString(); });
        ff.on('close', code => {
          if (code === 0) resolve();
          else reject(new Error(`Loop boomerang exit ${code}: ${stderr.slice(-400)}`));
        });
        ff.on('error', reject);
        setTimeout(() => { try { ff.kill('SIGKILL'); } catch(_){} reject(new Error('Loop boomerang timeout 90s')); }, 90000);
      });
      fs.renameSync(withLoopPath, outputPath);
      console.log(`[${jobId}] Loop Hook boomerang applied OK (5s total, has_audio=${loopHasAudio})`);
    }

    // v1.1.16 — #13 LUT brand DictoKey : color grading subtle vers palette brand
    // (violet #7C3AED + dark #0F0F13). Approche pragmatique sans .cube : eq + colorbalance ffmpeg.
    // Effet : boost bleu+rouge midtones/highlights, dark shadows, saturation +10%. Non destructif.
    if (lutBrandEnabled) {
      console.log(`[${jobId}] LUT brand DictoKey : applying color grading...`);
      // eq=contrast=1.05 : très subtil boost contraste
      // eq=saturation=1.08 : très subtil boost saturation (couleurs plus vives sans cartoon)
      // colorbalance=rs=0.04:bs=0.10 : shadows shift rouge+bleu (= violet) léger
      // colorbalance=rm=0.02:bm=0.06 : midtones shift rouge+bleu plus léger encore
      // gamma_b=1.08 : boost bleu global (= ambiance dark+violet)
      const lutFilter = 'eq=contrast=1.05:saturation=1.08:gamma_b=1.08,colorbalance=rs=0.04:bs=0.10:rm=0.02:bm=0.06';
      const withLutPath = path.join(tmpDir, 'with_lut.mp4');
      await new Promise((resolve, reject) => {
        const ff = spawn('ffmpeg', [
          '-i', outputPath,
          '-vf', lutFilter,
          ...ENCODER_FAST, '-pix_fmt', 'yuv420p',
          '-c:a', 'copy',
          '-movflags', '+faststart',
          '-y', withLutPath
        ], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true, cwd: tmpDir });
        let stderr = '';
        ff.stderr.on('data', d => { stderr += d.toString(); });
        ff.on('close', code => {
          if (code === 0) resolve();
          else reject(new Error(`LUT brand exit ${code}: ${stderr.slice(-400)}`));
        });
        ff.on('error', reject);
        setTimeout(() => { try { ff.kill('SIGKILL'); } catch(_){} reject(new Error('LUT brand timeout 60s')); }, 60000);
      });
      fs.renameSync(withLutPath, outputPath);
      console.log(`[${jobId}] LUT brand applied OK`);
    }

    // v1.1.26 — #14 Ken Burns POST-PROCESS : zoom-in CENTRE 1.00 -> 1.04 progressif sur
    // toute la duree finale. Subtile = sujet reste centre, juste un effet cinema vivant
    // (evite l'aspect "video figee 9:16"). En post-process pour fiabilite zoompan + simplicite.
    // Toggle kenBurnsEnabled, default OFF.
    if (kenBurnsEnabled) {
      console.log(`[${jobId}] Ken Burns subtle 1.00 -> 1.06 : applying centered zoom-in...`);
      // Probe duree actuelle pour calculer increment par frame
      const kbDur = await new Promise((resolve) => {
        const ff = spawn('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', outputPath], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
        let out = '';
        ff.stdout.on('data', d => { out += d.toString(); });
        ff.on('close', () => resolve(parseFloat(out.trim()) || 0));
        ff.on('error', () => resolve(0));
        setTimeout(() => { try { ff.kill(); } catch(_){} resolve(0); }, 5000);
      });
      if (kbDur < 1.5) {
        console.log(`[${jobId}] Ken Burns SKIP : duree ${kbDur.toFixed(1)}s < 1.5s (eviter zoom abrupt)`);
      } else {
        const totalFrames = Math.max(45, Math.round(kbDur * 30));
        const inc = (0.06 / totalFrames).toFixed(7);
        // zoompan en -vf simple (1 input, fiable) ; centre strict via x/y
        const kbFilter = `zoompan=z='min(zoom+${inc}\\,1.06)':d=1:fps=30:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${outWidth}x${outHeight}`;
        const withKbPath = path.join(tmpDir, 'with_kenburns.mp4');
        await new Promise((resolve, reject) => {
          const ff = spawn('ffmpeg', [
            '-i', outputPath,
            '-vf', kbFilter,
            ...ENCODER_FAST, '-pix_fmt', 'yuv420p',
            '-c:a', 'copy',
            '-movflags', '+faststart',
            '-y', withKbPath
          ], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true, cwd: tmpDir });
          let stderr = '';
          ff.stderr.on('data', d => { stderr += d.toString(); });
          ff.on('close', code => {
            if (code === 0) resolve();
            else reject(new Error(`Ken Burns exit ${code}: ${stderr.slice(-400)}`));
          });
          ff.on('error', reject);
          setTimeout(() => { try { ff.kill('SIGKILL'); } catch(_){} reject(new Error('Ken Burns timeout 90s')); }, 90000);
        });
        fs.renameSync(withKbPath, outputPath);
        console.log(`[${jobId}] Ken Burns applied OK (${totalFrames} frames, inc=${inc})`);
      }
    }

    // v1.1.26 — #14 Vignette douce : assombrissement subtil des coins (cinema-like).
    // angle=PI/5 = 36deg = vignette douce ; eval=init = calcul une fois (perf).
    // mode=forward = darkening (default). Toggle vignetteEnabled, default OFF.
    if (vignetteEnabled) {
      console.log(`[${jobId}] Vignette douce : applying soft corner darkening...`);
      const vignFilter = 'vignette=angle=PI/5:mode=forward:eval=init';
      const withVignPath = path.join(tmpDir, 'with_vignette.mp4');
      await new Promise((resolve, reject) => {
        const ff = spawn('ffmpeg', [
          '-i', outputPath,
          '-vf', vignFilter,
          ...ENCODER_FAST, '-pix_fmt', 'yuv420p',
          '-c:a', 'copy',
          '-movflags', '+faststart',
          '-y', withVignPath
        ], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true, cwd: tmpDir });
        let stderr = '';
        ff.stderr.on('data', d => { stderr += d.toString(); });
        ff.on('close', code => {
          if (code === 0) resolve();
          else reject(new Error(`Vignette exit ${code}: ${stderr.slice(-400)}`));
        });
        ff.on('error', reject);
        setTimeout(() => { try { ff.kill('SIGKILL'); } catch(_){} reject(new Error('Vignette timeout 60s')); }, 60000);
      });
      fs.renameSync(withVignPath, outputPath);
      console.log(`[${jobId}] Vignette applied OK`);
    }

    // Outro image assembly (optional)
    if (outroClip) {
      const XFADE_DUR = 0.3;
      const clips = [];

      const actualMainDur = await new Promise((resolve) => {
        const ff = spawn('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', outputPath], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
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
            ...ENCODER_FAST, '-pix_fmt', 'yuv420p',
            '-t', String(oDur), '-y', outroVidPath
          ], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
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
            ...ENCODER_FINAL,
            '-c:a', 'aac', '-b:a', '128k', '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart', '-y', finalPath
          ], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
          let stderr = '';
          ff.stderr.on('data', d => { stderr += d.toString(); });
          ff.on('close', code => code === 0 ? resolve() : reject(new Error('Xfade Pro: ' + stderr.slice(-300))));
          ff.on('error', reject);
          setTimeout(() => { try { ff.kill('SIGKILL'); } catch(_){} reject(new Error('Xfade Pro timeout 180s')); }, 180000);
        });
        fs.renameSync(finalPath, outputPath);
        console.log(`[${jobId}] Intro/Outro xfade OK`);
      }
    }

    // v1.1.12 — Jump cuts auto silences (Kimi #1 vote 17/05 : rétention TikTok #1 facteur 2026).
    // Post-process : silencedetect sur l'audio → liste segments à garder → trim+concat.
    // Le subs ASS est déjà burned dans outputPath donc reste sync avec l'audio raccourci.
    if (jumpCutsEnabled) {
      console.log(`[${jobId}] Jump cuts auto silences : analyse audio...`);
      const SILENCE_THRESHOLD_DB = -30;
      const SILENCE_MIN_DURATION = 0.4;
      // 1. silencedetect (parse stderr)
      const silences = await new Promise((resolve) => {
        const ff = spawn('ffmpeg', ['-i', outputPath, '-af',
          `silencedetect=noise=${SILENCE_THRESHOLD_DB}dB:d=${SILENCE_MIN_DURATION}`,
          '-f', 'null', '-'], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
        let stderr = '';
        ff.stderr.on('data', d => stderr += d.toString());
        ff.on('close', () => {
          const out = [];
          const startRe = /silence_start:\s*([\d.]+)/g;
          const endRe = /silence_end:\s*([\d.]+)/g;
          const starts = [...stderr.matchAll(startRe)].map(m => parseFloat(m[1]));
          const ends = [...stderr.matchAll(endRe)].map(m => parseFloat(m[1]));
          for (let i = 0; i < starts.length; i++) {
            out.push({ start: starts[i], end: ends[i] != null ? ends[i] : starts[i] + SILENCE_MIN_DURATION });
          }
          resolve(out);
        });
        ff.on('error', () => resolve([]));
        setTimeout(() => { try { ff.kill(); } catch(_){} resolve([]); }, 60000);
      });
      console.log(`[${jobId}] Silences détectés : ${silences.length}`);
      if (silences.length > 0) {
        // 2. Build segments à garder (inverser les silences)
        // ffprobe duration totale
        const totalDur = await new Promise((resolve) => {
          const ff = spawn('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', outputPath], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
          let out = ''; ff.stdout.on('data', d => out += d.toString());
          ff.on('close', () => resolve(parseFloat(out.trim()) || 0));
          ff.on('error', () => resolve(0));
          setTimeout(() => { try { ff.kill(); } catch(_){} resolve(0); }, 5000);
        });
        // Marges de 0.05s autour des silences pour ne pas couper net
        const MARGIN = 0.05;
        const keepSegs = [];
        let cursor = 0;
        for (const s of silences) {
          const segStart = cursor;
          const segEnd = Math.max(cursor, s.start - MARGIN);
          if (segEnd - segStart > 0.05) keepSegs.push([segStart, segEnd]);
          cursor = s.end + MARGIN;
        }
        if (totalDur > cursor + 0.05) keepSegs.push([cursor, totalDur]);
        if (keepSegs.length > 0) {
          // Build select/aselect expressions
          const selectExpr = keepSegs.map(([a, b]) => `between(t,${a.toFixed(3)},${b.toFixed(3)})`).join('+');
          const cutPath = path.join(tmpDir, 'jumpcut.mp4');
          await new Promise((resolve, reject) => {
            const ff = spawn('ffmpeg', ['-i', outputPath,
              '-vf', `select='${selectExpr}',setpts=N/FRAME_RATE/TB`,
              '-af', `aselect='${selectExpr}',asetpts=N/SR/TB`,
              ...ENCODER_FINAL,
              '-c:a', 'aac', '-b:a', '128k',
              '-pix_fmt', 'yuv420p',
              '-movflags', '+faststart',
              '-y', cutPath
            ], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
            let stderr = '';
            ff.stderr.on('data', d => stderr += d.toString());
            ff.on('close', code => code === 0 ? resolve() : reject(new Error(`JumpCut exit ${code}: ${stderr.slice(-300)}`)));
            ff.on('error', reject);
            setTimeout(() => { try { ff.kill('SIGKILL'); } catch(_){} reject(new Error('JumpCut timeout 120s')); }, 120000);
          });
          const cutStat = fs.statSync(cutPath);
          const savedSec = (totalDur - keepSegs.reduce((a, [s, e]) => a + (e - s), 0)).toFixed(2);
          console.log(`[${jobId}] Jump cuts OK : ${keepSegs.length} segments gardés, ${savedSec}s économisés`);
          fs.renameSync(cutPath, outputPath);
        }
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
// POST /promo-assembly-split — Split-Screen Frustration (killer feature DictoKey)
// v1.1.7 — vote 3-LLM 16/05 (Kimi #1) : démontre la valeur produit en un visuel viral.
// Vstack vertical : top = capture saisie manuelle slow, bottom = capture dictée DictoKey.
// Labels "AVANT — Manuel" / "APRÈS — DictoKey" + voiceover live commentary + subs.
// ---------------------------------------------------------------------------
app.post('/promo-assembly-split', jsonLarge, requireAnySecret, async (req, res) => {
  const jobId = `pas-${Date.now().toString(36)}`;
  console.log(`[${jobId}] /promo-assembly-split start`);

  if (activeJobs >= MAX_CONCURRENT_JOBS) {
    return res.status(503).json({ error: 'Server busy, try again later' });
  }

  const {
    videoLeft, videoLeftMime, videoRight, videoRightMime,
    audio, subtitles,
    leftLabel, rightLabel,
    width = 1080, height = 1920,
  } = req.body;

  if (!videoLeft || !videoRight) {
    return res.status(400).json({ error: 'videoLeft and videoRight (base64) both required' });
  }

  const tmpDir = path.join(os.tmpdir(), jobId);
  let jobCounted = false;
  try {
    fs.mkdirSync(tmpDir, { recursive: true });
    activeJobs++;
    jobCounted = true;
    resetIdleTimer();

    // 1. Write inputs
    const extL = (videoLeftMime || '').includes('webm') ? 'webm' : 'mp4';
    const extR = (videoRightMime || '').includes('webm') ? 'webm' : 'mp4';
    const leftPath = path.join(tmpDir, `left.${extL}`);
    const rightPath = path.join(tmpDir, `right.${extR}`);
    fs.writeFileSync(leftPath, Buffer.from(videoLeft, 'base64'));
    fs.writeFileSync(rightPath, Buffer.from(videoRight, 'base64'));
    console.log(`[${jobId}] Inputs: left=${(fs.statSync(leftPath).size / 1048576).toFixed(1)}MB right=${(fs.statSync(rightPath).size / 1048576).toFixed(1)}MB`);

    // Audio (voiceover) optional
    let audioPath = null;
    if (audio) {
      audioPath = path.join(tmpDir, 'voice.mp3');
      fs.writeFileSync(audioPath, Buffer.from(audio, 'base64'));
    }

    // Subtitles
    let subPath = null;
    let subPathFF = null;
    if (subtitles) {
      subPath = path.join(tmpDir, 'subs.ass');
      subPathFF = 'subs.ass';
      fs.writeFileSync(subPath, subtitles, 'utf8');
    }

    // 2. Probe durations
    const probeDur = (p) => new Promise((resolve) => {
      const ff = spawn('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p], { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true });
      let out = '';
      ff.stdout.on('data', d => out += d.toString());
      ff.on('close', code => resolve(code === 0 ? (parseFloat(out.trim()) || 0) : 0));
      ff.on('error', () => resolve(0));
      setTimeout(() => { try { ff.kill(); } catch(_){} resolve(0); }, 5000);
    });
    const [leftDur, rightDur] = await Promise.all([probeDur(leftPath), probeDur(rightPath)]);
    const totalDur = Math.min(60, Math.max(leftDur, rightDur) || 14);
    console.log(`[${jobId}] Durations: left=${leftDur.toFixed(2)}s right=${rightDur.toFixed(2)}s -> total=${totalDur.toFixed(2)}s`);

    // 3. Build filter complex : vstack top/bottom + labels + subs
    const halfH = Math.floor(height / 2);
    // Escape labels for drawtext (single quotes + colons need backslash)
    const escDt = (s) => (s || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/:/g, '\\:');
    const lLabel = escDt(leftLabel || 'AVANT — Manuel');
    const rLabel = escDt(rightLabel || 'APRÈS — DictoKey');

    // Each input : scale+pad to width x halfH, then drawtext label top-left
    // tpad to make sure each stream lasts totalDur (loop last frame if shorter)
    const leftFilter = [
      `[0:v]scale=${width}:${halfH}:force_original_aspect_ratio=decrease`,
      `pad=${width}:${halfH}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13`,
      `setsar=1,fps=30`,
      `tpad=stop_mode=clone:stop_duration=${Math.max(0, totalDur - leftDur).toFixed(2)}`,
      `drawtext=text='${lLabel}':fontsize=42:fontcolor=white:fontfile='/Windows/Fonts/arialbd.ttf':box=1:boxcolor=#EF4444@0.85:boxborderw=10:x=20:y=20`
    ].join(',') + '[top]';

    const rightFilter = [
      `[1:v]scale=${width}:${halfH}:force_original_aspect_ratio=decrease`,
      `pad=${width}:${halfH}:(ow-iw)/2:(oh-ih)/2:color=0x0F0F13`,
      `setsar=1,fps=30`,
      `tpad=stop_mode=clone:stop_duration=${Math.max(0, totalDur - rightDur).toFixed(2)}`,
      `drawtext=text='${rLabel}':fontsize=42:fontcolor=white:fontfile='/Windows/Fonts/arialbd.ttf':box=1:boxcolor=#14B8A6@0.85:boxborderw=10:x=20:y=20`
    ].join(',') + '[bot]';

    // Vstack + draw separator + subs overlay
    const vstack = `[top][bot]vstack=inputs=2[stacked]`;
    // Separator : 4px teal line at y=halfH
    const sep = `[stacked]drawbox=y=${halfH - 2}:w=${width}:h=4:color=#14B8A6@0.9:t=fill[outv]`;
    const subFilter = subPathFF ? `;[outv]ass=${subPathFF}[final]` : '';
    const mapVideo = subFilter ? '[final]' : '[outv]';

    const filterComplex = [leftFilter, rightFilter, vstack, sep].join(';') + subFilter;

    // 4. ffmpeg command : 2 video inputs + optional audio + filter graph
    const outputPath = path.join(tmpDir, 'output.mp4');
    const ffArgs = ['-i', leftPath, '-i', rightPath];
    if (audioPath) ffArgs.push('-i', audioPath);
    ffArgs.push(
      '-filter_complex', filterComplex,
      '-map', mapVideo,
    );
    if (audioPath) {
      ffArgs.push('-map', '2:a');
    }
    ffArgs.push(
      ...ENCODER_FINAL,
      '-c:a', 'aac', '-b:a', '128k',
      '-pix_fmt', 'yuv420p',
      '-movflags', '+faststart',
      '-t', String(totalDur),
      '-y', outputPath
    );

    console.log(`[${jobId}] FFmpeg split start...`);
    await new Promise((resolve, reject) => {
      const ff = spawn('ffmpeg', ffArgs, { stdio: ['ignore', 'pipe', 'pipe'], windowsHide: true, cwd: tmpDir });
      let stderr = '';
      ff.stderr.on('data', d => stderr += d.toString());
      ff.on('close', code => code === 0 ? resolve() : reject(new Error(`split exit ${code}: ${stderr.slice(-500)}`)));
      ff.on('error', reject);
      setTimeout(() => { try { ff.kill('SIGKILL'); } catch(_){} reject(new Error('split timeout 120s')); }, 120000);
    });

    // 5. Stream output
    const stat = fs.statSync(outputPath);
    res.setHeader('Content-Type', 'video/mp4');
    res.setHeader('Content-Length', stat.size);
    res.setHeader('X-Job-Id', jobId);
    const stream = fs.createReadStream(outputPath);
    stream.pipe(res);
    stream.on('end', () => {
      try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
      console.log(`[${jobId}] DONE ${(stat.size / 1048576).toFixed(1)}MB`);
    });
    stream.on('error', () => {
      try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    });
  } catch (e) {
    console.error(`[${jobId}] ERR:`, e.message);
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    if (!res.headersSent) res.status(500).json({ error: e.message });
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
