#!/usr/bin/env node
const http = require('http');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const { URL } = require('url');
const { DatabaseSync } = require('node:sqlite');

const PORT = Number(process.env.BRIDGE_PORT || 8787);
const TOKEN = process.env.BRIDGE_TOKEN || 'change-me';
const DATA_DIR = process.env.BRIDGE_DATA_DIR || path.join(__dirname, 'data');
const DB_FILE = process.env.BRIDGE_DB_FILE || path.join(DATA_DIR, 'bridge.sqlite');

fs.mkdirSync(DATA_DIR, { recursive: true });
const db = new DatabaseSync(DB_FILE);
db.exec(`
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  target TEXT NOT NULL,
  type TEXT NOT NULL,
  content TEXT,
  conversation_id TEXT,
  metadata_json TEXT,
  status TEXT NOT NULL,
  result TEXT,
  error TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_target_status ON tasks(target, status);
CREATE INDEX IF NOT EXISTS idx_tasks_source ON tasks(source);
`);

function now() {
  return new Date().toISOString();
}

function json(res, status, body) {
  const data = JSON.stringify(body, null, 2);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(data),
  });
  res.end(data);
}

function notFound(res) {
  json(res, 404, { error: 'not_found' });
}

function unauthorized(res) {
  json(res, 401, { error: 'unauthorized' });
}

function badRequest(res, message) {
  json(res, 400, { error: 'bad_request', message });
}

function getAuthToken(req) {
  const header = req.headers['authorization'] || '';
  const prefix = 'Bearer ';
  return header.startsWith(prefix) ? header.slice(prefix.length).trim() : '';
}

function requireAuth(req, res) {
  const token = getAuthToken(req);
  if (!TOKEN || token !== TOKEN) {
    unauthorized(res);
    return false;
  }
  return true;
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', chunk => {
      data += chunk;
      if (data.length > 1024 * 1024) {
        reject(new Error('body_too_large'));
        req.destroy();
      }
    });
    req.on('end', () => {
      if (!data) return resolve({});
      try {
        resolve(JSON.parse(data));
      } catch (e) {
        reject(new Error('invalid_json'));
      }
    });
    req.on('error', reject);
  });
}

function newId() {
  return 'task_' + crypto.randomBytes(8).toString('hex');
}

function rowToTask(row) {
  if (!row) return null;
  return {
    id: row.id,
    source: row.source,
    target: row.target,
    type: row.type,
    content: row.content,
    conversationId: row.conversation_id,
    metadata: row.metadata_json ? JSON.parse(row.metadata_json) : {},
    status: row.status,
    result: row.result,
    error: row.error,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

const insertStmt = db.prepare(`
INSERT INTO tasks (
  id, source, target, type, content, conversation_id, metadata_json,
  status, result, error, created_at, updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
`);

const getStmt = db.prepare(`SELECT * FROM tasks WHERE id = ?`);
const updateResultStmt = db.prepare(`
UPDATE tasks
SET status = ?, result = ?, error = ?, updated_at = ?
WHERE id = ?
`);

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const pathname = url.pathname;

  if (req.method === 'GET' && pathname === '/health') {
    return json(res, 200, { ok: true, service: 'bot-bridge-sqlite', db: DB_FILE, time: now() });
  }

  if (!requireAuth(req, res)) return;

  if (req.method === 'POST' && pathname === '/tasks') {
    try {
      const body = await readBody(req);
      if (!body.target || !body.type) {
        return badRequest(res, 'target and type are required');
      }
      const task = {
        id: newId(),
        source: body.source || 'unknown',
        target: body.target,
        type: body.type,
        content: body.content || '',
        conversationId: body.conversationId || null,
        metadata: body.metadata || {},
        status: 'pending',
        result: null,
        error: null,
        createdAt: now(),
        updatedAt: now(),
      };
      insertStmt.run(
        task.id,
        task.source,
        task.target,
        task.type,
        task.content,
        task.conversationId,
        JSON.stringify(task.metadata || {}),
        task.status,
        task.result,
        task.error,
        task.createdAt,
        task.updatedAt
      );
      return json(res, 201, task);
    } catch (e) {
      return badRequest(res, e.message);
    }
  }

  if (req.method === 'GET' && pathname === '/tasks') {
    const params = [];
    const where = [];
    if (url.searchParams.get('target')) {
      where.push('target = ?');
      params.push(url.searchParams.get('target'));
    }
    if (url.searchParams.get('source')) {
      where.push('source = ?');
      params.push(url.searchParams.get('source'));
    }
    if (url.searchParams.get('status')) {
      where.push('status = ?');
      params.push(url.searchParams.get('status'));
    }
    if (url.searchParams.get('type')) {
      where.push('type = ?');
      params.push(url.searchParams.get('type'));
    }
    const sql = `SELECT * FROM tasks ${where.length ? 'WHERE ' + where.join(' AND ') : ''} ORDER BY created_at DESC`;
    const rows = db.prepare(sql).all(...params);
    return json(res, 200, { count: rows.length, tasks: rows.map(rowToTask) });
  }

  const taskIdMatch = pathname.match(/^\/tasks\/([^/]+)$/);
  if (req.method === 'GET' && taskIdMatch) {
    const row = getStmt.get(taskIdMatch[1]);
    if (!row) return notFound(res);
    return json(res, 200, rowToTask(row));
  }

  const resultMatch = pathname.match(/^\/tasks\/([^/]+)\/result$/);
  if (req.method === 'POST' && resultMatch) {
    try {
      const body = await readBody(req);
      const existing = getStmt.get(resultMatch[1]);
      if (!existing) return notFound(res);
      const updatedAt = now();
      updateResultStmt.run(
        body.status || 'done',
        body.result ?? null,
        body.error ?? null,
        updatedAt,
        resultMatch[1]
      );
      const row = getStmt.get(resultMatch[1]);
      return json(res, 200, rowToTask(row));
    } catch (e) {
      return badRequest(res, e.message);
    }
  }

  notFound(res);
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`bot-bridge-sqlite listening on :${PORT}`);
  console.log(`db file: ${DB_FILE}`);
});
