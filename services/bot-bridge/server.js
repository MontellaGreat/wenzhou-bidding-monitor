#!/usr/bin/env node
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { URL } = require('url');

const PORT = Number(process.env.BRIDGE_PORT || 8787);
const TOKEN = process.env.BRIDGE_TOKEN || 'change-me';
const DATA_DIR = process.env.BRIDGE_DATA_DIR || path.join(__dirname, 'data');
const DATA_FILE = path.join(DATA_DIR, 'tasks.json');

fs.mkdirSync(DATA_DIR, { recursive: true });
if (!fs.existsSync(DATA_FILE)) {
  fs.writeFileSync(DATA_FILE, JSON.stringify({ tasks: [] }, null, 2));
}

function loadDb() {
  try {
    return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
  } catch (e) {
    return { tasks: [] };
  }
}

function saveDb(db) {
  fs.writeFileSync(DATA_FILE, JSON.stringify(db, null, 2));
}

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

function matchTask(task, query) {
  if (query.target && task.target !== query.target) return false;
  if (query.source && task.source !== query.source) return false;
  if (query.status && task.status !== query.status) return false;
  if (query.type && task.type !== query.type) return false;
  return true;
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const pathname = url.pathname;

  if (req.method === 'GET' && pathname === '/health') {
    return json(res, 200, { ok: true, service: 'bot-bridge', time: now() });
  }

  if (!requireAuth(req, res)) return;

  if (req.method === 'POST' && pathname === '/tasks') {
    try {
      const body = await readBody(req);
      if (!body.target || !body.type) {
        return badRequest(res, 'target and type are required');
      }
      const db = loadDb();
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
      db.tasks.push(task);
      saveDb(db);
      return json(res, 201, task);
    } catch (e) {
      return badRequest(res, e.message);
    }
  }

  if (req.method === 'GET' && pathname === '/tasks') {
    const db = loadDb();
    const tasks = db.tasks.filter(task => matchTask(task, Object.fromEntries(url.searchParams.entries())));
    return json(res, 200, { count: tasks.length, tasks });
  }

  const taskIdMatch = pathname.match(/^\/tasks\/([^/]+)$/);
  if (req.method === 'GET' && taskIdMatch) {
    const db = loadDb();
    const task = db.tasks.find(t => t.id === taskIdMatch[1]);
    if (!task) return notFound(res);
    return json(res, 200, task);
  }

  const resultMatch = pathname.match(/^\/tasks\/([^/]+)\/result$/);
  if (req.method === 'POST' && resultMatch) {
    try {
      const body = await readBody(req);
      const db = loadDb();
      const task = db.tasks.find(t => t.id === resultMatch[1]);
      if (!task) return notFound(res);
      task.status = body.status || 'done';
      task.result = body.result ?? null;
      task.error = body.error ?? null;
      task.updatedAt = now();
      saveDb(db);
      return json(res, 200, task);
    } catch (e) {
      return badRequest(res, e.message);
    }
  }

  notFound(res);
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`bot-bridge listening on :${PORT}`);
  console.log(`data file: ${DATA_FILE}`);
});
