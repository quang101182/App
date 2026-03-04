/**
 * SubWhisper Fly.io FFmpeg Server
 * Version: 1.0.0
 *
 * Rôle: reçoit un job depuis le Cloudflare Worker, télécharge la vidéo
 * via FFmpeg (streaming), extrait l'audio en WAV 16kHz mono, découpe en
 * chunks ≤24MB, transcrit chaque chunk via Groq Whisper, assemble le SRT
 * complet et notifie le Worker via callback PATCH.
 */

'use strict';

const express = require('express');
const { spawn } = require('child_process');
const FormData = require('form-data');
// Note: jobId is provided by the Cloudflare Worker, no local UUID generation needed

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
// chunkBytes doit être aligné sur 2 octets (frameSize)
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
app.use(express.json({ limit: '1mb' }));

// ---------------------------------------------------------------------------
// Middleware auth
// ---------------------------------------------------------------------------

function requireFlySecret(req, res, next) {
  if (!FLY_SECRET) {
    // Si pas de secret configuré, on laisse passer (dev local)
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
    version: '1.0.0'
  });
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
    groqKey
  } = req.body || {};

  // Validation des champs obligatoires
  if (!jobId || !presignedDownload || !workerCallbackUrl || !workerSecret || !groqKey) {
    return res.status(400).json({
      error: 'Champs obligatoires manquants: jobId, presignedDownload, workerCallbackUrl, workerSecret, groqKey'
    });
  }

  // Throttling: max jobs simultanés
  if (activeJobs >= MAX_CONCURRENT_JOBS) {
    return res.status(503).json({
      error: 'Trop de jobs en cours',
      activeJobs,
      maxConcurrentJobs: MAX_CONCURRENT_JOBS
    });
  }

  // Répondre immédiatement puis traiter en async
  res.json({ accepted: true, jobId });

  // Lancer le pipeline en arrière-plan
  activeJobs++;
  const JOB_TIMEOUT_MS = 50 * 60 * 1000; // 50 min max par job
  const jobTimeout = new Promise((_, reject) =>
    setTimeout(() => reject(new Error('Job timeout 50min dépassé')), JOB_TIMEOUT_MS)
  );
  Promise.race([
    processJob({ jobId, presignedDownload, srcLang, workerCallbackUrl, workerSecret, groqKey }),
    jobTimeout
  ])
    .catch(async err => {
      console.error(`[${jobId}] Erreur pipeline:`, err.message);
      // Notifier le Worker de l'échec pour sortir l'app du polling immédiatement
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
  const { jobId, presignedDownload, srcLang, workerCallbackUrl, workerSecret, groqKey } = job;

  console.log(`[${jobId}] Démarrage du pipeline. URL: ${presignedDownload.substring(0, 80)}...`);

  try {
    // 1. Notification de démarrage
    await updateWorker(workerCallbackUrl, workerSecret, {
      jobId,
      progress: 5,
      log: 'Démarrage extraction audio via FFmpeg...',
      status: 'processing'
    });

    // 2. Lancer FFmpeg en streaming
    //    ffmpeg lit la vidéo depuis l'URL presignée et écrit WAV 16kHz mono sur stdout
    const ffmpegArgs = [
      '-i', presignedDownload,
      '-vn',                    // ignorer la piste vidéo
      '-acodec', 'pcm_s16le',  // PCM 16-bit little-endian
      '-ar', '16000',           // 16 kHz
      '-ac', '1',               // mono
      '-f', 'wav',              // format WAV
      'pipe:1'                  // écrire sur stdout
    ];

    console.log(`[${jobId}] Commande FFmpeg: ffmpeg ${ffmpegArgs.join(' ')}`);

    await updateWorker(workerCallbackUrl, workerSecret, {
      jobId,
      progress: 10,
      log: 'FFmpeg démarré, extraction en cours...',
      status: 'processing'
    });

    // 3. Découper le WAV en chunks et transcrire
    const allSegments = await streamAndTranscribe({
      jobId,
      ffmpegArgs,
      srcLang,
      groqKey,
      workerCallbackUrl,
      workerSecret
    });

    // 4. Assembler le SRT final
    await updateWorker(workerCallbackUrl, workerSecret, {
      jobId,
      progress: 95,
      log: `Assemblage du SRT (${allSegments.length} segments)...`,
      status: 'processing'
    });

    const srt = assembleSrt(allSegments);
    console.log(`[${jobId}] SRT assemblé: ${srt.length} caractères, ${allSegments.length} segments`);

    // 5. Callback "done" vers le Worker
    await updateWorker(workerCallbackUrl, workerSecret, {
      jobId,
      progress: 100,
      log: 'Transcription terminée.',
      status: 'done',
      srt
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
// Streaming FFmpeg + découpe en chunks + transcription Groq
// ---------------------------------------------------------------------------

async function streamAndTranscribe({ jobId, ffmpegArgs, srcLang, groqKey, workerCallbackUrl, workerSecret }) {
  return new Promise((resolve, reject) => {
    const ffmpeg = spawn('ffmpeg', ffmpegArgs, {
      stdio: ['ignore', 'pipe', 'pipe']
    });

    let ffmpegStderr = '';
    let ffmpegExitCode = null;
    let promiseResolved = false;

    ffmpeg.stderr.on('data', (d) => {
      ffmpegStderr += d.toString();
    });

    // Buffers pour gérer le streaming WAV
    let headerBuffer = null;       // 44 bytes du header WAV
    let headerParsed = false;
    let headerAccum = Buffer.alloc(0);

    let pcmAccum = Buffer.alloc(0); // buffer PCM courant (sans header)
    let chunkIndex = 0;

    // Résultats de tous les chunks (promises accumulées)
    const chunkPromises = [];

    // Throttling Groq
    let lastGroqCallTime = 0;

    // Fonction pour envoyer un chunk PCM accumulé à Groq
    async function flushChunk(pcmData, chunkIdx) {
      // Construire le WAV complet: header + PCM
      const wavBuffer = buildWavBuffer(pcmData);

      // Throttling: attendre si dernier appel Groq < 4s
      const now = Date.now();
      const elapsed = now - lastGroqCallTime;
      if (elapsed < GROQ_MIN_INTERVAL_MS && lastGroqCallTime > 0) {
        const wait = GROQ_MIN_INTERVAL_MS - elapsed;
        console.log(`[${jobId}] Chunk ${chunkIdx}: throttling Groq, attente ${wait}ms...`);
        await sleep(wait);
      }

      lastGroqCallTime = Date.now();

      // Calculer l'offset temporel de ce chunk
      const offsetSec = chunkIdx * CHUNK_DUR_SEC;

      // Mettre à jour la progression
      const progress = Math.min(85, 20 + chunkIdx * 15);
      await updateWorker(workerCallbackUrl, workerSecret, {
        jobId,
        progress,
        log: `Transcription chunk ${chunkIdx + 1} (offset ${offsetSec.toFixed(1)}s)...`,
        status: 'processing'
      }).catch(() => {}); // non-bloquant

      // Envoyer à Groq avec retry x3
      const segments = await transcribeWithGroq({
        jobId,
        wavBuffer,
        chunkIdx,
        srcLang,
        groqKey,
        offsetSec
      });

      return segments;
    }

    // Traiter les données stdout de FFmpeg (WAV stream)
    // IMPORTANT: handler synchrone — on pousse les promises sans await pour éviter
    // les race conditions avec l'event loop des Readable streams Node.js.
    ffmpeg.stdout.on('data', (chunk) => {
      // Phase 1: accumuler le header WAV (44 bytes)
      if (!headerParsed) {
        headerAccum = Buffer.concat([headerAccum, chunk]);
        if (headerAccum.length >= 44) {
          headerBuffer = headerAccum.slice(0, 44);
          headerParsed = true;
          // Le reste après le header: c'est du PCM
          const remaining = headerAccum.slice(44);
          if (remaining.length > 0) {
            pcmAccum = Buffer.concat([pcmAccum, remaining]);
          }
          console.log(`[${jobId}] Header WAV parsé. Sample rate: ${headerBuffer.readUInt32LE(24)} Hz, Channels: ${headerBuffer.readUInt16LE(22)}`);
        }
        return;
      }

      // Phase 2: accumuler le PCM et découper en chunks complets
      pcmAccum = Buffer.concat([pcmAccum, chunk]);

      // Dès qu'on a assez pour un chunk complet, créer la promise (sans await)
      // Les promises seront résolues séquentiellement dans 'end'
      while (pcmAccum.length >= CHUNK_MAX_BYTES) {
        const pcmChunk = pcmAccum.slice(0, CHUNK_MAX_BYTES);
        pcmAccum = pcmAccum.slice(CHUNK_MAX_BYTES);
        const idx = chunkIndex++;
        console.log(`[${jobId}] Chunk ${idx}: ${pcmChunk.length} bytes PCM → WAV ${(pcmChunk.length / 1024 / 1024).toFixed(1)} MB`);
        // Lancer la promise mais ne pas l'await ici (handler synchrone)
        chunkPromises.push({ idx, promise: flushChunk(pcmChunk, idx) });
      }
    });

    ffmpeg.stdout.on('end', async () => {
      console.log(`[${jobId}] FFmpeg stdout terminé. PCM restant: ${pcmAccum.length} bytes`);

      // Vérifier si FFmpeg a échoué sans produire de données WAV valides
      if (!headerParsed && chunkPromises.length === 0) {
        const errMsg = `FFmpeg n'a produit aucun audio WAV valide. Stderr: ${ffmpegStderr.slice(-500)}`;
        console.error(`[${jobId}] ${errMsg}`);
        promiseResolved = true;
        return reject(new Error(errMsg));
      }

      // Flusher le dernier chunk PCM s'il y en a un
      if (pcmAccum.length > 0 && headerParsed) {
        const idx = chunkIndex++;
        console.log(`[${jobId}] Dernier chunk ${idx}: ${pcmAccum.length} bytes PCM`);
        chunkPromises.push({ idx, promise: flushChunk(pcmAccum, idx) });
      }

      // Attendre tous les chunks dans l'ordre (séquentiellement pour le throttling Groq)
      try {
        const allSegments = [];
        for (const { idx, promise } of chunkPromises) {
          const segments = await promise;
          console.log(`[${jobId}] Chunk ${idx} transcrit: ${segments.length} segments`);
          allSegments.push(...segments);
        }
        promiseResolved = true;
        resolve(allSegments);
      } catch (err) {
        promiseResolved = true;
        reject(err);
      }
    });

    ffmpeg.on('error', (err) => {
      console.error(`[${jobId}] Erreur spawn FFmpeg:`, err);
      if (!promiseResolved) {
        promiseResolved = true;
        reject(new Error(`FFmpeg spawn error: ${err.message}`));
      }
    });

    ffmpeg.on('close', (code) => {
      ffmpegExitCode = code;
      if (code !== 0) {
        console.error(`[${jobId}] FFmpeg exited with code ${code}`);
        console.error(`[${jobId}] FFmpeg stderr:\n${ffmpegStderr.slice(-2000)}`);
        // Si la promise n'a pas encore été résolue (cas: stdout vide + code != 0)
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
// Transcription Groq avec retry x3
// ---------------------------------------------------------------------------

async function transcribeWithGroq({ jobId, wavBuffer, chunkIdx, srcLang, groqKey, offsetSec }) {
  const MAX_RETRIES = 3;
  let lastError;

  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      console.log(`[${jobId}] Chunk ${chunkIdx}: appel Groq (tentative ${attempt}/${MAX_RETRIES})...`);

      const form = new FormData();
      form.append('file', wavBuffer, {
        filename: `chunk_${chunkIdx}.wav`,
        contentType: 'audio/wav'
      });
      form.append('model', GROQ_MODEL);
      form.append('response_format', 'verbose_json');
      form.append('timestamp_granularities[]', 'segment');
      if (srcLang && srcLang.trim()) {
        form.append('language', srcLang.trim());
      }

      const response = await fetch(GROQ_ENDPOINT, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${groqKey}`,
          ...form.getHeaders()
        },
        body: form
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`Groq HTTP ${response.status}: ${errText.substring(0, 300)}`);
      }

      const data = await response.json();

      if (!data.segments || !Array.isArray(data.segments)) {
        console.warn(`[${jobId}] Chunk ${chunkIdx}: pas de segments dans la réponse Groq`);
        return [];
      }

      // Appliquer l'offset temporel à chaque segment
      const segments = data.segments.map(seg => ({
        start: (seg.start || 0) + offsetSec,
        end: (seg.end || 0) + offsetSec,
        text: (seg.text || '').trim()
      })).filter(seg => seg.text.length > 0);

      console.log(`[${jobId}] Chunk ${chunkIdx}: ${segments.length} segments reçus de Groq (offset=${offsetSec.toFixed(1)}s)`);
      return segments;

    } catch (err) {
      lastError = err;
      console.error(`[${jobId}] Chunk ${chunkIdx}: tentative ${attempt} échouée:`, err.message);

      if (attempt < MAX_RETRIES) {
        const backoff = attempt * 5000; // 5s, 10s
        console.log(`[${jobId}] Chunk ${chunkIdx}: retry dans ${backoff}ms...`);
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
  const byteRate = sampleRate * numChannels * (bitsPerSample / 8); // 32000
  const blockAlign = numChannels * (bitsPerSample / 8);           // 2
  const dataSize = pcmData.length;
  const chunkSize = 36 + dataSize;

  const header = Buffer.alloc(44);

  // RIFF header
  header.write('RIFF', 0, 'ascii');
  header.writeUInt32LE(chunkSize, 4);
  header.write('WAVE', 8, 'ascii');

  // fmt chunk
  header.write('fmt ', 12, 'ascii');
  header.writeUInt32LE(16, 16);           // subchunk1Size (PCM = 16)
  header.writeUInt16LE(1, 20);            // audioFormat (PCM = 1)
  header.writeUInt16LE(numChannels, 22);  // numChannels
  header.writeUInt32LE(sampleRate, 24);   // sampleRate
  header.writeUInt32LE(byteRate, 28);     // byteRate
  header.writeUInt16LE(blockAlign, 32);   // blockAlign
  header.writeUInt16LE(bitsPerSample, 34); // bitsPerSample

  // data chunk
  header.write('data', 36, 'ascii');
  header.writeUInt32LE(dataSize, 40);

  return Buffer.concat([header, pcmData]);
}

// ---------------------------------------------------------------------------
// Assemblage SRT depuis les segments (avec offsets déjà appliqués)
// ---------------------------------------------------------------------------

function assembleSrt(segments) {
  if (!segments || segments.length === 0) {
    return '';
  }

  const lines = [];
  let blockNum = 1;

  for (const seg of segments) {
    const text = (seg.text || '').trim();
    if (!text) continue;

    const startStr = secToSrtTime(seg.start);
    const endStr = secToSrtTime(seg.end);

    lines.push(String(blockNum));
    lines.push(`${startStr} --> ${endStr}`);
    lines.push(text);
    lines.push(''); // ligne vide entre blocs

    blockNum++;
  }

  return lines.join('\n');
}

// Convertit des secondes en format SRT: HH:MM:SS,mmm
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
      // Timeout 10s pour les callbacks de progression
      signal: AbortSignal.timeout(10000)
    });

    if (!response.ok) {
      const errText = await response.text().catch(() => '');
      console.warn(`[updateWorker] Callback HTTP ${response.status} vers ${url}: ${errText.substring(0, 200)}`);
    }
  } catch (err) {
    // Non-bloquant: on logue mais on ne lance pas d'erreur
    console.warn(`[updateWorker] Erreur callback vers ${url}:`, err.message);
  }
}

// ---------------------------------------------------------------------------
// Utilitaires
// ---------------------------------------------------------------------------

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ---------------------------------------------------------------------------
// Démarrage du serveur
// ---------------------------------------------------------------------------

app.listen(PORT, () => {
  console.log(`[SubWhisper FFmpeg Server v1.0.0] Démarré sur le port ${PORT}`);
  console.log(`  MAX_CONCURRENT_JOBS = ${MAX_CONCURRENT_JOBS}`);
  console.log(`  FLY_SECRET configuré: ${FLY_SECRET ? 'OUI' : 'NON (mode dev)'}`);
  console.log(`  CHUNK_MAX_BYTES = ${CHUNK_MAX_BYTES} bytes (${(CHUNK_MAX_BYTES / 1024 / 1024).toFixed(1)} MB PCM)`);
  console.log(`  CHUNK_DUR_SEC = ${CHUNK_DUR_SEC.toFixed(1)} secondes`);
  console.log(`  GROQ_MODEL = ${GROQ_MODEL}`);
});

// Gestion propre des signaux POSIX (Fly.io envoie SIGTERM avant de tuer)
process.on('SIGTERM', () => {
  console.log('[SIGTERM] Arrêt demandé. Jobs actifs restants:', activeJobs);
  // Pas de graceful drain pour l'instant — les jobs en cours seront perdus
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('[SIGINT] Arrêt. Jobs actifs restants:', activeJobs);
  process.exit(0);
});
