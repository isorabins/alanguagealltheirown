#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_MATRIX = JSON.parse(fs.readFileSync(path.join(HERE, 'matrix.json'), 'utf8'));
const MAX_WAIT_MS = 10_000;
const MAX_RECEIPT_BYTES = 65_536;

function fail(message) { throw new Error(message); }
function readJson(file) { return JSON.parse(fs.readFileSync(file, 'utf8')); }
function sha256(file) { return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'); }
function safeName(name) {
  if (!/^[0-9A-Za-z][0-9A-Za-z._-]*$/.test(name) || name.includes('..')) fail(`unsafe evidence filename: ${name}`);
  return name;
}
function parseArgs(argv) {
  const out = { headless: false, overwrite: false };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--plan') out.plan = argv[++i];
    else if (arg === '--output') out.output = argv[++i];
    else if (arg === '--browser') out.browser = argv[++i];
    else if (arg === '--headless') out.headless = true;
    else if (arg === '--overwrite') out.overwrite = true;
    else fail(`unknown argument: ${arg}`);
  }
  if (!out.plan) fail('--plan is required');
  return out;
}

export function validatePlan(plan) {
  if (plan.schemaVersion !== 1) fail('plan schemaVersion must be 1');
  if (!['fixture', 'production'].includes(plan.target)) fail('target must be fixture or production');
  if (!Array.isArray(plan.rows) || !plan.rows.length) fail('plan rows are required');
  if (plan.target === 'production') {
    if (!plan.approvalReceipt || !path.isAbsolute(plan.approvalReceipt)) fail('production plan requires an absolute approvalReceipt path');
    if (!fs.existsSync(plan.approvalReceipt)) fail('production approvalReceipt is missing');
    if (plan.fixtureRoot) fail('production plan cannot use fixtureRoot');
    let productionUrl;
    try { productionUrl = new URL(plan.baseUrl); } catch { fail('production plan requires an absolute HTTPS baseUrl'); }
    if (productionUrl.protocol !== 'https:' || ['127.0.0.1', 'localhost'].includes(productionUrl.hostname)) fail('production plan requires a non-loopback HTTPS baseUrl');
    if (!Number.isInteger(plan.visibleDwellMs) || plan.visibleDwellMs < 500 || plan.visibleDwellMs > 5000) fail('production visibleDwellMs must be 500-5000');
    const ids = plan.rows.map(row => row.id);
    if (JSON.stringify(ids) !== JSON.stringify(PROJECT_MATRIX.rows.map(row => row.id))) fail('production plan must cover rows 1-26 in order');
  }
  if (plan.finalDwellMs !== undefined && (!Number.isInteger(plan.finalDwellMs) || plan.finalDwellMs < 0 || plan.finalDwellMs > 10_000)) fail('finalDwellMs must be 0-10000');
  const filenames = new Set();
  for (const row of plan.rows) {
    if (!Number.isInteger(row.id) || row.id < 1) fail('every row needs a positive integer id');
    if (!Array.isArray(row.actions) || !Array.isArray(row.assertions)) fail(`row ${row.id} needs actions and assertions arrays`);
    for (const shot of row.screenshots || []) {
      safeName(shot);
      if (filenames.has(shot)) fail(`duplicate screenshot name: ${shot}`);
      filenames.add(shot);
    }
  }
  if (plan.target === 'production') {
    const expected = PROJECT_MATRIX.rows.flatMap(row => row.screenshots).sort();
    const actual = [...filenames].sort();
    if (JSON.stringify(actual) !== JSON.stringify(expected)) fail('production screenshot names do not match the canonical 26-row matrix');
  }
  return true;
}

function fixtureServer(root) {
  const resolvedRoot = path.resolve(root);
  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      const requestPath = new URL(req.url, 'http://fixture.invalid').pathname;
      const relative = requestPath === '/' ? 'index.html' : requestPath.slice(1);
      const file = path.resolve(resolvedRoot, relative);
      if (!file.startsWith(`${resolvedRoot}${path.sep}`) || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
        res.writeHead(404, {'content-type': 'text/plain'}); res.end('not found'); return;
      }
      const type = file.endsWith('.html') ? 'text/html; charset=utf-8' : 'application/octet-stream';
      res.writeHead(200, {'content-type': type, 'cache-control': 'no-store'});
      fs.createReadStream(file).pipe(res);
    });
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => resolve({server, baseUrl: `http://127.0.0.1:${server.address().port}`}));
  });
}

async function getReceipt(url, baseUrl, outputFile) {
  const target = new URL(url, baseUrl);
  const base = new URL(baseUrl);
  if (target.origin !== base.origin) fail(`receipt URL leaves the tested origin: ${target.origin}`);
  const response = await fetch(target, {method: 'GET', redirect: 'error'});
  const bytes = Buffer.from(await response.arrayBuffer());
  if (bytes.length > MAX_RECEIPT_BYTES) fail(`receipt exceeds ${MAX_RECEIPT_BYTES} bytes`);
  const record = {url: target.href, status: response.status, bytes: bytes.length, sha256: crypto.createHash('sha256').update(bytes).digest('hex')};
  fs.writeFileSync(outputFile, `${JSON.stringify(record, null, 2)}\n`, {mode: 0o600});
  return record;
}

async function perform(page, action, context) {
  const timeout = Math.min(action.timeoutMs || 5000, MAX_WAIT_MS);
  await page.bringToFront();
  switch (action.type) {
    case 'goto': await page.goto(new URL(action.path || '/', context.baseUrl).href, {waitUntil: 'domcontentloaded', timeout}); break;
    case 'click': await page.locator(action.selector).click({timeout}); break;
    case 'fill': await page.locator(action.selector).fill(String(action.value ?? ''), {timeout}); break;
    case 'press': await page.locator(action.selector || 'body').press(action.key, {timeout}); break;
    case 'reload': await page.reload({waitUntil: 'domcontentloaded', timeout}); break;
    case 'waitFor': await page.locator(action.selector).waitFor({state: action.state || 'visible', timeout}); break;
    case 'wait': {
      const ms = Number(action.ms);
      if (!Number.isFinite(ms) || ms < 0 || ms > MAX_WAIT_MS) fail(`wait must be 0-${MAX_WAIT_MS}ms`);
      await page.waitForTimeout(ms); break;
    }
    case 'viewport': await page.setViewportSize({width: action.width, height: action.height}); break;
    case 'screenshot': {
      const file = path.join(context.output, safeName(action.file));
      await page.screenshot({path: file, fullPage: action.fullPage !== false});
      context.screenshots.add(action.file);
      if (context.visibleDwellMs) {
        await page.waitForTimeout(context.visibleDwellMs);
        context.browserVisibleMs += context.visibleDwellMs;
      }
      break;
    }
    case 'receiptHttp': {
      const file = path.join(context.output, safeName(action.file));
      const receipt = await getReceipt(action.path || '/', context.baseUrl, file);
      context.receipts.push({file: action.file, ...receipt}); break;
    }
    case 'restartBrowser': context.restartRequested = true; break;
    default: fail(`unsupported action type: ${action.type}`);
  }
}

async function assertState(page, assertion) {
  const locator = assertion.selector ? page.locator(assertion.selector) : null;
  switch (assertion.type) {
    case 'visible': if (!(await locator.isVisible())) fail(`${assertion.selector} is not visible`); break;
    case 'hidden': if (await locator.isVisible()) fail(`${assertion.selector} is visible`); break;
    case 'textContains': if (!(await locator.textContent())?.includes(assertion.value)) fail(`${assertion.selector} lacks expected text`); break;
    case 'textEquals': if ((await locator.textContent())?.trim() !== assertion.value) fail(`${assertion.selector} text differs`); break;
    case 'count': if (await locator.count() !== assertion.value) fail(`${assertion.selector} count differs`); break;
    case 'urlContains': if (!page.url().includes(assertion.value)) fail(`URL lacks ${assertion.value}`); break;
    default: fail(`unsupported assertion type: ${assertion.type}`);
  }
}

async function main() {
  const startedAt = new Date();
  const args = parseArgs(process.argv.slice(2));
  const planFile = path.resolve(args.plan);
  const plan = readJson(planFile);
  validatePlan(plan);
  const output = path.resolve(args.output || path.join(HERE, '.evidence', plan.runId || 'run'));
  if (fs.existsSync(output) && fs.lstatSync(output).isSymbolicLink()) fail('evidence output cannot be a symlink');
  if (fs.existsSync(output) && fs.readdirSync(output).length && !args.overwrite) fail('evidence output exists and is not empty');
  fs.mkdirSync(output, {recursive: true, mode: 0o700});

  let fixture;
  let baseUrl = plan.baseUrl;
  if (plan.fixtureRoot) {
    fixture = await fixtureServer(path.resolve(path.dirname(planFile), plan.fixtureRoot));
    baseUrl = fixture.baseUrl;
  }
  if (!baseUrl) fail('plan requires baseUrl or fixtureRoot');
  const base = new URL(baseUrl);
  if (plan.target === 'fixture' && !['127.0.0.1', 'localhost'].includes(base.hostname)) fail('fixture target must stay on loopback');

  const executablePath = args.browser || plan.browserExecutable || process.env.BROWSER || process.env.CHROME_BIN;
  if (!executablePath || !path.isAbsolute(executablePath) || !fs.existsSync(executablePath)) fail('an existing absolute browser executable is required');
  const results = [];
  const state = {output, baseUrl, screenshots: new Set(), receipts: [], restartRequested: false, visibleDwellMs: plan.visibleDwellMs || 0, browserVisibleMs: 0};
  let browser;
  let page;
  let restarts = 0;
  const launch = async () => {
    const headless = args.headless || plan.headless === true;
    const browserArgs = ['--no-first-run', '--no-default-browser-check'];
    if (!headless) browserArgs.push('--start-maximized', '--window-position=0,0');
    browser = await chromium.launch({headless, executablePath, args: browserArgs});
    const context = await browser.newContext({viewport: plan.viewport || {width: 1440, height: 1000}});
    page = await context.newPage();
    await page.bringToFront();
  };
  await launch();
  try {
    for (const row of plan.rows) {
      const result = {id: row.id, name: row.name, result: 'PASS', error: null};
      try {
        for (const action of row.actions) {
          await perform(page, action, state);
          if (state.restartRequested) {
            const reopen = page.url();
            state.restartRequested = false;
            await browser.close();
            await launch();
            await page.goto(reopen, {waitUntil: 'domcontentloaded', timeout: MAX_WAIT_MS});
            restarts += 1;
          }
        }
        for (const assertion of row.assertions) await assertState(page, assertion);
        for (const expected of row.screenshots || []) if (!state.screenshots.has(expected)) fail(`missing required screenshot ${expected}`);
      } catch (error) {
        result.result = 'FAIL';
        result.error = String(error.message || error).replace(/[\r\n]+/g, ' ').slice(0, 500);
      }
      results.push(result);
      if (result.result !== 'PASS' && plan.failFast !== false) break;
    }
    if (plan.finalDwellMs) {
      await page.bringToFront();
      await page.waitForTimeout(plan.finalDwellMs);
      state.browserVisibleMs += plan.finalDwellMs;
    }
  } finally {
    await browser?.close();
    await new Promise(resolve => fixture?.server.close(resolve) || resolve());
  }
  const files = fs.readdirSync(output).filter(name => fs.statSync(path.join(output, name)).isFile()).sort();
  const manifest = {
    schemaVersion: 1,
    runId: plan.runId,
    target: plan.target,
    browser: path.basename(executablePath),
    browserRestarts: restarts,
    startedAt: startedAt.toISOString(),
    finishedAt: new Date().toISOString(),
    durationMs: Date.now() - startedAt.getTime(),
    browserVisibleMs: state.browserVisibleMs,
    rows: results,
    receipts: state.receipts,
    files: files.map(name => ({name, bytes: fs.statSync(path.join(output, name)).size, sha256: sha256(path.join(output, name))})),
    overall: results.length === plan.rows.length && results.every(row => row.result === 'PASS') ? 'PASS' : 'FAIL'
  };
  fs.writeFileSync(path.join(output, 'matrix-results.json'), `${JSON.stringify(manifest, null, 2)}\n`, {mode: 0o600});
  process.stdout.write(`${JSON.stringify(manifest, null, 2)}\n`);
  if (manifest.overall !== 'PASS') process.exitCode = 1;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) main().catch(error => { console.error(error.message); process.exitCode = 1; });
