/**
 * SubWhisper Fly.io FFmpeg Server
 * Version: 1.26.0 — Added /smart-zoom, /speed-ramp, /promo-assembly for PromoClip
 *
 * Fixes v1.1.0:
 *  - Remplacé form-data npm par native FormData+Blob (Node 20 globals)
 *    → corrige "multipart: NextPart: EOF" chez Groq
 *  - Chunks traités séquentiellement dans end handler au lieu de concurrents dans data handler
 *    → corrige unhandled promise rejection → crash Node.js sans callback d'erreur
 * Fixes v1.2.0:
 *  - Buffer.concat O(n²) → array accumulation + concat unique dans end handler
 * Fixes v1.3.0:
 *  - const pcmAccum → let pcmAccum (TypeError assignment to const)
 * Fixes v1.4.0:
 *  - Groq HTTP 429 : parse "try again in Xm Y.Zs" et attend exactement ce délai
 *  - MAX_RETRIES 3→5 pour couvrir plusieurs fenêtres de rate limit
 * Fixes v1.5.0:
 *  - Groq Whisper hallucine parfois seg.end >> durée du chunk (ex: 9min→1h00)
 *    → clamp seg.end à chunkDurationSec avant d'ajouter offsetSec
 *    → passe chunkDurationSec = pcmChunk.length/32000 à transcribeWithGroq
 * Fixes v1.6.0:
 *  - Groq Whisper hallucine parfois des segments de durée modérée (ex: 51.9s) dans un boundary chunk
 *    → non corrigés par le clamp v1.5.0 (le segment reste dans la durée du chunk)
 *    → cap 30s max par segment : Math.min(seg.end, relStart+30, maxRelEnd)
 * Fixes v1.7.0:
 *  - Groq Whisper hallucine seg.start >= chunkDurationSec → timestamps finaux > durée vidéo
 *    → ex: chunk de 786s, seg.start=820s → offset+820 >> durée vidéo
 *    → filtre : skip les segments dont relStart >= maxRelEnd (hors frontière chunk)
 */

'use strict';

const express = require('express');
const { spawn } = require('child_process');
const https = require('https');
const fs = require('fs');
const path = require('path');
const os = require('os');
// Note: FormData et Blob sont des globals Node.js 20+, pas besoin de require

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const PORT = parseInt(process.env.PORT || '3000', 10);
const FLY_SECRET = process.env.FLY_SECRET || '';
const MAX_CONCURRENT_JOBS = parseInt(process.env.MAX_CONCURRENT_JOBS || '2', 10);

// Groq rate limit: 15 req/min → min 4s entre appels
const GROQ_MIN_INTERVAL_MS = 4000;

// Taille max d'un chunk WAV: 24 MB
// PCM s16le = 2 bytes/sample, 16000 samples/sec = 32000 bytes/sec
const CHUNK_MAX_BYTES = Math.floor((24 * 1024 * 1024 - 44) / 2) * 2; // ~24MB WAV - 44 bytes header
const CHUNK_DUR_SEC = CHUNK_MAX_BYTES / 32000; // durée en secondes du chunk PCM

// Groq
const GROQ_ENDPOINT = 'https://api.groq.com/openai/v1/audio/transcriptions';
const GROQ_MODEL = 'whisper-large-v3-turbo';

// ---------------------------------------------------------------------------
// État global
// ---------------------------------------------------------------------------

let activeJobs = 0;
const startTime = Date.now();

// ---------------------------------------------------------------------------
// Auto-shutdown : éteindre la machine après IDLE_SHUTDOWN_MS sans jobs actifs
// Nécessaire car auto_stop_machines = "off" (empêche Fly.io de tuer les jobs)
// ---------------------------------------------------------------------------
const IDLE_SHUTDOWN_MS = 30 * 60 * 1000; // 30 minutes
let idleTimer = null;

function resetIdleTimer() {
  if (idleTimer) clearTimeout(idleTimer);
  if (activeJobs > 0) return; // pas de timer si jobs actifs
  idleTimer = setTimeout(() => {
    if (activeJobs === 0) {
      console.log(`[AUTO-SHUTDOWN] Aucun job depuis ${IDLE_SHUTDOWN_MS / 60000}min — arrêt du serveur.`);
      process.exit(0); // Fly.io redémarrera la machine à la prochaine requête (auto_start_machines=true)
    }
  }, IDLE_SHUTDOWN_MS);
}
// Démarrer le timer dès le boot
resetIdleTimer();

// ---------------------------------------------------------------------------
// Startup cleanup: supprimer les dossiers /data/hls_* orphelins
// (survivent aux redémarrages car le volume /data est persistant)
// ---------------------------------------------------------------------------
function cleanupOrphanDirs() {
  const hlsBase = fs.existsSync('/data') ? '/data' : null;
  if (!hlsBase) return;
  try {
    const entries = fs.readdirSync(hlsBase);
    let cleaned = 0;
    for (const entry of entries) {
      if (entry.startsWith('hls_')) {
        const fullPath = path.join(hlsBase, entry);
        try {
          fs.rmSync(fullPath, { recursive: true, force: true });
          cleaned++;
          console.log(`[STARTUP-CLEANUP] Supprime orphelin: ${entry}`);
        } catch (e) {}
      }
    }
    if (cleaned > 0) console.log(`[STARTUP-CLEANUP] ${cleaned} dossier(s) orphelin(s) nettoye(s)`);
  } catch (e) {
    console.error('[STARTUP-CLEANUP] Erreur:', e.message);
  }
}
cleanupOrphanDirs();

// ---------------------------------------------------------------------------
// App Express
// ---------------------------------------------------------------------------

const app = express();

// CORS middleware global — DOIT être avant toutes les routes
app.use((req, res, next) => {
  res.set({
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS, DELETE',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  });
  if (req.method === 'OPTIONS') return res.status(204).end();
  next();
});

app.use(express.json({ limit: '50mb' }));

// Auth middleware that accepts FLY_SECRET or WORKER_SECRET (header or query param ?s=)
function requireAnySecret(req, res, next) {
  const auth = req.headers['authorization'] || '';
  const token = auth.startsWith('Bearer ') ? auth.slice(7) : (req.query.s || '');
  if (!token) return res.status(401).json({ error: 'Missing Authorization' });
  const flySecret = process.env.FLY_SECRET || '';
  const workerSecret = process.env.WORKER_SECRET || '';
  if ((flySecret && token === flySecret) || (workerSecret && token === workerSecret)) return next();
  if (!flySecret && !workerSecret) return next(); // dev mode
  return res.status(401).json({ error: 'Unauthorized' });
}

// ---------------------------------------------------------------------------
// Middleware auth
// ---------------------------------------------------------------------------

function requireFlySecret(req, res, next) {
  if (!FLY_SECRET) {
    console.warn('[WARN] FLY_SECRET non configuré — authentification désactivée');
    return next();
  }
  const auth = req.headers['authorization'] || '';
  if (auth !== `Bearer ${FLY_SECRET}`) {
    return res.status(401).json({ error: 'Unauthorized' });
  }
  next();
}

// ---------------------------------------------------------------------------
// GET /health
// ---------------------------------------------------------------------------

app.get('/health', (req, res) => {
  res.json({
    ok: true,
    activeJobs,
    uptime: Math.floor((Date.now() - startTime) / 1000),
    maxConcurrentJobs: MAX_CONCURRENT_JOBS,
    version: '1.20.0'
  });
});

// ---------------------------------------------------------------------------
// POST /deepgram — Reçoit audio/vidéo, extrait l'audio avec FFmpeg, envoie à Deepgram
// Pipeline: upload → disque → FFmpeg → MP3 ~30MB → Deepgram → réponse
// Supporte fichiers vidéo > 2 GB via source_url (R2 presigned URL)
// Mode 1: body direct (petits fichiers < 95MB)
// Mode 2: source_url query param (gros fichiers — Fly.io télécharge depuis R2)
// ---------------------------------------------------------------------------

app.post('/deepgram', requireAnySecret, async (req, res) => {
  // Vérifier concurrence GLOBALE (partagée avec /extract)
  if (activeJobs >= MAX_CONCURRENT_JOBS) {
    return res.status(503).json({
      error: 'Serveur occupé — un autre traitement est en cours. Réessayez dans quelques minutes.',
      activeJobs,
      maxConcurrentJobs: MAX_CONCURRENT_JOBS
    });
  }
  activeJobs++;
  resetIdleTimer();

  const DEEPGRAM_KEY = process.env.DEEPGRAM_KEY || '';
  if (!DEEPGRAM_KEY) {
    activeJobs--;
    return res.status(503).json({ error: 'DEEPGRAM_KEY not configured' });
  }

  const urlObj = new URL(req.url, 'http://localhost');
  const sourceUrl = urlObj.searchParams.get('source_url');
  // Construire le query string pour Deepgram SANS source_url
  urlObj.searchParams.delete('source_url');
  const dgParams = urlObj.searchParams.toString();
  const qs = dgParams ? `?${dgParams}` : '';

  const contentType = req.headers['content-type'] || 'audio/mpeg';
  const contentLength = req.headers['content-length'] || '0';
  const sizeMB = (parseInt(contentLength) / 1048576).toFixed(1);
  const jobId = `dg-${Date.now().toString(36)}`;
  const tmpDir = process.env.NODE_ENV === 'production' ? '/app/tmp' : os.tmpdir();
  const inputPath = path.join(tmpDir, `${jobId}-input`);
  const audioPath = path.join(tmpDir, `${jobId}-audio.mp3`);

  const startMs = Date.now();
  const streaming = !!sourceUrl; // NDJSON streaming progress for source_url mode

  // Helper: envoyer une ligne NDJSON de progression (mode streaming uniquement)
  function sendProgress(pct, step) {
    if (!streaming) return;
    try { res.write(JSON.stringify({ type: 'progress', pct, step }) + '\n'); } catch (_) {}
  }

  // Étape 1: Obtenir le fichier sur disque (2 modes)
  try {
    // Mode streaming: configurer les headers NDJSON
    if (streaming) {
      res.writeHead(200, {
        'Content-Type': 'application/x-ndjson',
        'Transfer-Encoding': 'chunked',
        'Cache-Control': 'no-cache',
        'X-Content-Type-Options': 'nosniff',
      });
      sendProgress(5, 'download');
    }

    let fileToSend, sendContentType;

    if (sourceUrl) {
      // ── Mode URL: FFmpeg lit DIRECTEMENT depuis l'URL R2 (skip download!) ──
      console.log(`[${jobId}] Mode source_url — FFmpeg direct depuis R2 URL (skip download)`);
      sendProgress(10, 'ffmpeg');
      const ffmpegStart = Date.now();

      await new Promise((resolve, reject) => {
        const ff = spawn('ffmpeg', [
          '-i', sourceUrl,   // FFmpeg télécharge + convertit en 1 seule passe
          '-vn',
          '-acodec', 'libmp3lame',
          '-b:a', '128k',
          '-ac', '1',
          '-ar', '16000',
          '-y',
          audioPath
        ], { stdio: ['ignore', 'pipe', 'pipe'] });

        let stderr = '';
        let lastPct = 0;
        ff.stderr.on('data', d => {
          const chunk = d.toString();
          stderr += chunk;
          // Parse FFmpeg time= progress
          const m = chunk.match(/time=(\d+):(\d+):(\d+)/);
          if (m) {
            const secs = parseInt(m[1]) * 3600 + parseInt(m[2]) * 60 + parseInt(m[3]);
            const newPct = Math.min(60, 10 + Math.floor(secs / 30) * 5);
            if (newPct > lastPct) {
              lastPct = newPct;
              sendProgress(newPct, 'ffmpeg');
              console.log(`[${jobId}] FFmpeg: ${secs}s audio traité`);
            }
          }
        });
        ff.on('close', code => {
          if (code === 0) resolve();
          else reject(new Error(`FFmpeg exit ${code}: ${stderr.slice(-500)}`));
        });
        ff.on('error', reject);
      });

      const audioStat = fs.statSync(audioPath);
      const ffElapsed = ((Date.now() - ffmpegStart) / 1000).toFixed(1);
      console.log(`[${jobId}] FFmpeg direct terminé en ${ffElapsed}s → ${(audioStat.size / 1048576).toFixed(1)} MB audio`);
      sendProgress(65, 'deepgram');

      fileToSend = audioPath;
      sendContentType = 'audio/mpeg';

    } else {
      // ── Mode body direct: streaming du body HTTP sur disque ──
      console.log(`[${jobId}] Reçu ${sizeMB} MB (${contentType}) — sauvegarde sur disque...`);
      await new Promise((resolve, reject) => {
        const ws = fs.createWriteStream(inputPath);
        let received = 0;
        req.on('data', (chunk) => {
          received += chunk.length;
          if (received % (50 * 1024 * 1024) < chunk.length) {
            console.log(`[${jobId}] Reçu ${(received / 1048576).toFixed(0)}/${sizeMB} MB`);
          }
        });
        req.pipe(ws);
        ws.on('finish', resolve);
        ws.on('error', reject);
        req.on('error', reject);
      });
      const uploadElapsed = ((Date.now() - startMs) / 1000).toFixed(1);
      const inputStat = fs.statSync(inputPath);
      const inputSize = inputStat.size;
      console.log(`[${jobId}] Upload terminé: ${(inputSize / 1048576).toFixed(1)} MB en ${uploadElapsed}s`);

      const isAudioOnly = contentType.startsWith('audio/');
      if (isAudioOnly && inputSize < 50 * 1024 * 1024) {
        fileToSend = inputPath;
        sendContentType = contentType;
        console.log(`[${jobId}] Petit fichier audio — envoi direct à Deepgram`);
      } else {
        console.log(`[${jobId}] FFmpeg: extraction audio → MP3 128kbps mono...`);
        const ffmpegStart = Date.now();

        await new Promise((resolve, reject) => {
          const ff = spawn('ffmpeg', [
            '-i', inputPath,
            '-vn',
            '-acodec', 'libmp3lame',
            '-b:a', '128k',
            '-ac', '1',
            '-ar', '16000',
            '-y',
            audioPath
          ], { stdio: ['ignore', 'pipe', 'pipe'] });

          let stderr = '';
          ff.stderr.on('data', d => { stderr += d.toString(); });
          ff.on('close', code => {
            if (code === 0) resolve();
            else reject(new Error(`FFmpeg exit ${code}: ${stderr.slice(-300)}`));
          });
          ff.on('error', reject);
        });

        const audioStat = fs.statSync(audioPath);
        const ffElapsed = ((Date.now() - ffmpegStart) / 1000).toFixed(1);
        console.log(`[${jobId}] FFmpeg terminé en ${ffElapsed}s: ${(inputSize / 1048576).toFixed(1)} MB → ${(audioStat.size / 1048576).toFixed(1)} MB`);

        fileToSend = audioPath;
        sendContentType = 'audio/mpeg';
      }
    }

    // Étape 3: Envoyer le fichier audio à Deepgram (streaming depuis disque)
    sendProgress(70, 'deepgram');
    const fileStat = fs.statSync(fileToSend);
    console.log(`[${jobId}] Envoi ${(fileStat.size / 1048576).toFixed(1)} MB à Deepgram...`);
    const dgStart = Date.now();

    const dgResult = await new Promise((resolve, reject) => {
      const dgReq = https.request({
        hostname: 'api.deepgram.com',
        path: `/v1/listen${qs}`,
        method: 'POST',
        headers: {
          'Authorization': `Token ${DEEPGRAM_KEY}`,
          'Content-Type': sendContentType,
          'Content-Length': fileStat.size,
        },
        timeout: 600000,
      }, (dgRes) => {
        let body = '';
        dgRes.on('data', d => { body += d.toString(); });
        dgRes.on('end', () => resolve({ status: dgRes.statusCode, body }));
      });

      dgReq.on('error', reject);
      dgReq.on('timeout', () => dgReq.destroy(new Error('Deepgram timeout')));

      const rs = fs.createReadStream(fileToSend);
      rs.pipe(dgReq);
    });

    const dgElapsed = ((Date.now() - dgStart) / 1000).toFixed(1);
    const totalElapsed = ((Date.now() - startMs) / 1000).toFixed(1);
    console.log(`[${jobId}] Deepgram répondu ${dgResult.status} en ${dgElapsed}s (total: ${totalElapsed}s)`);

    if (streaming) {
      // Mode NDJSON: envoyer le résultat final puis fermer
      sendProgress(95, 'done');
      res.write(JSON.stringify({ type: 'result', status: dgResult.status, body: dgResult.body }) + '\n');
      res.end();
    } else {
      res.status(dgResult.status);
      res.set('Content-Type', 'application/json');
      res.send(dgResult.body);
    }

  } catch (err) {
    console.error(`[${jobId}] Erreur:`, err.message);
    if (streaming && !res.writableEnded) {
      res.write(JSON.stringify({ type: 'error', error: err.message }) + '\n');
      res.end();
    } else if (!res.headersSent) {
      res.status(502).json({ error: `Deepgram proxy error: ${err.message}` });
    }
  } finally {
    activeJobs--;
    resetIdleTimer();
    console.log(`[${jobId}] Deepgram job terminé. Jobs actifs: ${activeJobs}`);
    try { fs.unlinkSync(inputPath); } catch (_) {}
    try { fs.unlinkSync(audioPath); } catch (_) {}
  }
});

// ---------------------------------------------------------------------------
// POST /extract
// ---------------------------------------------------------------------------

app.post('/extract', requireFlySecret, (req, res) => {
  const {
    jobId,
    presignedDownload,
    srcLang,
    workerCallbackUrl,
    workerSecret,
    groqKey,
    gatewayKey,
    gatewayUrl
  } = req.body || {};

  if (!jobId || !presignedDownload || !workerCallbackUrl || !workerSecret || (!groqKey && !(gatewayKey && gatewayUrl))) {
    return res.status(400).json({
      error: 'Champs obligatoires manquants: jobId, presignedDownload, workerCallbackUrl, workerSecret, (groqKey ou gatewayKey+gatewayUrl)'
    });
  }

  if (activeJobs >= MAX_CONCURRENT_JOBS) {
    return res.status(503).json({
      error: 'Trop de jobs en cours',
      activeJobs,
      maxConcurrentJobs: MAX_CONCURRENT_JOBS
    });
  }

  // Répondre immédiatement puis traiter en async
  res.json({ accepted: true, jobId });

  activeJobs++;
  resetIdleTimer();
  const JOB_TIMEOUT_MS = 50 * 60 * 1000; // 50 min max
  const jobTimeout = new Promise((_, reject) =>
    setTimeout(() => reject(new Error('Job timeout 50min dépassé')), JOB_TIMEOUT_MS)
  );

  Promise.race([
    processJob({ jobId, presignedDownload, srcLang, workerCallbackUrl, workerSecret, groqKey, gatewayKey, gatewayUrl }),
    jobTimeout
  ])
    .catch(async err => {
      console.error(`[${jobId}] Erreur pipeline:`, err.message);
      await updateWorker(workerCallbackUrl, workerSecret, {
        jobId, status: 'error', error: err.message
      }).catch(() => {});
    })
    .finally(() => {
      activeJobs--;
      resetIdleTimer();
      console.log(`[${jobId}] Job terminé. Jobs actifs: ${activeJobs}`);
    });
});

// ---------------------------------------------------------------------------
// Pipeline principal
// ---------------------------------------------------------------------------

async function processJob(job) {
  const { jobId, presignedDownload, srcLang, workerCallbackUrl, workerSecret, groqKey, gatewayKey, gatewayUrl } = job;

  console.log(`[${jobId}] Démarrage du pipeline. URL: ${presignedDownload.substring(0, 80)}...`);

  try {
    await updateWorker(workerCallbackUrl, workerSecret, {
      jobId,
      progress: 5,
      log: 'Démarrage extraction audio via FFmpeg...',
      status: 'processing'
    });

    const ffmpegArgs = [
      '-i', presignedDownload,
      '-vn',
      '-acodec', 'pcm_s16le',
      '-ar', '16000',
      '-ac', '1',
      '-f', 'wav',
      'pipe:1'
    ];

    console.log(`[${jobId}] Commande FFmpeg: ffmpeg ${ffmpegArgs.slice(0, 4).join(' ')} ... pipe:1`);

    await updateWorker(workerCallbackUrl, workerSecret, {
      jobId,
      progress: 10,
      log: '🔊 FFmpeg démarré — extraction audio WAV 16kHz mono...',
      status: 'processing'
    });

    const { allSegments, chunkReport } = await streamAndTranscribe({
      jobId,
      ffmpegArgs,
      srcLang,
      groqKey,
      gatewayKey,
      gatewayUrl,
      workerCallbackUrl,
      workerSecret
    });

    await updateWorker(workerCallbackUrl, workerSecret, {
      jobId,
      progress: 95,
      log: `📝 Assemblage SRT — ${allSegments.length} segments au total`,
      status: 'processing'
    });

    const srt = assembleSrt(allSegments);
    console.log(`[${jobId}] SRT assemblé: ${srt.length} caractères, ${allSegments.length} segments`);

    // Détecter les gaps dans l'assemblage final
    const gapReport = [];
    for (let gi = 1; gi < allSegments.length; gi++) {
      const gap = allSegments[gi].start - allSegments[gi - 1].end;
      if (gap > 5) gapReport.push({ at: +allSegments[gi - 1].end.toFixed(1), dur: +gap.toFixed(1) });
    }

    await updateWorker(workerCallbackUrl, workerSecret, {
      jobId,
      progress: 100,
      log: 'Transcription terminée.',
      status: 'done',
      srt,
      chunkReport,
      gapReport
    });

    console.log(`[${jobId}] Pipeline terminé avec succès.`);

  } catch (err) {
    console.error(`[${jobId}] Erreur pipeline:`, err);
    await updateWorker(workerCallbackUrl, workerSecret, {
      jobId,
      status: 'error',
      error: err.message || String(err),
      log: `Erreur: ${err.message || String(err)}`
    }).catch(e => console.error(`[${jobId}] Impossible d'envoyer le callback d'erreur:`, e));
  }
}

// ---------------------------------------------------------------------------
// Streaming FFmpeg → accumulation PCM → chunks séquentiels → Groq
// ---------------------------------------------------------------------------

async function streamAndTranscribe({ jobId, ffmpegArgs, srcLang, groqKey, gatewayKey, gatewayUrl, workerCallbackUrl, workerSecret }) {
  return new Promise((resolve, reject) => {
    const ffmpeg = spawn('ffmpeg', ffmpegArgs, {
      stdio: ['ignore', 'pipe', 'pipe']
    });

    let ffmpegStderr = '';
    let promiseResolved = false;
    let headerParsed = false;
    let headerAccum = Buffer.alloc(0);
    // IMPORTANT: on accumule les chunks dans un array et on concat UNE SEULE FOIS à la fin
    // Buffer.concat([buf, chunk]) dans un loop = O(n²) copies → bloque l'event loop sur gros fichiers
    const pcmChunks = [];

    ffmpeg.stderr.on('data', d => { ffmpegStderr += d.toString(); });

    // Phase 1: accumuler header WAV (44 bytes) + PCM
    ffmpeg.stdout.on('data', chunk => {
      if (!headerParsed) {
        headerAccum = Buffer.concat([headerAccum, chunk]);
        if (headerAccum.length >= 44) {
          headerParsed = true;
          const remaining = headerAccum.slice(44);
          if (remaining.length > 0) {
            pcmChunks.push(remaining);
          }
          // Estimer durée et nombre de chunks
          const bytesPerSec = headerAccum.readUInt32LE(28);
          const dataSize = headerAccum.readUInt32LE(40);
          const sampleRate = headerAccum.readUInt32LE(24);
          const numChannels = headerAccum.readUInt16LE(22);
          console.log(`[${jobId}] Header WAV parsé. Sample rate: ${sampleRate} Hz, Channels: ${numChannels}, dataSize header: ${dataSize}`);
          // Note: en mode pipe (pipe:1), FFmpeg ne peut pas seek-back pour écrire la vraie taille
          // → dataSize est souvent 0 ou un placeholder. On affiche "?" si < 32000 bytes (~1s)
          const dataValid = dataSize > 32000 && dataSize < 0x7FFFFFFF;
          const estimatedChunks = dataValid ? Math.ceil(dataSize / CHUNK_MAX_BYTES) : '?';
          const estimatedMin = dataValid && bytesPerSec > 0 ? (dataSize / bytesPerSec / 60).toFixed(1) : '?';
          updateWorker(workerCallbackUrl, workerSecret, {
            jobId,
            progress: 15,
            log: `📐 Audio: ${estimatedMin === '?' ? 'durée inconnue (streaming)' : estimatedMin + 'min détectés'} — ~${estimatedChunks} chunks estimés`,
            status: 'processing'
          }).catch(() => {});
        }
        return;
      }
      // Accumuler PCM dans l'array (O(1) par event, concat unique dans end)
      pcmChunks.push(chunk);
    });

    // Phase 2: tout le PCM est accumulé, traiter chunks SÉQUENTIELLEMENT
    ffmpeg.stdout.on('end', async () => {
      // Concat unique ici — O(n) au lieu de O(n²) dans le data handler
      let pcmAccum = pcmChunks.length > 0 ? Buffer.concat(pcmChunks) : Buffer.alloc(0);
      console.log(`[${jobId}] FFmpeg stdout terminé. PCM total: ${pcmAccum.length} bytes (${(pcmAccum.length / 1024 / 1024).toFixed(1)} MB)`);

      if (!headerParsed || pcmAccum.length === 0) {
        const errMsg = `FFmpeg n'a produit aucun audio WAV valide. Stderr: ${ffmpegStderr.slice(-500)}`;
        console.error(`[${jobId}] ${errMsg}`);
        if (!promiseResolved) { promiseResolved = true; reject(new Error(errMsg)); }
        return;
      }

      // Découper en chunks et transcrire séquentiellement
      try {
        const totalChunks = Math.ceil(pcmAccum.length / CHUNK_MAX_BYTES);
        console.log(`[${jobId}] ${totalChunks} chunk(s) à transcrire séquentiellement`);

        const allSegments = [];
        const chunkReport = [];
        let lastGroqCallTime = 0;

        for (let i = 0; i < totalChunks; i++) {
          const start = i * CHUNK_MAX_BYTES;
          const end = Math.min(start + CHUNK_MAX_BYTES, pcmAccum.length);
          const pcmChunk = pcmAccum.slice(start, end);
          const chunkDurationSec = pcmChunk.length / 32000;

          console.log(`[${jobId}] Chunk ${i}: ${pcmChunk.length} bytes PCM → WAV ${(pcmChunk.length / 1024 / 1024).toFixed(1)} MB`);

          // Throttling Groq
          const now = Date.now();
          const elapsed = now - lastGroqCallTime;
          if (elapsed < GROQ_MIN_INTERVAL_MS && lastGroqCallTime > 0) {
            const wait = GROQ_MIN_INTERVAL_MS - elapsed;
            console.log(`[${jobId}] Chunk ${i}: throttling Groq, attente ${wait}ms...`);
            await sleep(wait);
          }

          const offsetSec = i * CHUNK_DUR_SEC;
          const progress = Math.min(85, 20 + Math.round((i / totalChunks) * 65));

          await updateWorker(workerCallbackUrl, workerSecret, {
            jobId,
            progress,
            log: `🎯 Chunk ${i + 1}/${totalChunks} → Groq Whisper (${formatTime(offsetSec)} → ${formatTime(offsetSec + chunkDurationSec)})...`,
            status: 'processing'
          }).catch(() => {});

          lastGroqCallTime = Date.now();

          const wavBuffer = buildWavBuffer(pcmChunk);
          const segments = await transcribeWithGroq({
            jobId,
            wavBuffer,
            chunkIdx: i,
            srcLang,
            groqKey,
            gatewayKey,
            gatewayUrl,
            offsetSec,
            chunkDurationSec,
            workerCallbackUrl,
            workerSecret
          });

          console.log(`[${jobId}] Chunk ${i}: ${segments.length} segments reçus`);
          allSegments.push(...segments);

          // Calculer la couverture réelle de ce chunk
          const covPct = segments.length > 0
            ? Math.round((segments[segments.length - 1].end - offsetSec) / chunkDurationSec * 100)
            : 0;
          const txtFirst = segments.length > 0 ? segments[0].text.substring(0, 40) : '';
          const txtLast  = segments.length > 1 ? segments[segments.length - 1].text.substring(0, 40) : txtFirst;
          const incomplete = segments.length > 0 && covPct < 70;

          chunkReport.push({
            i: i + 1,
            total: totalChunks,
            segs: segments.length,
            dur: +chunkDurationSec.toFixed(1),
            cov: covPct,
            ok: !incomplete,
            first: txtFirst,
            last: txtLast
          });

          const chunkLogMsg = segments.length === 0
            ? `❌ Chunk ${i + 1}/${totalChunks} — 0 segments (audio vide ?)`
            : `${incomplete ? '⚠️' : '✅'} Chunk ${i + 1}/${totalChunks}: ${segments.length} segs · couv ${covPct}%${incomplete ? ' INCOMPLET' : ''}`;

          await updateWorker(workerCallbackUrl, workerSecret, {
            jobId,
            progress,
            log: chunkLogMsg,
            status: 'processing'
          }).catch(() => {});
        }

        // Libérer la mémoire PCM
        pcmAccum = Buffer.alloc(0);

        promiseResolved = true;
        resolve({ allSegments, chunkReport });

      } catch (err) {
        if (!promiseResolved) { promiseResolved = true; reject(err); }
      }
    }); // fin ffmpeg.stdout.on('end')

    ffmpeg.on('error', err => {
      console.error(`[${jobId}] Erreur spawn FFmpeg:`, err);
      if (!promiseResolved) { promiseResolved = true; reject(new Error(`FFmpeg spawn error: ${err.message}`)); }
    });

    ffmpeg.on('close', code => {
      if (code !== 0) {
        console.error(`[${jobId}] FFmpeg exited with code ${code}`);
        console.error(`[${jobId}] FFmpeg stderr:\n${ffmpegStderr.slice(-2000)}`);
        if (!promiseResolved) {
          promiseResolved = true;
          reject(new Error(`FFmpeg a échoué (code ${code}): ${ffmpegStderr.slice(-500)}`));
        }
      } else {
        console.log(`[${jobId}] FFmpeg terminé avec succès (code 0)`);
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Transcription Groq avec retry x3 — FormData NATIF Node.js 20
// ---------------------------------------------------------------------------

async function transcribeWithGroq({ jobId, wavBuffer, chunkIdx, srcLang, groqKey, gatewayKey, gatewayUrl, offsetSec, chunkDurationSec, workerCallbackUrl, workerSecret }) {
  const MAX_RETRIES = 5; // augmenté pour couvrir plusieurs fenêtres rate-limit Groq
  let lastError;

  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      console.log(`[${jobId}] Chunk ${chunkIdx}: appel Groq (tentative ${attempt}/${MAX_RETRIES})...`);

      // Utiliser FormData et Blob NATIFS de Node.js 20 (pas le paquet npm form-data)
      // Cela évite le bug "multipart: NextPart: EOF" avec fetch natif
      const blob = new Blob([wavBuffer], { type: 'audio/wav' });
      const form = new FormData();
      form.append('file', blob, `chunk_${chunkIdx}.wav`);
      form.append('model', GROQ_MODEL);
      form.append('response_format', 'verbose_json');
      form.append('timestamp_granularities[]', 'segment');
      if (srcLang && srcLang.trim()) {
        form.append('language', srcLang.trim());
      }

      // Si groqKey dispo → Groq direct ; sinon → passer via la gateway CF
      let transcribeUrl, transcribeHeaders;
      if (groqKey) {
        transcribeUrl = GROQ_ENDPOINT;
        transcribeHeaders = { 'Authorization': `Bearer ${groqKey}` };
      } else {
        transcribeUrl = `${gatewayUrl}/api/groq`;
        transcribeHeaders = {
          'Authorization': `Bearer ${gatewayKey}`,
          'X-Api-Path': '/openai/v1/audio/transcriptions',
        };
      }

      const response = await fetch(transcribeUrl, {
        method: 'POST',
        headers: transcribeHeaders,
        // PAS de Content-Type — fetch le définit automatiquement avec le bon boundary
        body: form,
      });

      if (!response.ok) {
        const errText = await response.text();

        // Cas rate-limit : parser "try again in Xm Y.Zs" pour attendre exactement ce délai
        if (response.status === 429) {
          const m = errText.match(/try again in (\d+)m(\d+(?:\.\d+)?)s/i);
          const waitMs = m
            ? Math.ceil((parseInt(m[1]) * 60 + parseFloat(m[2])) * 1000) + 10000 // +10s buffer
            : 6 * 60 * 1000; // fallback : 6 minutes
          const waitSec = Math.round(waitMs / 1000);
          const err429 = new Error(`Groq HTTP 429 (rate limit) — pause ${waitSec}s`);
          err429.retryAfterMs = waitMs;
          err429.is429 = true;
          throw err429;
        }

        throw new Error(`Groq HTTP ${response.status}: ${errText.substring(0, 300)}`);
      }

      const data = await response.json();

      if (!data.segments || !Array.isArray(data.segments)) {
        console.warn(`[${jobId}] Chunk ${chunkIdx}: pas de segments dans la réponse Groq`);
        return [];
      }

      // Clamp seg.end à chunkDurationSec : Groq Whisper hallucine parfois des end >> durée du chunk
      // v1.7.0: filtre aussi seg.start >= chunkDurationSec (hallucination start hors-limites → dépasse durée vidéo)
      const maxRelEnd = chunkDurationSec || CHUNK_DUR_SEC;
      const segments = data.segments.filter(seg => {
        const relStart = seg.start || 0;
        if (relStart >= maxRelEnd) {
          console.warn(`[${jobId}] Chunk ${chunkIdx}: skip hallucination start=${relStart.toFixed(1)}s >= chunkDur=${maxRelEnd.toFixed(1)}s — "${(seg.text||'').trim().substring(0,60)}"`);
          return false;
        }
        return true;
      }).map(seg => {
        const relStart = seg.start || 0;
        const relEnd   = Math.min(seg.end || 0, relStart + 30, maxRelEnd); // cap 30s max/segment
        return {
          start: relStart + offsetSec,
          end  : Math.max(relEnd + offsetSec, relStart + offsetSec + 0.1), // end > start toujours
          text : (seg.text || '').trim()
        };
      }).filter(seg => seg.text.length > 0);

      console.log(`[${jobId}] Chunk ${chunkIdx}: ${segments.length} segments reçus de Groq (offset=${offsetSec.toFixed(1)}s)`);
      return segments;

    } catch (err) {
      lastError = err;
      console.error(`[${jobId}] Chunk ${chunkIdx}: tentative ${attempt} échouée:`, err.message);

      if (attempt < MAX_RETRIES) {
        // Pour 429 : attendre le délai exact indiqué par Groq (5+ min)
        // Pour autres erreurs : backoff exponentiel court (5s, 10s, 15s...)
        const backoff = err.is429 ? (err.retryAfterMs || 6 * 60 * 1000) : attempt * 5000;
        const backoffSec = Math.round(backoff / 1000);
        console.log(`[${jobId}] Chunk ${chunkIdx}: ${err.is429 ? '⏳ rate limit' : '⚠️ erreur'} — retry dans ${backoffSec}s...`);
        updateWorker(workerCallbackUrl, workerSecret, {
          jobId,
          log: err.is429
            ? `⏳ Rate limit Groq — pause ${backoffSec}s (tentative ${attempt}/${MAX_RETRIES})...`
            : `⚠️ Groq erreur — retry ${attempt}/${MAX_RETRIES} dans ${backoffSec}s... (${err.message.substring(0, 80)})`,
          status: 'processing'
        }).catch(() => {});
        await sleep(backoff);
      }
    }
  }

  throw new Error(`Groq transcription échouée après ${MAX_RETRIES} tentatives pour chunk ${chunkIdx}: ${lastError?.message}`);
}

// ---------------------------------------------------------------------------
// Construction du buffer WAV (header 44 bytes + PCM)
// ---------------------------------------------------------------------------

function buildWavBuffer(pcmData) {
  const numChannels = 1;
  const sampleRate = 16000;
  const bitsPerSample = 16;
  const byteRate = sampleRate * numChannels * (bitsPerSample / 8);
  const blockAlign = numChannels * (bitsPerSample / 8);
  const dataSize = pcmData.length;
  const chunkSize = 36 + dataSize;

  const header = Buffer.alloc(44);
  header.write('RIFF', 0, 'ascii');
  header.writeUInt32LE(chunkSize, 4);
  header.write('WAVE', 8, 'ascii');
  header.write('fmt ', 12, 'ascii');
  header.writeUInt32LE(16, 16);
  header.writeUInt16LE(1, 20);
  header.writeUInt16LE(numChannels, 22);
  header.writeUInt32LE(sampleRate, 24);
  header.writeUInt32LE(byteRate, 28);
  header.writeUInt16LE(blockAlign, 32);
  header.writeUInt16LE(bitsPerSample, 34);
  header.write('data', 36, 'ascii');
  header.writeUInt32LE(dataSize, 40);

  return Buffer.concat([header, pcmData]);
}

// ---------------------------------------------------------------------------
// Assemblage SRT depuis les segments
// ---------------------------------------------------------------------------

function assembleSrt(segments) {
  if (!segments || segments.length === 0) return '';

  const lines = [];
  let blockNum = 1;

  for (const seg of segments) {
    const text = (seg.text || '').trim();
    if (!text) continue;
    lines.push(String(blockNum));
    lines.push(`${secToSrtTime(seg.start)} --> ${secToSrtTime(seg.end)}`);
    lines.push(text);
    lines.push('');
    blockNum++;
  }

  return lines.join('\n');
}

function secToSrtTime(sec) {
  const totalMs = Math.round((sec || 0) * 1000);
  const ms = totalMs % 1000;
  const totalSec = Math.floor(totalMs / 1000);
  const s = totalSec % 60;
  const totalMin = Math.floor(totalSec / 60);
  const m = totalMin % 60;
  const h = Math.floor(totalMin / 60);
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms).padStart(3, '0')}`;
}

// ---------------------------------------------------------------------------
// Callback vers le Cloudflare Worker
// ---------------------------------------------------------------------------

async function updateWorker(url, secret, payload) {
  try {
    const response = await fetch(url, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Secret': secret
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(10000)
    });
    if (!response.ok) {
      const errText = await response.text().catch(() => '');
      console.warn(`[updateWorker] Callback HTTP ${response.status} vers ${url}: ${errText.substring(0, 200)}`);
    }
  } catch (err) {
    console.warn(`[updateWorker] Erreur callback:`, err.message);
  }
}

// ---------------------------------------------------------------------------
// Utilitaires
// ---------------------------------------------------------------------------

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function formatTime(sec) {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  return h > 0
    ? `${h}h${String(m).padStart(2, '0')}m${String(s).padStart(2, '0')}s`
    : `${m}m${String(s).padStart(2, '0')}s`;
}

// ---------------------------------------------------------------------------
// POST /webproxy — Web proxy pour VideoGrab (contourne blocage IP datacenter CF)
// Le Worker CF redirige ici quand le fetch direct retourne 403
// ---------------------------------------------------------------------------

const CHROME_HEADERS = {
  'User-Agent': 'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
  'Accept-Language': 'en-US,en;q=0.9,fr-FR;q=0.8,fr;q=0.7',
  'Accept-Encoding': 'gzip, deflate, br',
  'Sec-Ch-Ua': '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
  'Sec-Ch-Ua-Mobile': '?1',
  'Sec-Ch-Ua-Platform': '"Android"',
  'Sec-Fetch-Dest': 'document',
  'Sec-Fetch-Mode': 'navigate',
  'Sec-Fetch-Site': 'none',
  'Sec-Fetch-User': '?1',
  'Upgrade-Insecure-Requests': '1',
  'DNT': '1',
  'Cache-Control': 'max-age=0',
};

app.post('/webproxy', requireAnySecret, async (req, res) => {
  const { url, method: reqMethod, headers: extraHeaders, raw } = req.body || {};
  if (!url) return res.status(400).json({ error: 'missing url' });

  try {
    const target = new URL(url);
    if (!['http:', 'https:'].includes(target.protocol)) {
      return res.status(400).json({ error: 'only http/https' });
    }

    const fetchHeaders = { ...CHROME_HEADERS, 'Referer': target.origin + '/' };
    if (raw) {
      fetchHeaders['Accept'] = '*/*';
      fetchHeaders['Sec-Fetch-Dest'] = 'empty';
      fetchHeaders['Sec-Fetch-Mode'] = 'cors';
    }
    // Forward cookies if provided
    if (extraHeaders && extraHeaders.cookie) fetchHeaders['Cookie'] = extraHeaders.cookie;
    if (extraHeaders && extraHeaders.range) fetchHeaders['Range'] = extraHeaders.range;

    const upstream = await fetch(url, {
      method: reqMethod || 'GET',
      headers: fetchHeaders,
      redirect: 'follow',
    });

    // Forward status + key headers
    const respHeaders = {
      'Content-Type': upstream.headers.get('content-type') || 'text/html',
      'Access-Control-Allow-Origin': '*',
      'X-Proxy-Status': String(upstream.status),
    };
    for (const h of ['content-length', 'accept-ranges', 'content-range', 'content-disposition', 'last-modified', 'etag', 'set-cookie']) {
      const v = upstream.headers.get(h);
      if (v) respHeaders[h] = v;
    }

    // Stream body
    const body = Buffer.from(await upstream.arrayBuffer());
    res.status(upstream.status).set(respHeaders).send(body);

  } catch (err) {
    console.error('[webproxy] Error:', err.message);
    res.status(502).json({ error: 'fetch failed: ' + err.message });
  }
});

app.get('/webproxy', requireAnySecret, async (req, res) => {
  const url = req.query.url;
  if (!url) return res.status(400).json({ error: 'missing url query param' });

  try {
    const target = new URL(url);
    const raw = req.query.raw === '1';
    const fetchHeaders = { ...CHROME_HEADERS, 'Referer': target.origin + '/' };
    if (raw) {
      fetchHeaders['Accept'] = '*/*';
      fetchHeaders['Sec-Fetch-Dest'] = 'empty';
      fetchHeaders['Sec-Fetch-Mode'] = 'cors';
    }
    const range = req.headers['range'];
    if (range) fetchHeaders['Range'] = range;

    const upstream = await fetch(url, { headers: fetchHeaders, redirect: 'follow' });

    const respHeaders = {
      'Content-Type': upstream.headers.get('content-type') || 'application/octet-stream',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Expose-Headers': 'Content-Range, Content-Length, Accept-Ranges',
    };
    for (const h of ['content-length', 'accept-ranges', 'content-range', 'content-disposition']) {
      const v = upstream.headers.get(h);
      if (v) respHeaders[h] = v;
    }

    const body = Buffer.from(await upstream.arrayBuffer());
    res.status(upstream.status).set(respHeaders).send(body);
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

// ---------------------------------------------------------------------------
// HLS to MP4 — Job-based with SSE progress tracking
// POST /hls2mp4       → starts job, returns { jobId }
// GET  /hls2mp4/events/:id → SSE stream with progress events
// GET  /hls2mp4/file/:id   → download completed MP4 file
// ---------------------------------------------------------------------------

const hlsJobs = new Map(); // jobId → { status, logs[], progress, mp4Path, tmpDir, mp4Size, safeName, error }
const MAX_HLS_CONCURRENT = 2; // 5GB volume supports concurrent jobs
const hlsQueue = []; // pending job processing functions

function hlsActiveCount() {
  let c = 0;
  for (const j of hlsJobs.values()) { if (j.status === 'processing') c++; }
  return c;
}

function hlsTryNext() {
  while (hlsQueue.length > 0 && hlsActiveCount() < MAX_HLS_CONCURRENT) {
    const next = hlsQueue.shift();
    next();
  }
}

// Cleanup old jobs after 10 minutes (safety net)
setInterval(() => {
  const now = Date.now();
  for (const [id, job] of hlsJobs) {
    if (now - job.created > 600000) {
      try { fs.rmSync(job.tmpDir, { recursive: true, force: true }); } catch (e) {}
      hlsJobs.delete(id);
      console.log(`[CLEANUP-INTERVAL] Job ${id} supprime (>10min)`);
    }
  }
  // Aussi nettoyer les dossiers orphelins (pas dans hlsJobs mais sur le disque)
  // Mais épargner les dirs avec output.mp4 récent (< 30 min) pour permettre le download
  const hlsBase = fs.existsSync('/data') ? '/data' : null;
  if (hlsBase) {
    try {
      const entries = fs.readdirSync(hlsBase);
      for (const entry of entries) {
        if (entry.startsWith('hls_')) {
          const jobIdFromDir = entry.replace('hls_', '');
          if (!hlsJobs.has(jobIdFromDir)) {
            const dirPath = path.join(hlsBase, entry);
            const mp4File = path.join(dirPath, 'output.mp4');
            // Keep orphan dirs with output.mp4 less than 30 min old (user might still download)
            if (fs.existsSync(mp4File)) {
              try {
                const age = now - fs.statSync(mp4File).mtimeMs;
                if (age < 1800000) continue; // < 30 min → keep
              } catch (e) {}
            }
            try {
              fs.rmSync(dirPath, { recursive: true, force: true });
              console.log(`[CLEANUP-INTERVAL] Orphelin supprime: ${entry}`);
            } catch (e) {}
          }
        }
      }
    } catch (e) {}
  }
}, 60000);

// Check available disk space (returns MB)
function getAvailableDiskMB() {
  try {
    const { execSync } = require('child_process');
    const df = execSync('df /data 2>/dev/null || df /tmp', { encoding: 'utf8' });
    const lines = df.trim().split('\n');
    if (lines.length >= 2) {
      const parts = lines[1].split(/\s+/);
      // df output: Filesystem 1K-blocks Used Available Use% Mounted
      const availKB = parseInt(parts[3], 10);
      if (!isNaN(availKB)) return Math.floor(availKB / 1024);
    }
  } catch (e) {}
  return 9999; // fallback: assume OK
}

function jobLog(job, msg) {
  const ts = new Date().toISOString().split('T')[1].split('.')[0];
  const line = `[${ts}] ${msg}`;
  job.logs.push(line);
  console.log(`[hls2mp4:${job.id}] ${msg}`);
  // Notify SSE listeners
  if (job.listeners) job.listeners.forEach(fn => fn({ type: 'log', data: line, progress: job.progress, status: job.status }));
}

function jobProgress(job, pct) {
  job.progress = pct;
  if (job.listeners) job.listeners.forEach(fn => fn({ type: 'progress', data: pct, status: job.status }));
}

function jobDone(job, status, error) {
  job.status = status;
  if (error) job.error = error;
  if (job.listeners) job.listeners.forEach(fn => fn({ type: 'done', status, error: error || null, mp4Size: job.mp4Size || 0 }));
}

app.post('/hls2mp4', requireAnySecret, async (req, res) => {
  const { m3u8Url, title, proxyBase } = req.body || {};
  if (!m3u8Url) return res.status(400).json({ error: 'missing m3u8Url' });

  const jobId = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  // Use /data volume in production (5GB persistent), fallback to os.tmpdir()
  const hlsBase = fs.existsSync('/data') ? '/data' : os.tmpdir();
  const tmpDir = path.join(hlsBase, 'hls_' + jobId);
  fs.mkdirSync(tmpDir, { recursive: true });

  const job = {
    id: jobId, status: 'queued', logs: [], progress: 0,
    mp4Path: null, mp4Size: 0, tmpDir, safeName: '',
    created: Date.now(), listeners: new Set(),
  };
  hlsJobs.set(jobId, job);

  // Check disk space before accepting job
  const availMB = getAvailableDiskMB();
  if (availMB < 500) {
    // Emergency cleanup: remove all orphan dirs
    try {
      const entries = fs.readdirSync(hlsBase);
      for (const entry of entries) {
        if (entry.startsWith('hls_') && entry !== 'hls_' + jobId) {
          const orphanId = entry.replace('hls_', '');
          const orphanJob = hlsJobs.get(orphanId);
          if (!orphanJob || orphanJob.status === 'error' || orphanJob.status === 'done') {
            try { fs.rmSync(path.join(hlsBase, entry), { recursive: true, force: true }); } catch (e) {}
            if (orphanJob) hlsJobs.delete(orphanId);
            console.log(`[DISK-LOW] Nettoyage urgence: ${entry}`);
          }
        }
      }
    } catch (e) {}
    const afterCleanMB = getAvailableDiskMB();
    if (afterCleanMB < 200) {
      try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (e) {}
      return res.status(507).json({ error: `Espace disque insuffisant: ${afterCleanMB} MB libre (min 200 MB)` });
    }
  }

  const active = hlsActiveCount();
  const queued = hlsQueue.length;
  res.json({ jobId, position: active >= MAX_HLS_CONCURRENT ? queued + 1 : 0 });

  // Process function (called immediately or from queue)
  const processJob = async () => {
  job.status = 'processing';
  jobLog(job, 'Demarrage du traitement...');

  const combinedTs = path.join(tmpDir, 'combined.ts');

  // Direct fetch first, proxy fallback only if needed
  async function fetchUrl(url, useProxy, signal) {
    const opts = { headers: { ...CHROME_HEADERS, 'Accept': '*/*' } };
    if (signal) opts.signal = signal;
    if (useProxy && proxyBase) {
      return fetch(`${proxyBase}${encodeURIComponent(url)}`, opts);
    }
    return fetch(url, opts);
  }

  try {
    jobLog(job, `Debut — ${m3u8Url.substring(0, 80)}...`);

    // 1. Fetch and parse m3u8 (try direct first, then proxy)
    let m3u8Resp = await fetchUrl(m3u8Url, false);
    if (!m3u8Resp.ok && proxyBase) {
      jobLog(job, 'Direct m3u8 echoue, essai via proxy...');
      m3u8Resp = await fetchUrl(m3u8Url, true);
    }
    if (!m3u8Resp.ok) throw new Error(`m3u8 HTTP ${m3u8Resp.status}`);
    const m3u8Text = await m3u8Resp.text();
    const allLines = m3u8Text.split('\n').map(l => l.trim()).filter(l => l);
    const baseUrl = m3u8Url.substring(0, m3u8Url.lastIndexOf('/') + 1);

    jobLog(job, 'Playlist m3u8 recuperee');

    // Check for master playlist
    let isMaster = false, bestBandwidth = 0, bestVariant = '';
    for (let i = 0; i < allLines.length; i++) {
      if (allLines[i].startsWith('#EXT-X-STREAM-INF')) {
        isMaster = true;
        const bw = parseInt((allLines[i].match(/BANDWIDTH=(\d+)/) || [])[1] || '0');
        const next = allLines[i + 1];
        if (next && !next.startsWith('#') && bw >= bestBandwidth) {
          bestBandwidth = bw;
          bestVariant = next.startsWith('http') ? next : baseUrl + next;
        }
      }
    }

    let segUrls = [];
    if (isMaster && bestVariant) {
      jobLog(job, `Master playlist → variante ${(bestBandwidth/1000).toFixed(0)} kbps`);
      let varResp = await fetchUrl(bestVariant, false);
      if (!varResp.ok && proxyBase) varResp = await fetchUrl(bestVariant, true);
      if (!varResp.ok) throw new Error(`Variant HTTP ${varResp.status}`);
      const varText = await varResp.text();
      const varBase = bestVariant.substring(0, bestVariant.lastIndexOf('/') + 1);
      for (const vl of varText.split('\n').map(l => l.trim())) {
        if (vl && !vl.startsWith('#')) segUrls.push(vl.startsWith('http') ? vl : varBase + vl);
      }
    } else {
      for (const line of allLines) {
        if (line && !line.startsWith('#')) segUrls.push(line.startsWith('http') ? line : baseUrl + line);
      }
    }

    if (!segUrls.length) throw new Error('Aucun segment trouve');
    jobLog(job, `${segUrls.length} segments a telecharger`);

    // 2. Download segments (direct first, proxy fallback — batch of 60 for speed)
    const writeStream = fs.createWriteStream(combinedTs);
    let downloaded = 0;
    const BATCH = 60;
    let useProxy = false; // start direct, switch to proxy if first batch fails

    for (let i = 0; i < segUrls.length; i += BATCH) {
      const batch = segUrls.slice(i, i + BATCH);
      const buffers = await Promise.all(batch.map(async (url) => {
        try {
          const ctrl = new AbortController();
          const timer = setTimeout(() => ctrl.abort(), 15000); // 15s timeout per segment
          let r = await fetchUrl(url, useProxy, ctrl.signal);
          clearTimeout(timer);
          if (!r.ok && proxyBase && !useProxy) {
            const ctrl2 = new AbortController();
            const timer2 = setTimeout(() => ctrl2.abort(), 15000);
            r = await fetchUrl(url, true, ctrl2.signal);
            clearTimeout(timer2);
            if (r.ok) useProxy = true;
          }
          if (!r.ok) return Buffer.alloc(0);
          return Buffer.from(await r.arrayBuffer());
        } catch (e) { return Buffer.alloc(0); }
      }));
      for (const buf of buffers) {
        if (buf.length > 0) writeStream.write(buf);
        downloaded++;
      }
      const pct = Math.round(downloaded / segUrls.length * 70); // 0-70% for download
      jobProgress(job, pct);
      if (downloaded % 60 === 0 || downloaded === segUrls.length) {
        jobLog(job, `Segments: ${downloaded}/${segUrls.length}`);
      }
    }

    // Heartbeat pendant le flush du writeStream (peut prendre 30-60s pour 1GB+)
    // Sans ça, les clients SSE coupent par timeout
    const flushHeartbeat = setInterval(() => {
      jobLog(job, 'Ecriture combined.ts en cours...');
    }, 10000);
    await new Promise((resolve) => { writeStream.end(resolve); });
    clearInterval(flushHeartbeat);

    const tsSize = fs.statSync(combinedTs).size;
    jobLog(job, `combined.ts = ${(tsSize / 1048576).toFixed(1)} MB`);
    if (tsSize < 1000) throw new Error('Fichier TS vide — echec telechargement');

    // 3. FFmpeg remux (copy first, re-encode fallback if stuck)
    jobProgress(job, 75);
    const safeName = (title || 'video').replace(/[<>:"/\\|?*]/g, '').substring(0, 100).trim();
    job.safeName = safeName;
    const outMp4 = path.join(tmpDir, 'output.mp4');

    // Remux TS → MP4 (no faststart — saves disk, not needed for direct download)
    function runFFmpegRemux(mode) {
      const label = mode === 'copy' ? 'remux' : 're-encode';
      jobLog(job, `FFmpeg ${label} TS → MP4...`);
      const args = ['-y',
        '-fflags', '+genpts+igndts+discardcorrupt',
        '-analyzeduration', '5000000', '-probesize', '5000000',
        '-err_detect', 'ignore_err',
        '-i', combinedTs];
      if (mode === 'copy') {
        args.push('-c', 'copy', '-copytb', '1', '-bsf:a', 'aac_adtstoasc');
      } else {
        args.push('-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '18', '-c:a', 'aac', '-b:a', '192k');
      }
      args.push('-max_muxing_queue_size', '9999', outMp4);

      return new Promise((resolve, reject) => {
        const ff = spawn('ffmpeg', args, { stdio: ['pipe', 'pipe', 'pipe'] });
        let lastProgress = '';
        let stuckCount = 0;
        let stderrBuf = '';
        const stuckLimit = mode === 'copy' ? 20 : 40;

        const watchdog = setInterval(() => {
          const m = stderrBuf.match(/time=(\d+:\d+:\d+\.\d+)/);
          const cur = m ? m[1] : '';
          if (cur && cur === lastProgress) { stuckCount++; } else { stuckCount = 0; }
          lastProgress = cur;
          if (stuckCount >= stuckLimit) {
            clearInterval(watchdog);
            jobLog(job, `FFmpeg ${label} bloque a ${cur} — kill`);
            ff.kill('SIGKILL');
            reject(new Error(`FFmpeg stuck at ${cur}`));
          }
        }, 3000);

        ff.stderr.on('data', chunk => {
          stderrBuf += chunk.toString();
          if (stderrBuf.length > 4096) stderrBuf = stderrBuf.slice(-4096);
          const m = stderrBuf.match(/time=(\d+:\d+:\d+\.\d+)/);
          if (m) jobLog(job, `FFmpeg: ${m[1]}`);
        });

        ff.on('close', code => {
          clearInterval(watchdog);
          // Delete combined.ts immediately to free disk
          try { fs.unlinkSync(combinedTs); } catch (e) {}
          if (code !== 0) {
            console.error(`[hls2mp4:${job.id}] FFmpeg ${label} stderr: ${stderrBuf.slice(-500)}`);
            reject(new Error(`FFmpeg ${label} code ${code}: ${stderrBuf.slice(-200)}`));
          } else {
            resolve();
          }
        });
        ff.on('error', e => { clearInterval(watchdog); reject(e); });
      });
    }

    // Try copy first, fallback to re-encode if stuck
    try {
      await runFFmpegRemux('copy');
    } catch (copyErr) {
      if (copyErr.message.includes('stuck')) {
        jobLog(job, 'Copy bloque — fallback re-encode...');
        jobProgress(job, 78);
        try { fs.unlinkSync(outMp4); } catch (e) {}
        await runFFmpegRemux('reencode');
      } else {
        throw copyErr;
      }
    }

    // Supprimer combined.ts immédiatement après remux — libère ~1GB+
    try { fs.unlinkSync(combinedTs); } catch (e) {}
    jobLog(job, 'combined.ts supprime (libere espace)');

    jobProgress(job, 95);
    job.mp4Path = outMp4;
    job.mp4Size = fs.statSync(outMp4).size;
    jobLog(job, `MP4 pret: ${(job.mp4Size / 1048576).toFixed(1)} MB`);
    jobProgress(job, 100);
    jobDone(job, 'done');

  } catch (err) {
    jobLog(job, `ERREUR: ${err.message}`);
    jobDone(job, 'error', err.message);
    // Cleanup immédiat sur erreur — ne pas garder des GB inutiles
    try { fs.rmSync(job.tmpDir, { recursive: true, force: true }); } catch (e) {}
    console.log(`[CLEANUP-ERROR] Job ${job.id} nettoye apres erreur`);
  }
  hlsTryNext(); // process next queued job
  }; // end processJob

  // Queue or start immediately
  if (hlsActiveCount() < MAX_HLS_CONCURRENT) {
    processJob();
  } else {
    jobLog(job, `File d'attente — position ${hlsQueue.length + 1} (max ${MAX_HLS_CONCURRENT} simultanes)`);
    hlsQueue.push(processJob);
  }
});

// SSE progress events (auth via ?s= query param since EventSource doesn't support headers)
app.get('/hls2mp4/events/:jobId', requireAnySecret, (req, res) => {
  const job = hlsJobs.get(req.params.jobId);
  if (!job) return res.status(404).json({ error: 'job not found' });

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.flushHeaders();

  // Send existing logs
  for (const line of job.logs) {
    res.write(`data: ${JSON.stringify({ type: 'log', data: line, progress: job.progress, status: job.status })}\n\n`);
  }

  // If already done, send final event and close
  if (job.status === 'done' || job.status === 'error') {
    res.write(`data: ${JSON.stringify({ type: 'done', status: job.status, error: job.error || null, mp4Size: job.mp4Size || 0 })}\n\n`);
    res.end();
    return;
  }

  // Subscribe to live events
  const listener = (evt) => {
    try {
      res.write(`data: ${JSON.stringify(evt)}\n\n`);
      if (evt.type === 'done') res.end();
    } catch (e) {}
  };
  job.listeners.add(listener);

  req.on('close', () => {
    job.listeners.delete(listener);
  });
});

// Poll job status (fallback when SSE drops on mobile)
app.get('/hls2mp4/poll/:jobId', requireAnySecret, (req, res) => {
  const job = hlsJobs.get(req.params.jobId);
  if (!job) return res.status(404).json({ error: 'job not found' });
  res.json({ status: job.status, progress: job.progress, mp4Size: job.mp4Size || 0, error: job.error || null, lastLog: job.logs[job.logs.length - 1] || '' });
});

// Cancel a job (kill FFmpeg, cleanup)
app.delete('/hls2mp4/:jobId', requireAnySecret, (req, res) => {
  const job = hlsJobs.get(req.params.jobId);
  if (!job) return res.status(404).json({ error: 'job not found' });

  job.status = 'cancelled';
  if (job.listeners) job.listeners.forEach(fn => fn({ type: 'done', status: 'cancelled', error: 'Annule par utilisateur', mp4Size: 0 }));

  // Cleanup files
  try { fs.rmSync(job.tmpDir, { recursive: true, force: true }); } catch (e) {}
  hlsJobs.delete(job.id);

  console.log(`[hls2mp4:${job.id}] Cancelled by user`);
  res.json({ ok: true });
});

// Download completed MP4 (auth via ?s= query param or Authorization header)
// Also serves orphan files (job completed but Map entry cleaned up)
app.get('/hls2mp4/file/:jobId', requireAnySecret, (req, res) => {
  const jobId = req.params.jobId;
  const job = hlsJobs.get(jobId);

  // Try job from Map first
  let mp4Path, mp4Size, safeName, tmpDir;
  if (job) {
    if (job.status !== 'done') return res.status(409).json({ error: 'not ready', status: job.status });
    if (!job.mp4Path || !fs.existsSync(job.mp4Path)) return res.status(410).json({ error: 'file gone' });
    mp4Path = job.mp4Path;
    mp4Size = job.mp4Size;
    safeName = job.safeName || 'video';
    tmpDir = job.tmpDir;
  } else {
    // Orphan recovery: check if file exists on disk even though job is not in Map
    const hlsBase = fs.existsSync('/data') ? '/data' : os.tmpdir();
    const orphanDir = path.join(hlsBase, 'hls_' + jobId);
    const orphanMp4 = path.join(orphanDir, 'output.mp4');
    if (!fs.existsSync(orphanMp4)) return res.status(404).json({ error: 'job not found' });
    mp4Path = orphanMp4;
    mp4Size = fs.statSync(orphanMp4).size;
    safeName = 'video';
    tmpDir = orphanDir;
    console.log(`[hls2mp4:${jobId}] Orphan file recovery: ${(mp4Size / 1048576).toFixed(1)} MB`);
  }

  res.setHeader('Content-Type', 'video/mp4');
  res.setHeader('Content-Length', mp4Size);
  res.setHeader('Content-Disposition', `attachment; filename="${encodeURIComponent(safeName)}.mp4"; filename*=UTF-8''${encodeURIComponent(safeName)}.mp4`);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Expose-Headers', 'Content-Disposition, Content-Length');

  const fileStream = fs.createReadStream(mp4Path);
  fileStream.pipe(res);
  fileStream.on('end', () => {
    // Cleanup after download
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (e) {}
    if (job) hlsJobs.delete(job.id);
  });
  fileStream.on('error', err => {
    console.error(`[hls2mp4:${jobId}] Stream error:`, err.message);
    try { res.end(); } catch (e) {}
  });
});

// ---------------------------------------------------------------------------
// POST /slideshow — Génère un slideshow vidéo MP4 à partir d'images + audio
// Input JSON: { images: [base64...], audio: base64, durations: [10,8,...], texts?: [str...], width: 1080, height: 1920 }
// Output: MP4 binaire streamé en réponse
// ---------------------------------------------------------------------------

app.post('/slideshow', requireAnySecret, async (req, res) => {
  const { images, audio, durations, texts, width = 1080, height = 1920 } = req.body;

  if (!images || !Array.isArray(images) || images.length === 0) {
    return res.status(400).json({ error: 'images[] required (base64 PNG/JPG)' });
  }
  if (!audio) {
    return res.status(400).json({ error: 'audio required (base64 MP3)' });
  }
  if (!durations || !Array.isArray(durations) || durations.length !== images.length) {
    return res.status(400).json({ error: 'durations[] required, same length as images[]' });
  }

  const jobId = `slide-${Date.now().toString(36)}`;
  const tmpDir = path.join(os.tmpdir(), jobId);
  fs.mkdirSync(tmpDir, { recursive: true });

  console.log(`[${jobId}] Slideshow: ${images.length} images, ${width}x${height}`);

  try {
    // Write images to disk
    const imgPaths = [];
    for (let i = 0; i < images.length; i++) {
      const imgBuf = Buffer.from(images[i], 'base64');
      const imgPath = path.join(tmpDir, `img_${i}.png`);
      fs.writeFileSync(imgPath, imgBuf);
      imgPaths.push(imgPath);
    }

    // Write audio to disk
    const audioPath = path.join(tmpDir, 'audio.mp3');
    fs.writeFileSync(audioPath, Buffer.from(audio, 'base64'));

    const outPath = path.join(tmpDir, 'output.mp4');

    // Build FFmpeg command for slideshow with fade transitions
    const ffArgs = [];
    const FADE_DUR = 0.5;

    // Input files: each image looped for its duration
    for (let i = 0; i < imgPaths.length; i++) {
      ffArgs.push('-loop', '1', '-t', String(durations[i]), '-i', imgPaths[i]);
    }
    // Audio input
    ffArgs.push('-i', audioPath);

    // Build filter_complex: scale + fade out each image, then concat
    const filters = [];
    const concatInputs = [];

    for (let i = 0; i < imgPaths.length; i++) {
      const dur = durations[i];
      const fadeOutStart = Math.max(0, dur - FADE_DUR);
      let filter = `[${i}:v]scale=${width}:${height}:force_original_aspect_ratio=decrease,pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p`;
      // Optional text overlay
      if (texts && texts[i]) {
        const safeText = texts[i].replace(/\\/g, '\\\\\\\\').replace(/'/g, "\\u2019").replace(/:/g, '\\\\:').replace(/\[/g, '\\\\[').replace(/]/g, '\\\\]').replace(/%/g, '%%');
        filter += `,drawtext=fontfile=/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf:text='${safeText}':fontsize=${Math.round(height * 0.042)}:fontcolor=white:x=(w-text_w)/2:y=h*0.18:box=1:boxcolor=black@0.55:boxborderw=14:shadowx=2:shadowy=2:shadowcolor=black@0.8`;
      }
      // Fade in on first and subsequent slides, fade out on all
      if (i > 0) {
        filter += `,fade=in:st=0:d=${FADE_DUR}`;
      }
      filter += `,fade=out:st=${fadeOutStart}:d=${FADE_DUR}[v${i}]`;
      filters.push(filter);
      concatInputs.push(`[v${i}]`);
    }

    // Concat all video streams
    filters.push(`${concatInputs.join('')}concat=n=${imgPaths.length}:v=1:a=0[outv]`);

    const audioIdx = imgPaths.length; // audio is the last input
    ffArgs.push(
      '-filter_complex', filters.join(';'),
      '-map', '[outv]',
      '-map', `${audioIdx}:a`,
      '-c:v', 'libx264',
      '-preset', 'fast',
      '-crf', '23',
      '-c:a', 'aac',
      '-b:a', '128k',
      '-shortest',
      '-movflags', '+faststart',
      '-y', outPath
    );

    console.log(`[${jobId}] FFmpeg slideshow start...`);

    await new Promise((resolve, reject) => {
      const ff = spawn('ffmpeg', ffArgs, { stdio: ['ignore', 'pipe', 'pipe'] });
      let stderr = '';
      ff.stderr.on('data', d => { stderr += d.toString(); });
      ff.on('close', code => {
        if (code === 0) resolve();
        else reject(new Error(`FFmpeg exit ${code}: ${stderr.slice(-500)}`));
      });
      ff.on('error', reject);

      // Timeout 120s
      setTimeout(() => {
        try { ff.kill('SIGKILL'); } catch (_) {}
        reject(new Error('FFmpeg timeout 120s'));
      }, 120000);
    });

    const mp4Stat = fs.statSync(outPath);
    console.log(`[${jobId}] Slideshow OK: ${(mp4Stat.size / 1048576).toFixed(1)} MB`);

    res.setHeader('Content-Type', 'video/mp4');
    res.setHeader('Content-Length', mp4Stat.size);
    res.setHeader('Content-Disposition', `attachment; filename="slideshow-${jobId}.mp4"`);

    const stream = fs.createReadStream(outPath);
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
    console.error(`[${jobId}] Slideshow error:`, err.message);
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    if (!res.headersSent) {
      res.status(500).json({ error: err.message });
    }
  }
});

// ---------------------------------------------------------------------------
// POST /merge — Merge video + audio (replace audio track)
// Input: { video: base64_MP4, audio: base64_MP3 }
// Output: MP4 with original video + new audio
// ---------------------------------------------------------------------------
app.post('/merge', requireAnySecret, async (req, res) => {
  const { video, videoUrl, audio } = req.body;

  if (!video && !videoUrl) return res.status(400).json({ error: 'video (base64) or videoUrl required' });
  if (!audio) return res.status(400).json({ error: 'audio required (base64 MP3)' });

  const jobId = `merge-${Date.now().toString(36)}`;
  const tmpDir = path.join(os.tmpdir(), jobId);
  fs.mkdirSync(tmpDir, { recursive: true });

  const audioSizeKB = Math.round(audio.length * 3 / 4 / 1024);
  console.log(`[${jobId}] Merge: ${videoUrl ? 'URL' : `base64 ${Math.round(video.length * 3/4/1024)}KB`} + audio ${audioSizeKB}KB`);

  try {
    const videoPath = path.join(tmpDir, 'input.mp4');
    const audioPath = path.join(tmpDir, 'audio.mp3');
    const outPath = path.join(tmpDir, 'output.mp4');

    // Video: download from URL or decode base64
    if (videoUrl) {
      const https = require('https');
      const http = require('http');
      await new Promise((resolve, reject) => {
        const MAX_REDIRECTS = 5;
        let redirectCount = 0;
        const timer = setTimeout(() => reject(new Error('Video download timeout 60s')), 60000);

        function doGet(url) {
          const client = url.startsWith('https') ? https : http;
          client.get(url, (response) => {
            // Follow 301/302/303/307/308 redirects
            if ([301, 302, 303, 307, 308].includes(response.statusCode) && response.headers.location) {
              redirectCount++;
              if (redirectCount > MAX_REDIRECTS) {
                clearTimeout(timer);
                reject(new Error(`Too many redirects (>${MAX_REDIRECTS})`));
                return;
              }
              const redirectUrl = response.headers.location.startsWith('http')
                ? response.headers.location
                : new URL(response.headers.location, url).href;
              console.log(`[${jobId}] Redirect ${redirectCount}: ${response.statusCode} → ${redirectUrl.slice(0, 120)}...`);
              response.resume(); // drain the response
              doGet(redirectUrl);
              return;
            }
            if (response.statusCode !== 200) {
              clearTimeout(timer);
              reject(new Error(`Video download HTTP ${response.statusCode}`));
              return;
            }
            const fileStream = fs.createWriteStream(videoPath);
            response.pipe(fileStream);
            fileStream.on('finish', () => { clearTimeout(timer); fileStream.close(resolve); });
            fileStream.on('error', (err) => { clearTimeout(timer); reject(err); });
          }).on('error', (err) => { clearTimeout(timer); reject(err); });
        }

        doGet(videoUrl);
      });
      const dlSize = fs.statSync(videoPath).size;
      console.log(`[${jobId}] Video downloaded: ${(dlSize / 1048576).toFixed(1)} MB`);
    } else {
      fs.writeFileSync(videoPath, Buffer.from(video, 'base64'));
    }
    fs.writeFileSync(audioPath, Buffer.from(audio, 'base64'));

    const ffArgs = [
      '-i', videoPath,
      '-i', audioPath,
      '-map', '0:v',
      '-map', '1:a',
      '-c:v', 'copy',
      '-c:a', 'aac',
      '-b:a', '128k',
      '-shortest',
      '-movflags', '+faststart',
      '-y', outPath
    ];

    await new Promise((resolve, reject) => {
      const ff = spawn('ffmpeg', ffArgs, { stdio: ['ignore', 'pipe', 'pipe'] });
      let stderr = '';
      ff.stderr.on('data', d => { stderr += d.toString(); });
      ff.on('close', code => {
        if (code === 0) resolve();
        else reject(new Error(`FFmpeg exit ${code}: ${stderr.slice(-500)}`));
      });
      ff.on('error', reject);
      setTimeout(() => {
        try { ff.kill('SIGKILL'); } catch (_) {}
        reject(new Error('FFmpeg merge timeout 120s'));
      }, 120000);
    });

    const mp4Stat = fs.statSync(outPath);
    console.log(`[${jobId}] Merge OK: ${(mp4Stat.size / 1048576).toFixed(1)} MB`);

    res.setHeader('Content-Type', 'video/mp4');
    res.setHeader('Content-Length', mp4Stat.size);
    res.setHeader('Content-Disposition', `attachment; filename="merge-${jobId}.mp4"`);

    const stream = fs.createReadStream(outPath);
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
    console.error(`[${jobId}] Merge error:`, err.message);
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    if (!res.headersSent) {
      res.status(500).json({ error: err.message });
    }
  }
});

// POST /resize — exact image resize (upscale/downscale + crop to exact dimensions)
app.post('/resize', requireAnySecret, async (req, res) => {
  const { image, width, height } = req.body;
  if (!image) return res.status(400).json({ error: 'image required (base64)' });
  if (!width || !height) return res.status(400).json({ error: 'width and height required' });

  const jobId = `resize-${Date.now().toString(36)}`;
  const tmpDir = path.join(os.tmpdir(), jobId);
  fs.mkdirSync(tmpDir, { recursive: true });

  console.log(`[${jobId}] Resize: ${Math.round(image.length * 3/4/1024)}KB → ${width}x${height}`);

  try {
    const inPath = path.join(tmpDir, 'input.jpg');
    const outPath = path.join(tmpDir, 'output.jpg');

    fs.writeFileSync(inPath, Buffer.from(image, 'base64'));

    // Scale to fill target dimensions (preserving aspect ratio), then crop to exact size
    const ffArgs = [
      '-i', inPath,
      '-vf', `scale=${width}:${height}:force_original_aspect_ratio=increase,crop=${width}:${height}`,
      '-q:v', '2',
      '-y', outPath
    ];

    await new Promise((resolve, reject) => {
      const ff = spawn('ffmpeg', ffArgs, { stdio: ['ignore', 'pipe', 'pipe'] });
      let stderr = '';
      ff.stderr.on('data', d => { stderr += d.toString(); });
      ff.on('close', code => {
        if (code === 0) resolve();
        else reject(new Error(`FFmpeg exit ${code}: ${stderr.slice(-300)}`));
      });
      ff.on('error', reject);
      setTimeout(() => { try { ff.kill('SIGKILL'); } catch (_) {} reject(new Error('Resize timeout 30s')); }, 30000);
    });

    const outBuf = fs.readFileSync(outPath);
    const outBase64 = outBuf.toString('base64');
    console.log(`[${jobId}] Resize OK: ${(outBuf.length / 1024).toFixed(0)}KB`);

    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    res.json({ ok: true, base64: outBase64, sizeKB: Math.round(outBuf.length / 1024) });
  } catch (err) {
    console.error(`[${jobId}] Resize error:`, err.message);
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    if (!res.headersSent) res.status(500).json({ error: err.message });
  }
});

// ---------------------------------------------------------------------------
// POST /slideshow-pip — Slideshow with avatar video in PiP overlay
// Input: { images: base64[], avatarUrl: string, durations: number[], texts?: string[], width?, height?, pipSize?, pipPosition? }
// Output: MP4 with slides fullscreen + avatar PiP circle overlay, audio from avatar
// ---------------------------------------------------------------------------
app.post('/slideshow-pip', requireAnySecret, async (req, res) => {
  const { images, avatarUrl, avatarVideo, durations, texts, width = 720, height = 1280, pipSize = 30, pipPosition = 'bottom-right' } = req.body;

  if (!images || !Array.isArray(images) || images.length === 0) {
    return res.status(400).json({ error: 'images[] required (base64 PNG/JPG)' });
  }
  if (!avatarUrl && !avatarVideo) {
    return res.status(400).json({ error: 'avatarUrl or avatarVideo required' });
  }
  if (!durations || !Array.isArray(durations) || durations.length !== images.length) {
    return res.status(400).json({ error: 'durations[] required, same length as images[]' });
  }

  const jobId = `pip-${Date.now().toString(36)}`;
  const tmpDir = path.join(os.tmpdir(), jobId);
  fs.mkdirSync(tmpDir, { recursive: true });

  console.log(`[${jobId}] Slideshow-PiP: ${images.length} slides, ${width}x${height}, pip=${pipSize}%`);

  try {
    // Write slide images to disk
    const imgPaths = [];
    for (let i = 0; i < images.length; i++) {
      const imgBuf = Buffer.from(images[i], 'base64');
      const imgPath = path.join(tmpDir, `img_${i}.png`);
      fs.writeFileSync(imgPath, imgBuf);
      imgPaths.push(imgPath);
    }

    // Download or write avatar video
    const avatarPath = path.join(tmpDir, 'avatar.mp4');
    if (avatarVideo) {
      fs.writeFileSync(avatarPath, Buffer.from(avatarVideo, 'base64'));
    } else {
      // Download from URL with redirect support
      const downloadVideo = (url, dest, redirects = 5) => new Promise((resolve, reject) => {
        if (redirects <= 0) return reject(new Error('Too many redirects'));
        const mod = url.startsWith('https') ? require('https') : require('http');
        mod.get(url, { timeout: 60000 }, (response) => {
          if ([301, 302, 303, 307, 308].includes(response.statusCode) && response.headers.location) {
            return downloadVideo(response.headers.location, dest, redirects - 1).then(resolve).catch(reject);
          }
          if (response.statusCode !== 200) return reject(new Error(`Download failed: HTTP ${response.statusCode}`));
          const ws = fs.createWriteStream(dest);
          response.pipe(ws);
          ws.on('finish', () => ws.close(resolve));
          ws.on('error', reject);
        }).on('error', reject);
      });
      await downloadVideo(avatarUrl, avatarPath);
    }

    const avatarStat = fs.statSync(avatarPath);
    console.log(`[${jobId}] Avatar video: ${(avatarStat.size / 1048576).toFixed(1)} MB`);

    const outPath = path.join(tmpDir, 'output.mp4');

    // Calculate PiP dimensions
    const pipPx = Math.round(height * pipSize / 100); // pip diameter in pixels
    const margin = Math.round(height * 0.03); // 3% margin

    // PiP position
    let pipX, pipY;
    switch (pipPosition) {
      case 'bottom-left':  pipX = margin; pipY = `H-${pipPx}-${margin}`; break;
      case 'top-right':    pipX = `W-${pipPx}-${margin}`; pipY = margin; break;
      case 'top-left':     pipX = margin; pipY = margin; break;
      default:             pipX = `W-${pipPx}-${margin}`; pipY = `H-${pipPx}-${margin}`; break; // bottom-right
    }

    // Build FFmpeg command
    const ffArgs = [];
    const FADE_DUR = 0.5;

    // Input: slide images
    for (let i = 0; i < imgPaths.length; i++) {
      ffArgs.push('-loop', '1', '-t', String(durations[i]), '-i', imgPaths[i]);
    }
    // Input: avatar video
    ffArgs.push('-i', avatarPath);

    const avatarIdx = imgPaths.length; // avatar input index

    // Build filter_complex
    const filters = [];
    const concatInputs = [];

    // 1. Process each slide (scale + text overlay + fade)
    for (let i = 0; i < imgPaths.length; i++) {
      const dur = durations[i];
      const fadeOutStart = Math.max(0, dur - FADE_DUR);
      let filter = `[${i}:v]scale=${width}:${height}:force_original_aspect_ratio=decrease,pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p`;
      // Optional text overlay
      if (texts && texts[i]) {
        const safeText = texts[i].replace(/\\/g, '\\\\\\\\').replace(/'/g, '\u2019').replace(/:/g, '\\\\:').replace(/\[/g, '\\\\[').replace(/]/g, '\\\\]').replace(/%/g, '%%');
        filter += `,drawtext=fontfile=/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf:text='${safeText}':fontsize=${Math.round(height * 0.042)}:fontcolor=white:x=(w-text_w)/2:y=h*0.18:box=1:boxcolor=black@0.55:boxborderw=14:shadowx=2:shadowy=2:shadowcolor=black@0.8`;
      }
      if (i > 0) filter += `,fade=in:st=0:d=${FADE_DUR}`;
      filter += `,fade=out:st=${fadeOutStart}:d=${FADE_DUR}[v${i}]`;
      filters.push(filter);
      concatInputs.push(`[v${i}]`);
    }

    // 2. Concat all slides into background
    filters.push(`${concatInputs.join('')}concat=n=${imgPaths.length}:v=1:a=0[bg]`);

    // 3. Scale avatar to PiP size and crop to circle
    // Crop to square first, then scale, then create circular mask
    filters.push(`[${avatarIdx}:v]scale=${pipPx}:${pipPx}:force_original_aspect_ratio=decrease,pad=${pipPx}:${pipPx}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuva420p,geq=lum='p(X,Y)':cb='p(X,Y)':cr='p(X,Y)':a='if(gt(pow(X-${pipPx}/2,2)+pow(Y-${pipPx}/2,2),pow(${pipPx}/2-4,2)),0,255)'[pip]`);

    // 4. Overlay PiP on background
    filters.push(`[bg][pip]overlay=${pipX}:${pipY}:shortest=1[outv]`);

    ffArgs.push(
      '-filter_complex', filters.join(';'),
      '-map', '[outv]',
      '-map', `${avatarIdx}:a`,
      '-c:v', 'libx264',
      '-preset', 'fast',
      '-crf', '23',
      '-c:a', 'aac',
      '-b:a', '128k',
      '-shortest',
      '-movflags', '+faststart',
      '-y', outPath
    );

    console.log(`[${jobId}] FFmpeg slideshow-pip start...`);

    await new Promise((resolve, reject) => {
      const ff = spawn('ffmpeg', ffArgs, { stdio: ['ignore', 'pipe', 'pipe'] });
      let stderr = '';
      ff.stderr.on('data', d => { stderr += d.toString(); });
      ff.on('close', code => {
        if (code === 0) resolve();
        else reject(new Error(`FFmpeg exit ${code}: ${stderr.slice(-500)}`));
      });
      ff.on('error', reject);
      setTimeout(() => {
        try { ff.kill('SIGKILL'); } catch (_) {}
        reject(new Error('FFmpeg timeout 180s'));
      }, 180000);
    });

    const mp4Stat = fs.statSync(outPath);
    console.log(`[${jobId}] Slideshow-PiP OK: ${(mp4Stat.size / 1048576).toFixed(1)} MB`);

    res.setHeader('Content-Type', 'video/mp4');
    res.setHeader('Content-Length', mp4Stat.size);
    res.setHeader('Content-Disposition', `attachment; filename="pip-${jobId}.mp4"`);

    const stream = fs.createReadStream(outPath);
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
    console.error(`[${jobId}] Slideshow-PiP error:`, err.message);
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    if (!res.headersSent) {
      res.status(500).json({ error: err.message });
    }
  }
});

// ---------------------------------------------------------------------------
// POST /extract-frames — Extract frames from video at specific timestamps
// Input: { videoUrl, timestamps[], width?, height? }
// Output: { ok: true, frames: [{ timestamp, base64 }] }
// ---------------------------------------------------------------------------

app.post('/extract-frames', requireAnySecret, async (req, res) => {
  const { videoUrl, timestamps, width = 1080, height = 1920 } = req.body;

  if (!videoUrl) return res.status(400).json({ error: 'videoUrl required' });
  if (!timestamps || !Array.isArray(timestamps) || timestamps.length === 0) {
    return res.status(400).json({ error: 'timestamps[] required (array of seconds)' });
  }
  if (timestamps.length > 10) {
    return res.status(400).json({ error: 'Max 10 timestamps allowed' });
  }

  const jobId = `frames-${Date.now().toString(36)}`;
  const tmpDir = path.join(os.tmpdir(), jobId);
  fs.mkdirSync(tmpDir, { recursive: true });

  console.log(`[${jobId}] Extract-frames: ${timestamps.length} timestamps, ${width}x${height}, url=${videoUrl.slice(0, 80)}...`);

  try {
    // Download video from URL (same pattern as /merge videoUrl)
    const videoPath = path.join(tmpDir, 'input.mp4');
    const http = require('http');
    await new Promise((resolve, reject) => {
      const MAX_REDIRECTS = 5;
      let redirectCount = 0;
      const timer = setTimeout(() => reject(new Error('Video download timeout 60s')), 60000);

      function doGet(url) {
        const client = url.startsWith('https') ? https : http;
        client.get(url, (response) => {
          if ([301, 302, 303, 307, 308].includes(response.statusCode) && response.headers.location) {
            redirectCount++;
            if (redirectCount > MAX_REDIRECTS) {
              clearTimeout(timer);
              reject(new Error(`Too many redirects (>${MAX_REDIRECTS})`));
              return;
            }
            const redirectUrl = response.headers.location.startsWith('http')
              ? response.headers.location
              : new URL(response.headers.location, url).href;
            console.log(`[${jobId}] Redirect ${redirectCount}: ${response.statusCode} → ${redirectUrl.slice(0, 120)}...`);
            response.resume();
            doGet(redirectUrl);
            return;
          }
          if (response.statusCode !== 200) {
            clearTimeout(timer);
            reject(new Error(`Video download HTTP ${response.statusCode}`));
            return;
          }
          const fileStream = fs.createWriteStream(videoPath);
          response.pipe(fileStream);
          fileStream.on('finish', () => { clearTimeout(timer); fileStream.close(resolve); });
          fileStream.on('error', (err) => { clearTimeout(timer); reject(err); });
        }).on('error', (err) => { clearTimeout(timer); reject(err); });
      }

      doGet(videoUrl);
    });

    const dlSize = fs.statSync(videoPath).size;
    console.log(`[${jobId}] Video downloaded: ${(dlSize / 1048576).toFixed(1)} MB`);

    // Extract frame at each timestamp
    const frames = [];
    for (let i = 0; i < timestamps.length; i++) {
      const t = timestamps[i];
      const framePath = path.join(tmpDir, `frame_${i}.jpg`);

      await new Promise((resolve, reject) => {
        const ff = spawn('ffmpeg', [
          '-ss', String(t),
          '-i', videoPath,
          '-frames:v', '1',
          '-vf', `scale=${width}:${height}:force_original_aspect_ratio=decrease,pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2`,
          '-y', framePath
        ], { stdio: ['ignore', 'pipe', 'pipe'] });

        let stderr = '';
        ff.stderr.on('data', d => { stderr += d.toString(); });
        ff.on('close', code => {
          if (code === 0) resolve();
          else reject(new Error(`FFmpeg frame ${i} exit ${code}: ${stderr.slice(-300)}`));
        });
        ff.on('error', reject);

        // Timeout 60s per frame
        setTimeout(() => {
          try { ff.kill('SIGKILL'); } catch (_) {}
          reject(new Error(`FFmpeg frame ${i} timeout 60s`));
        }, 60000);
      });

      const frameData = fs.readFileSync(framePath);
      frames.push({ timestamp: t, base64: frameData.toString('base64') });
      console.log(`[${jobId}] Frame ${i}: t=${t}s → ${(frameData.length / 1024).toFixed(0)} KB`);
    }

    console.log(`[${jobId}] Extract-frames OK: ${frames.length} frames`);
    res.json({ ok: true, frames });

  } catch (err) {
    console.error(`[${jobId}] Extract-frames error:`, err.message);
    if (!res.headersSent) {
      res.status(500).json({ error: err.message });
    }
  } finally {
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
  }
});

// ---------------------------------------------------------------------------
// POST /ken-burns — Apply Ken Burns effect to a still image → MP4
// Input: { image (base64), effect, duration?, width?, height? }
// Output: MP4 binary stream
// ---------------------------------------------------------------------------

app.post('/ken-burns', requireAnySecret, async (req, res) => {
  const { image, effect = 'zoom_in', duration = 5, width = 1080, height = 1920 } = req.body;

  if (!image) return res.status(400).json({ error: 'image required (base64)' });

  const validEffects = ['zoom_in', 'zoom_out', 'pan_down', 'pan_right'];
  if (!validEffects.includes(effect)) {
    return res.status(400).json({ error: `effect must be one of: ${validEffects.join(', ')}` });
  }

  const dur = Math.min(10, Math.max(1, duration));
  const fps = 30;

  const jobId = `kb-${Date.now().toString(36)}`;
  const tmpDir = path.join(os.tmpdir(), jobId);
  fs.mkdirSync(tmpDir, { recursive: true });

  console.log(`[${jobId}] Ken-Burns: effect=${effect}, duration=${dur}s, ${width}x${height}`);

  try {
    // Write image to disk
    const imgPath = path.join(tmpDir, 'input.png');
    fs.writeFileSync(imgPath, Buffer.from(image, 'base64'));
    const outPath = path.join(tmpDir, 'output.mp4');

    // Build zoompan filter based on effect
    const d = Math.round(fps * dur);
    let zoompanFilter;
    switch (effect) {
      case 'zoom_in':
        zoompanFilter = `zoompan=z='min(zoom+0.001,1.5)':d=${d}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${width}x${height}:fps=${fps}`;
        break;
      case 'zoom_out':
        zoompanFilter = `zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.001))':d=${d}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=${width}x${height}:fps=${fps}`;
        break;
      case 'pan_down':
        zoompanFilter = `zoompan=z=1.3:d=${d}:x='(iw-iw/zoom)/2':y='min((ih-ih/zoom),on*2)':s=${width}x${height}:fps=${fps}`;
        break;
      case 'pan_right':
        zoompanFilter = `zoompan=z=1.2:d=${d}:x='min(on*3,(iw-iw/zoom))':y='(ih-ih/zoom)/2':s=${width}x${height}:fps=${fps}`;
        break;
    }

    const ffArgs = [
      '-loop', '1',
      '-i', imgPath,
      '-vf', `scale=2000:-1,${zoompanFilter}`,
      '-c:v', 'libx264',
      '-preset', 'fast',
      '-crf', '23',
      '-pix_fmt', 'yuv420p',
      '-movflags', '+faststart',
      '-t', String(dur),
      '-y', outPath
    ];

    await new Promise((resolve, reject) => {
      const ff = spawn('ffmpeg', ffArgs, { stdio: ['ignore', 'pipe', 'pipe'] });
      let stderr = '';
      ff.stderr.on('data', d => { stderr += d.toString(); });
      ff.on('close', code => {
        if (code === 0) resolve();
        else reject(new Error(`FFmpeg exit ${code}: ${stderr.slice(-500)}`));
      });
      ff.on('error', reject);

      // Timeout 60s
      setTimeout(() => {
        try { ff.kill('SIGKILL'); } catch (_) {}
        reject(new Error('FFmpeg ken-burns timeout 60s'));
      }, 60000);
    });

    const mp4Stat = fs.statSync(outPath);
    console.log(`[${jobId}] Ken-Burns OK: ${(mp4Stat.size / 1048576).toFixed(1)} MB`);

    res.setHeader('Content-Type', 'video/mp4');
    res.setHeader('Content-Length', mp4Stat.size);
    res.setHeader('Content-Disposition', `attachment; filename="kenburns-${jobId}.mp4"`);

    const stream = fs.createReadStream(outPath);
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
    console.error(`[${jobId}] Ken-Burns error:`, err.message);
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    if (!res.headersSent) {
      res.status(500).json({ error: err.message });
    }
  }
});

// ---------------------------------------------------------------------------
// POST /gemini-upload — Upload a file to Gemini Files API (proxy for n8n sandbox)
// Input: { base64, mimeType, displayName, geminiKey }
// Output: JSON { ok, file: { name, uri, state, mimeType, sizeBytes } }
// ---------------------------------------------------------------------------

app.post('/gemini-upload', requireAnySecret, async (req, res) => {
  const { base64, mimeType, displayName, geminiKey } = req.body || {};
  if (!base64 || !mimeType || !geminiKey) {
    return res.status(400).json({ ok: false, error: 'base64, mimeType, geminiKey required' });
  }

  const jobId = Math.random().toString(36).slice(2, 8);
  console.log(`[${jobId}] Gemini upload: ${displayName || 'unnamed'} (${mimeType}, ${(base64.length * 0.75 / 1024).toFixed(0)} KB)`);

  try {
    const fileBuffer = Buffer.from(base64, 'base64');
    const https = require('https');

    // Resumable upload: Step 1 — Initiate
    const initResp = await new Promise((resolve, reject) => {
      const initReq = https.request({
        hostname: 'generativelanguage.googleapis.com',
        path: '/upload/v1beta/files?key=' + geminiKey,
        method: 'POST',
        headers: {
          'X-Goog-Upload-Protocol': 'resumable',
          'X-Goog-Upload-Command': 'start',
          'X-Goog-Upload-Header-Content-Length': String(fileBuffer.length),
          'X-Goog-Upload-Header-Content-Type': mimeType,
          'Content-Type': 'application/json'
        }
      }, (r) => {
        const uploadUrl = r.headers['x-goog-upload-url'];
        let body = '';
        r.on('data', c => body += c);
        r.on('end', () => resolve({ uploadUrl, statusCode: r.statusCode, body }));
      });
      initReq.on('error', reject);
      initReq.write(JSON.stringify({ file: { displayName: displayName || 'upload', mimeType: mimeType } }));
      initReq.end();
    });

    if (!initResp.uploadUrl) {
      return res.status(500).json({ ok: false, error: 'No upload URL from Gemini', status: initResp.statusCode, body: initResp.body.substring(0, 300) });
    }

    // Resumable upload: Step 2 — Upload bytes
    const uploadResult = await new Promise((resolve, reject) => {
      const url = new URL(initResp.uploadUrl);
      const upReq = https.request({
        hostname: url.hostname,
        path: url.pathname + url.search,
        method: 'POST',
        headers: {
          'Content-Length': String(fileBuffer.length),
          'X-Goog-Upload-Offset': '0',
          'X-Goog-Upload-Command': 'upload, finalize'
        }
      }, (r) => {
        let data = '';
        r.on('data', c => data += c);
        r.on('end', () => {
          try { resolve(JSON.parse(data)); }
          catch (e) { reject(new Error('Parse failed: ' + data.substring(0, 200))); }
        });
      });
      upReq.on('error', reject);
      upReq.write(fileBuffer);
      upReq.end();
    });

    console.log(`[${jobId}] Gemini upload OK: ${uploadResult?.file?.name} (${uploadResult?.file?.state})`);
    res.json({ ok: true, file: uploadResult?.file || uploadResult });

  } catch (err) {
    console.error(`[${jobId}] Gemini upload error:`, err.message);
    res.status(500).json({ ok: false, error: err.message });
  }
});

// ---------------------------------------------------------------------------
// POST /smart-zoom — Image + Gemini bounding box → zoompan towards target element
// Input: { image (base64), bbox: {x1,y1,x2,y2} (0-1000 coords), duration (1-10), width, height }
// Output: MP4 stream
// ---------------------------------------------------------------------------

app.post('/smart-zoom', requireAnySecret, async (req, res) => {
  const { image, bbox, duration = 4, width = 1080, height = 1920 } = req.body;

  if (!image) return res.status(400).json({ error: 'image required (base64)' });
  if (!bbox || bbox.x1 == null || bbox.y1 == null || bbox.x2 == null || bbox.y2 == null) {
    return res.status(400).json({ error: 'bbox required: {x1,y1,x2,y2} in 0-1000 coords' });
  }

  const dur = Math.min(10, Math.max(1, duration));
  const fps = 15;

  const jobId = `sz-${Date.now().toString(36)}`;
  const tmpDir = path.join(os.tmpdir(), jobId);
  fs.mkdirSync(tmpDir, { recursive: true });

  console.log(`[${jobId}] Smart-zoom: bbox=(${bbox.x1},${bbox.y1})-(${bbox.x2},${bbox.y2}), dur=${dur}s, ${width}x${height}`);

  try {
    const imgPath = path.join(tmpDir, 'input.png');
    fs.writeFileSync(imgPath, Buffer.from(image, 'base64'));
    const outPath = path.join(tmpDir, 'output.mp4');

    // Convert 0-1000 bounding box to relative 0-1
    const cx = ((bbox.x1 + bbox.x2) / 2) / 1000;
    const cy = ((bbox.y1 + bbox.y2) / 2) / 1000;
    const bboxW = Math.abs(bbox.x2 - bbox.x1) / 1000;
    const bboxH = Math.abs(bbox.y2 - bbox.y1) / 1000;

    // Zoom level: inverse of bbox size (smaller bbox = more zoom), clamped
    const zoomTarget = Math.min(3.0, Math.max(1.3, 1 / Math.max(bboxW, bboxH)));
    const d = Math.round(fps * dur);

    // zoompan: start wide, zoom toward the center of the bounding box
    const zoompanFilter = `zoompan=z='min(zoom+${((zoomTarget - 1) / d).toFixed(6)},${zoomTarget.toFixed(2)})':d=${d}:x='${cx}*iw-iw/zoom/2':y='${cy}*ih-ih/zoom/2':s=${width}x${height}:fps=${fps}`;

    const ffArgs = [
      '-loop', '1',
      '-i', imgPath,
      '-vf', `scale=2000:-1,${zoompanFilter}`,
      '-c:v', 'libx264',
      '-preset', 'ultrafast',
      '-crf', '23',
      '-pix_fmt', 'yuv420p',
      '-movflags', '+faststart',
      '-t', String(dur),
      '-y', outPath
    ];

    await new Promise((resolve, reject) => {
      const ff = spawn('ffmpeg', ffArgs, { stdio: ['ignore', 'pipe', 'pipe'] });
      let stderr = '';
      ff.stderr.on('data', d => { stderr += d.toString(); });
      ff.on('close', code => {
        if (code === 0) resolve();
        else reject(new Error(`FFmpeg exit ${code}: ${stderr.slice(-500)}`));
      });
      ff.on('error', reject);
      setTimeout(() => {
        try { ff.kill('SIGKILL'); } catch (_) {}
        reject(new Error('FFmpeg smart-zoom timeout 60s'));
      }, 60000);
    });

    const mp4Stat = fs.statSync(outPath);
    console.log(`[${jobId}] Smart-zoom OK: ${(mp4Stat.size / 1048576).toFixed(1)} MB`);

    res.setHeader('Content-Type', 'video/mp4');
    res.setHeader('Content-Length', mp4Stat.size);
    res.setHeader('Content-Disposition', `attachment; filename="smartzoom-${jobId}.mp4"`);

    const stream = fs.createReadStream(outPath);
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
    console.error(`[${jobId}] Smart-zoom error:`, err.message);
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    if (!res.headersSent) {
      res.status(500).json({ error: err.message });
    }
  }
});

// ---------------------------------------------------------------------------
// POST /speed-ramp — Apply variable speed to video segments
// Input: { video (base64) OR videoUrl, segments: [{start,end,speed}], width, height }
// Output: MP4 stream
// ---------------------------------------------------------------------------

app.post('/speed-ramp', requireAnySecret, async (req, res) => {
  const { video, videoUrl, segments, width = 1080, height = 1920 } = req.body;

  if (!video && !videoUrl) return res.status(400).json({ error: 'video (base64) or videoUrl required' });
  if (!segments || !Array.isArray(segments) || segments.length === 0) {
    return res.status(400).json({ error: 'segments required: [{start,end,speed}]' });
  }

  const jobId = `sr-${Date.now().toString(36)}`;
  const tmpDir = path.join(os.tmpdir(), jobId);
  fs.mkdirSync(tmpDir, { recursive: true });

  console.log(`[${jobId}] Speed-ramp: ${segments.length} segments, ${width}x${height}`);

  try {
    let videoPath;
    if (video) {
      videoPath = path.join(tmpDir, 'input.mp4');
      fs.writeFileSync(videoPath, Buffer.from(video, 'base64'));
    } else {
      // Download video from URL
      videoPath = path.join(tmpDir, 'input.mp4');
      await new Promise((resolve, reject) => {
        const download = (url, redirects = 0) => {
          if (redirects > 5) return reject(new Error('Too many redirects'));
          const proto = url.startsWith('https') ? https : require('http');
          proto.get(url, { timeout: 60000 }, (resp) => {
            if ([301, 302, 303, 307, 308].includes(resp.statusCode) && resp.headers.location) {
              return download(resp.headers.location, redirects + 1);
            }
            if (resp.statusCode !== 200) return reject(new Error(`HTTP ${resp.statusCode}`));
            const ws = fs.createWriteStream(videoPath);
            resp.pipe(ws);
            ws.on('finish', resolve);
            ws.on('error', reject);
          }).on('error', reject);
        };
        download(videoUrl);
      });
    }

    // Build complex filtergraph for speed ramping
    // Strategy: split into segments, apply setpts for each, concat
    const segParts = [];
    const filterParts = [];
    const concatInputs = [];

    for (let i = 0; i < segments.length; i++) {
      const seg = segments[i];
      const speed = Math.min(4.0, Math.max(0.25, seg.speed || 1));
      const trimFilter = `[0:v]trim=start=${seg.start}:end=${seg.end},setpts=${(1 / speed).toFixed(4)}*(PTS-STARTPTS),scale=${width}:${height}:force_original_aspect_ratio=decrease,pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2[v${i}]`;
      const atrimFilter = `[0:a]atrim=start=${seg.start}:end=${seg.end},asetpts=PTS-STARTPTS,atempo=${speed}[a${i}]`;
      filterParts.push(trimFilter);
      filterParts.push(atrimFilter);
      concatInputs.push(`[v${i}][a${i}]`);
    }

    const filterComplex = filterParts.join('; ') + `; ${concatInputs.join('')}concat=n=${segments.length}:v=1:a=1[outv][outa]`;

    const outPath = path.join(tmpDir, 'output.mp4');
    const ffArgs = [
      '-i', videoPath,
      '-filter_complex', filterComplex,
      '-map', '[outv]', '-map', '[outa]',
      '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
      '-c:a', 'aac', '-b:a', '128k',
      '-pix_fmt', 'yuv420p',
      '-movflags', '+faststart',
      '-y', outPath
    ];

    await new Promise((resolve, reject) => {
      const ff = spawn('ffmpeg', ffArgs, { stdio: ['ignore', 'pipe', 'pipe'] });
      let stderr = '';
      ff.stderr.on('data', d => { stderr += d.toString(); });
      ff.on('close', code => {
        if (code === 0) resolve();
        else reject(new Error(`FFmpeg exit ${code}: ${stderr.slice(-500)}`));
      });
      ff.on('error', reject);
      setTimeout(() => {
        try { ff.kill('SIGKILL'); } catch (_) {}
        reject(new Error('FFmpeg speed-ramp timeout 120s'));
      }, 120000);
    });

    const mp4Stat = fs.statSync(outPath);
    console.log(`[${jobId}] Speed-ramp OK: ${(mp4Stat.size / 1048576).toFixed(1)} MB`);

    res.setHeader('Content-Type', 'video/mp4');
    res.setHeader('Content-Length', mp4Stat.size);
    res.setHeader('Content-Disposition', `attachment; filename="speedramp-${jobId}.mp4"`);

    const stream = fs.createReadStream(outPath);
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
    console.error(`[${jobId}] Speed-ramp error:`, err.message);
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) {}
    if (!res.headersSent) {
      res.status(500).json({ error: err.message });
    }
  }
});

// ---------------------------------------------------------------------------
// POST /promo-assembly — Full promo video pipeline
// Input: {
//   clips: [{ image (base64), bbox (optional), effect, duration }],
//   audio (base64, optional) — voiceover/TTS,
//   music (base64, optional) — background music,
//   subtitles (string, optional) — ASS subtitle content,
//   hookText (string, optional) — text overlay on first clip,
//   ctaText (string, optional) — text overlay on last clip,
//   width, height, musicVolume (0-1)
// }
// Output: MP4 stream
// ---------------------------------------------------------------------------

app.post('/promo-assembly', requireAnySecret, async (req, res) => {
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
  fs.mkdirSync(tmpDir, { recursive: true });

  console.log(`[${jobId}] Promo-assembly: ${clips.length} clips, audio=${!!audio}, music=${!!music}, subs=${!!subtitles}`);

  try {
    activeJobs++;
    resetIdleTimer();

    // 1. Write all clip images to disk
    const clipPaths = [];
    for (let i = 0; i < clips.length; i++) {
      const clipPath = path.join(tmpDir, `clip-${i}.png`);
      fs.writeFileSync(clipPath, Buffer.from(clips[i].image, 'base64'));
      clipPaths.push(clipPath);
    }

    // 2. Generate individual clip videos (ken-burns or smart-zoom)
    const clipVideos = [];
    for (let i = 0; i < clips.length; i++) {
      const clip = clips[i];
      const dur = Math.min(10, Math.max(1, clip.duration || 4));
      const fps = 15;
      const d = Math.round(fps * dur);
      const clipOutPath = path.join(tmpDir, `clip-${i}.mp4`);

      let zoompanFilter;
      if (clip.bbox && clip.bbox.x1 != null) {
        // Smart zoom toward bounding box
        const cx = ((clip.bbox.x1 + clip.bbox.x2) / 2) / 1000;
        const cy = ((clip.bbox.y1 + clip.bbox.y2) / 2) / 1000;
        const bboxW = Math.abs(clip.bbox.x2 - clip.bbox.x1) / 1000;
        const bboxH = Math.abs(clip.bbox.y2 - clip.bbox.y1) / 1000;
        const zoomTarget = Math.min(3.0, Math.max(1.3, 1 / Math.max(bboxW, bboxH)));
        zoompanFilter = `zoompan=z='min(zoom+${((zoomTarget - 1) / d).toFixed(6)},${zoomTarget.toFixed(2)})':d=${d}:x='${cx}*iw-iw/zoom/2':y='${cy}*ih-ih/zoom/2':s=${width}x${height}:fps=${fps}`;
      } else {
        // Default ken-burns effect
        const effect = clip.effect || 'zoom_in';
        switch (effect) {
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

      // Add text overlay for hook (first clip) or CTA (last clip)
      let textFilter = '';
      if (i === 0 && hookText) {
        textFilter = `,drawtext=text='${hookText.replace(/'/g, "\\'")}':fontsize=48:fontcolor=white:borderw=3:bordercolor=black:x=(w-tw)/2:y=h*0.15:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`;
      } else if (i === clips.length - 1 && ctaText) {
        textFilter = `,drawtext=text='${ctaText.replace(/'/g, "\\'")}':fontsize=40:fontcolor=white:borderw=3:bordercolor=black:x=(w-tw)/2:y=h*0.80:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf`;
      }

      const ffArgs = [
        '-loop', '1',
        '-i', clipPaths[i],
        '-vf', `scale=2000:-1,${zoompanFilter}${textFilter}`,
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

    // 3. Create concat list
    const concatList = path.join(tmpDir, 'concat.txt');
    fs.writeFileSync(concatList, clipVideos.map(p => `file '${p}'`).join('\n'));

    // 4. Concat all clips
    const concatOut = path.join(tmpDir, 'concat.mp4');
    const concatArgs = [
      '-f', 'concat', '-safe', '0',
      '-i', concatList,
      '-c', 'copy',
      '-movflags', '+faststart',
      '-y', concatOut
    ];

    await new Promise((resolve, reject) => {
      const ff = spawn('ffmpeg', concatArgs, { stdio: ['ignore', 'pipe', 'pipe'] });
      let stderr = '';
      ff.stderr.on('data', d => { stderr += d.toString(); });
      ff.on('close', code => {
        if (code === 0) resolve();
        else reject(new Error(`FFmpeg concat exit ${code}: ${stderr.slice(-500)}`));
      });
      ff.on('error', reject);
      setTimeout(() => {
        try { ff.kill('SIGKILL'); } catch (_) {}
        reject(new Error('FFmpeg concat timeout 60s'));
      }, 60000);
    });

    console.log(`[${jobId}] Concat OK`);

    // ── Avatar overlay (optional) ──
    let videoForMix = concatOut; // default: no avatar
    if (avatarVideo || avatarUrl) {
      const avatarPath = path.join(tmpDir, 'avatar.mp4');
      if (avatarVideo) {
        fs.writeFileSync(avatarPath, Buffer.from(avatarVideo, 'base64'));
      } else if (avatarUrl) {
        // Download avatar from URL
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
        // Circular PiP overlay
        const pipPx = Math.round(height * 0.25); // 25% of height
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
        });

        console.log(`[${jobId}] Avatar bubble overlay done`);

      } else if (mode === 'split-top' || mode === 'split-bottom') {
        // Split screen: avatar takes top or bottom half
        const halfH = Math.round(height / 2);
        let filterComplex;
        if (mode === 'split-top') {
          // Avatar on top, clips on bottom
          filterComplex = `[1:v]scale=${width}:${halfH}:force_original_aspect_ratio=decrease,pad=${width}:${halfH}:(ow-iw)/2:(oh-ih)/2[av];[0:v]scale=${width}:${halfH}:force_original_aspect_ratio=decrease,pad=${width}:${halfH}:(ow-iw)/2:(oh-ih)/2[cl];[av][cl]vstack=inputs=2[outv]`;
        } else {
          // Clips on top, avatar on bottom
          filterComplex = `[0:v]scale=${width}:${halfH}:force_original_aspect_ratio=decrease,pad=${width}:${halfH}:(ow-iw)/2:(oh-ih)/2[cl];[1:v]scale=${width}:${halfH}:force_original_aspect_ratio=decrease,pad=${width}:${halfH}:(ow-iw)/2:(oh-ih)/2[av];[cl][av]vstack=inputs=2[outv]`;
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

      // Build audio mix filtergraph
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

      mixArgs.push(
        '-c:v', 'copy',
        '-c:a', 'aac', '-b:a', '256k',
        '-shortest',
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
    activeJobs--;
    resetIdleTimer();
  }
});

// ---------------------------------------------------------------------------
// Démarrage du serveur
// ---------------------------------------------------------------------------

app.listen(PORT, () => {
  console.log(`[SubWhisper FFmpeg Server v1.26.0] Démarré sur le port ${PORT}`);
  console.log(`  MAX_CONCURRENT_JOBS = ${MAX_CONCURRENT_JOBS}`);
  console.log(`  FLY_SECRET configuré: ${FLY_SECRET ? 'OUI' : 'NON (mode dev)'}`);
  console.log(`  CHUNK_MAX_BYTES = ${CHUNK_MAX_BYTES} bytes (${(CHUNK_MAX_BYTES / 1024 / 1024).toFixed(1)} MB PCM)`);
  console.log(`  CHUNK_DUR_SEC = ${CHUNK_DUR_SEC.toFixed(1)} secondes`);
  console.log(`  GROQ_MODEL = ${GROQ_MODEL}`);
  console.log(`  Node.js: ${process.version} — FormData natif: ${typeof FormData !== 'undefined' ? 'OUI' : 'NON'}`);
});

process.on('SIGTERM', () => {
  console.log('[SIGTERM] Arrêt demandé. Jobs actifs restants:', activeJobs);
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('[SIGINT] Arrêt. Jobs actifs restants:', activeJobs);
  process.exit(0);
});
