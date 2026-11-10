#!/usr/bin/env node
/**
 * apply_agent.js - local HTTP server that runs Playwright apply scripts.
 * hunt.lan (Docker) calls http://127.0.0.1:2346/apply with a JSON body.
 * Runs on the HOST so it can access Chromium and resume files.
 */
const http = require('http');
const { execFile } = require('child_process');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PORT = 2346;
const SCRIPT_DIR = '/opt/jobhunt/playwright';
const CONFIG_DIR = '/tmp/apply_configs';
fs.mkdirSync(CONFIG_DIR, { recursive: true });

const server = http.createServer((req, res) => {
  if (req.method === 'POST' && req.url === '/apply') {
    let body = '';
    req.on('data', d => body += d);
    req.on('end', () => {
      let cfg;
      try { cfg = JSON.parse(body); } catch (e) {
        res.writeHead(400);
        return res.end(JSON.stringify({ error: 'Invalid JSON' }));
      }

      // Determine which script to use
      const ats = cfg.ats || 'greenhouse';
      const script = path.join(SCRIPT_DIR, `${ats}.js`);
      if (!fs.existsSync(script)) {
        res.writeHead(404);
        return res.end(JSON.stringify({ error: `No script for ATS: ${ats}` }));
      }

      // Write config to temp file
      const cfgFile = path.join(CONFIG_DIR, `${Date.now()}_${crypto.randomBytes(4).toString('hex')}.json`);
      fs.writeFileSync(cfgFile, JSON.stringify(cfg));

      console.log(`[apply_agent] Running ${ats} for job ${cfg.token || cfg.job_id}`);
      execFile('node', [script, cfgFile], { cwd: SCRIPT_DIR, timeout: 180000 }, (err, stdout, stderr) => {
        fs.unlinkSync(cfgFile);
        if (stderr) console.error('[apply_agent stderr]', stderr.slice(0, 500));

        let result;
        try { result = JSON.parse(stdout); } catch { result = { success: false, raw: stdout }; }

        if (err && !result.success) {
          result = { success: false, error: err.message, raw: stdout };
        }

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(result));
      });
    });
  } else if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200);
    res.end(JSON.stringify({ ok: true }));
  } else {
    res.writeHead(404);
    res.end('not found');
  }
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`apply_agent listening on 127.0.0.1:${PORT}`);
});
