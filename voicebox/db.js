// VoiceBox DB v0.2.0 — SQLite wrapper
// Synchronous SQLite database layer using better-sqlite3

const Database = require('better-sqlite3');
const path = require('path');

// ---------------------------------------------------------------------------
// Database initialization
// ---------------------------------------------------------------------------

const fs = require('fs');
const DEFAULT_DB = fs.existsSync('/data') ? '/data/bot.db' : path.resolve(__dirname, 'bot.db');
const DB_PATH = process.env.DB_PATH || DEFAULT_DB;
const db = new Database(DB_PATH);

// Enable WAL mode for better concurrent read performance
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

// ---------------------------------------------------------------------------
// Schema — auto-created on import
// ---------------------------------------------------------------------------

db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    plan TEXT DEFAULT 'free',
    daily_count INTEGER DEFAULT 0,
    last_reset TEXT,
    last_request_at TEXT,
    lang TEXT DEFAULT '',
    banned INTEGER DEFAULT 0,
    lemon_customer_id TEXT,
    lemon_subscription_id TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
  );

  CREATE TABLE IF NOT EXISTS usage_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER,
    timestamp TEXT DEFAULT (datetime('now')),
    duration_sec INTEGER,
    type TEXT,
    status TEXT,
    FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
  );
`);

// ---------------------------------------------------------------------------
// Migrations — add columns if missing (safe for existing DBs)
// ---------------------------------------------------------------------------

try {
  db.exec("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT ''");
} catch (e) {
  // Column already exists — ignore
}

// ---------------------------------------------------------------------------
// Prepared statements (cached for performance)
// ---------------------------------------------------------------------------

const stmts = {
  getUser: db.prepare('SELECT * FROM users WHERE telegram_id = ?'),

  insertUser: db.prepare(`
    INSERT INTO users (telegram_id, username, first_name, created_at, updated_at)
    VALUES (?, ?, ?, datetime('now'), datetime('now'))
    ON CONFLICT(telegram_id) DO UPDATE SET
      username = excluded.username,
      first_name = excluded.first_name,
      updated_at = datetime('now')
  `),

  resetDaily: db.prepare(`
    UPDATE users SET daily_count = 0, last_reset = ? WHERE telegram_id = ?
  `),

  incrementUsage: db.prepare(`
    UPDATE users
    SET daily_count = daily_count + 1,
        last_request_at = datetime('now'),
        updated_at = datetime('now')
    WHERE telegram_id = ?
  `),

  logUsage: db.prepare(`
    INSERT INTO usage_logs (telegram_id, duration_sec, type, status)
    VALUES (?, ?, ?, ?)
  `),

  setPlan: db.prepare(`
    UPDATE users
    SET plan = ?,
        lemon_customer_id = ?,
        lemon_subscription_id = ?,
        updated_at = datetime('now')
    WHERE telegram_id = ?
  `),

  setLang: db.prepare(`
    UPDATE users SET lang = ?, updated_at = datetime('now') WHERE telegram_id = ?
  `),

  // Stats queries
  totalUsers: db.prepare('SELECT COUNT(*) AS count FROM users'),
  proUsers: db.prepare("SELECT COUNT(*) AS count FROM users WHERE plan = 'pro'"),
  todayTranscriptions: db.prepare(
    "SELECT COUNT(*) AS count FROM usage_logs WHERE date(timestamp) = date('now')"
  ),
  totalTranscriptions: db.prepare('SELECT COUNT(*) AS count FROM usage_logs'),
};

// ---------------------------------------------------------------------------
// Plan limits
// ---------------------------------------------------------------------------

const PLAN_LIMITS = {
  free: { daily: 5, cooldownSec: 10 },
  pro:  { daily: 999999, cooldownSec: 5 },
};

/** Get today's date in UTC as YYYY-MM-DD */
function todayUTC() {
  return new Date().toISOString().slice(0, 10);
}

// ---------------------------------------------------------------------------
// Exported functions
// ---------------------------------------------------------------------------

/**
 * Upsert a user — creates if new, updates username/first_name if existing.
 * Preserves plan, lemon fields, daily_count, and banned status.
 */
function upsertUser(telegramId, username, firstName) {
  stmts.insertUser.run(telegramId, username || null, firstName || null);
}

/**
 * Get a user row by Telegram ID, or null if not found.
 */
function getUser(telegramId) {
  return stmts.getUser.get(telegramId) || null;
}

/**
 * Check if user has remaining daily quota.
 * Resets daily_count if last_reset is not today (UTC).
 * Banned users are always denied.
 *
 * @returns {{ allowed: boolean, remaining: number, plan: string, dailyCount: number, limit: number }}
 */
function checkQuota(telegramId) {
  const user = stmts.getUser.get(telegramId);

  // Unknown user — should not happen if upsertUser is called first
  if (!user) {
    return { allowed: false, remaining: 0, plan: 'free', dailyCount: 0, limit: 0 };
  }

  // Banned users are always blocked
  if (user.banned) {
    return { allowed: false, remaining: 0, plan: user.plan, dailyCount: user.daily_count, limit: 0 };
  }

  const today = todayUTC();
  const limits = PLAN_LIMITS[user.plan] || PLAN_LIMITS.free;

  // Reset counter if new day
  if (user.last_reset !== today) {
    stmts.resetDaily.run(today, telegramId);
    user.daily_count = 0;
  }

  const remaining = Math.max(0, limits.daily - user.daily_count);

  return {
    allowed: remaining > 0,
    remaining,
    plan: user.plan,
    dailyCount: user.daily_count,
    limit: limits.daily,
  };
}

/**
 * Check rate-limit cooldown between requests.
 * free: 10 s cooldown, pro: 5 s cooldown.
 *
 * @returns {{ allowed: boolean, waitSeconds: number }}
 */
function checkRateLimit(telegramId) {
  const user = stmts.getUser.get(telegramId);

  if (!user || !user.last_request_at) {
    return { allowed: true, waitSeconds: 0 };
  }

  const limits = PLAN_LIMITS[user.plan] || PLAN_LIMITS.free;
  const lastReq = new Date(user.last_request_at + 'Z'); // stored as UTC without Z
  const nowMs = Date.now();
  const elapsedSec = (nowMs - lastReq.getTime()) / 1000;
  const waitSeconds = Math.max(0, Math.ceil(limits.cooldownSec - elapsedSec));

  return {
    allowed: waitSeconds <= 0,
    waitSeconds,
  };
}

/**
 * Increment daily usage counter and update last_request_at.
 */
function incrementUsage(telegramId) {
  // Ensure daily counter is reset if needed
  const today = todayUTC();
  const user = stmts.getUser.get(telegramId);
  if (user && user.last_reset !== today) {
    stmts.resetDaily.run(today, telegramId);
  }

  stmts.incrementUsage.run(telegramId);
}

/**
 * Log a transcription/usage event.
 */
function logUsage(telegramId, durationSec, type, status) {
  stmts.logUsage.run(telegramId, durationSec || 0, type || 'unknown', status || 'ok');
}

/**
 * Update a user's plan and LemonSqueezy billing info.
 */
function setPlan(telegramId, plan, lemonCustomerId, lemonSubscriptionId) {
  stmts.setPlan.run(
    plan || 'free',
    lemonCustomerId || null,
    lemonSubscriptionId || null,
    telegramId
  );
}

/**
 * Set user's preferred translation language.
 */
function setLang(telegramId, lang) {
  stmts.setLang.run(lang || '', telegramId);
}

/**
 * Get user's preferred translation language.
 */
function getLang(telegramId) {
  const user = stmts.getUser.get(telegramId);
  return user ? (user.lang || '') : '';
}

/**
 * Get global stats for admin dashboard.
 *
 * @returns {{ totalUsers: number, proUsers: number, todayTranscriptions: number, totalTranscriptions: number }}
 */
function getStats() {
  return {
    totalUsers: stmts.totalUsers.get().count,
    proUsers: stmts.proUsers.get().count,
    todayTranscriptions: stmts.todayTranscriptions.get().count,
    totalTranscriptions: stmts.totalTranscriptions.get().count,
  };
}

// ---------------------------------------------------------------------------
// Exports
// ---------------------------------------------------------------------------

module.exports = {
  db,            // raw db instance (for advanced queries or graceful shutdown)
  upsertUser,
  getUser,
  checkQuota,
  checkRateLimit,
  incrementUsage,
  logUsage,
  setPlan,
  setLang,
  getLang,
  getStats,
};
