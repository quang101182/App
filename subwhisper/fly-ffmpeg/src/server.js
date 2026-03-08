/**
 * SubWhisper Fly.io FFmpeg Server
 * Version: 1.8.0 — chunkReport[] dans payload final (diagnostic sous-titres incomplets)
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
// App Express
// ---------------------------------------------------------------------------

const app = express();

// CORS middleware global — DOIT être avant toutes les routes
app.use((req, res, next) => {
  res.set({
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  });
  if (req.method === 'OPTIONS') return res.status(204).end();
  next();
});

app.use(express.json({ limit: '1mb' }));

// Auth middleware that accepts FLY_SECRET or WORKER_SECRET
function requireAnySecret(req, res, next) {
  const auth = req.headers['authorization'] || '';
  const token = auth.startsWith('Bearer ') ? auth.slice(7) : '';
  if (!token) return res.status(401).json({ error: 'Missing Authorization header' });
  const flySecret = process.env.FLY_SECRET || '';
  const workerSecret = process.env.WORKER_SECRET || '';
  if ((flySecret && token === flySecret) || (workerSecret && token === workerSecret)) return next();
  // Also accept gateway WORKER_SECRET from KV (passed as query param for convenience)
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
    version: '1.8.0'
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
          console.log(`[${jobId}] Header WAV parsé. Sample rate: ${sampleRate} Hz, Channels: ${numChannels}`);
          const estimatedChunks = dataSize > 0 ? Math.ceil(dataSize / CHUNK_MAX_BYTES) : '?';
          const estimatedMin = bytesPerSec > 0 ? (dataSize / bytesPerSec / 60).toFixed(1) : '?';
          updateWorker(workerCallbackUrl, workerSecret, {
            jobId,
            progress: 15,
            log: `📐 Audio: ${estimatedMin}min détectés — ~${estimatedChunks} chunks estimés`,
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
// POST /hls2mp4 — Download HLS m3u8, remux to MP4 via FFmpeg, stream result
// Handles any file size: FFmpeg reads segments directly from URLs, zero disk for video data
// ---------------------------------------------------------------------------

app.post('/hls2mp4', requireAnySecret, async (req, res) => {
  const { m3u8Url, title, proxyBase } = req.body || {};
  if (!m3u8Url) return res.status(400).json({ error: 'missing m3u8Url' });

  const jobTag = `[hls2mp4:${Date.now().toString(36)}]`;
  console.log(`${jobTag} Start — ${m3u8Url}`);

  const tmpDir = path.join(os.tmpdir(), 'hls_' + Date.now());
  fs.mkdirSync(tmpDir, { recursive: true });
  const combinedTs = path.join(tmpDir, 'combined.ts');

  // Helper: fetch a URL (optionally via proxy)
  async function fetchUrl(url) {
    const finalUrl = proxyBase ? `${proxyBase}${encodeURIComponent(url)}` : url;
    return fetch(finalUrl, { headers: { ...CHROME_HEADERS, 'Accept': '*/*' } });
  }

  try {
    // 1. Fetch and parse m3u8 playlist
    const m3u8Resp = await fetchUrl(m3u8Url);
    if (!m3u8Resp.ok) throw new Error(`m3u8 fetch failed: HTTP ${m3u8Resp.status}`);
    const m3u8Text = await m3u8Resp.text();
    const allLines = m3u8Text.split('\n').map(l => l.trim()).filter(l => l);
    const baseUrl = m3u8Url.substring(0, m3u8Url.lastIndexOf('/') + 1);

    // Check for master playlist → pick highest bandwidth variant
    let isMaster = false;
    let bestBandwidth = 0;
    let bestVariant = '';
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
      console.log(`${jobTag} Master playlist → variant (${bestBandwidth} bps)`);
      const varResp = await fetchUrl(bestVariant);
      if (!varResp.ok) throw new Error(`Variant fetch HTTP ${varResp.status}`);
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

    if (!segUrls.length) throw new Error('No segments found');
    console.log(`${jobTag} ${segUrls.length} segments — downloading to combined.ts`);

    // 2. Download all segments → append to combined.ts file
    const writeStream = fs.createWriteStream(combinedTs);
    let downloaded = 0;
    const BATCH = 6;

    for (let i = 0; i < segUrls.length; i += BATCH) {
      const batch = segUrls.slice(i, i + BATCH);
      const buffers = await Promise.all(batch.map(async (url) => {
        try {
          const r = await fetchUrl(url);
          if (!r.ok) { console.error(`${jobTag} Seg ${i} HTTP ${r.status}`); return Buffer.alloc(0); }
          return Buffer.from(await r.arrayBuffer());
        } catch (e) { console.error(`${jobTag} Seg fetch error: ${e.message}`); return Buffer.alloc(0); }
      }));
      for (const buf of buffers) {
        if (buf.length > 0) writeStream.write(buf);
        downloaded++;
      }
      if (downloaded % 30 === 0 || downloaded === segUrls.length) {
        console.log(`${jobTag} Downloaded ${downloaded}/${segUrls.length} segments`);
      }
    }

    await new Promise((resolve, reject) => { writeStream.end(resolve); });

    const tsSize = fs.statSync(combinedTs).size;
    console.log(`${jobTag} combined.ts = ${(tsSize / 1048576).toFixed(1)} MB — starting FFmpeg remux`);

    if (tsSize < 1000) throw new Error('combined.ts is empty — segments download failed');

    // 3. FFmpeg remux combined.ts → fragmented MP4 → stream to client
    const safeName = (title || 'video').replace(/[<>:"/\\|?*]/g, '').substring(0, 100).trim();
    res.setHeader('Content-Type', 'video/mp4');
    res.setHeader('Content-Disposition', `attachment; filename="${encodeURIComponent(safeName)}.mp4"; filename*=UTF-8''${encodeURIComponent(safeName)}.mp4`);
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Expose-Headers', 'Content-Disposition');

    const ffmpeg = spawn('ffmpeg', [
      '-y', '-i', combinedTs,
      '-c', 'copy',
      '-movflags', 'frag_keyframe+empty_moov',
      '-f', 'mp4',
      'pipe:1'
    ], { stdio: ['pipe', 'pipe', 'pipe'] });

    let stderrBuf = '';
    let bytesSent = 0;

    ffmpeg.stderr.on('data', chunk => {
      stderrBuf += chunk.toString();
      if (stderrBuf.length > 2048) stderrBuf = stderrBuf.slice(-2048);
    });

    ffmpeg.stdout.on('data', chunk => {
      bytesSent += chunk.length;
      try { res.write(chunk); } catch (e) {}
    });

    ffmpeg.on('close', code => {
      console.log(`${jobTag} FFmpeg exit code ${code} — ${(bytesSent / 1048576).toFixed(1)} MB sent`);
      if (code !== 0) console.error(`${jobTag} FFmpeg stderr: ${stderrBuf.slice(-500)}`);
      try { res.end(); } catch (e) {}
      try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (e) {}
    });

    ffmpeg.on('error', err => {
      console.error(`${jobTag} FFmpeg spawn error:`, err.message);
      if (!res.headersSent) res.status(500).json({ error: err.message });
      try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (e) {}
    });

    req.on('close', () => {
      if (!ffmpeg.killed) {
        console.log(`${jobTag} Client disconnected — killing FFmpeg`);
        ffmpeg.kill('SIGTERM');
        try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (e) {}
      }
    });

  } catch (err) {
    console.error(`${jobTag} Error:`, err.message);
    if (!res.headersSent) res.status(500).json({ error: err.message });
    try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (e) {}
  }
});

// ---------------------------------------------------------------------------
// Démarrage du serveur
// ---------------------------------------------------------------------------

app.listen(PORT, () => {
  console.log(`[SubWhisper FFmpeg Server v1.8.0] Démarré sur le port ${PORT}`);
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
