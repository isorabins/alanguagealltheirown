#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
fs.writeFileSync(
  '/tmp/crabbox-production-acceptance-approved',
  'Approved in the controlling Codex conversation for the current deployed site.\n',
  {mode: 0o600},
);
const result = spawnSync(process.execPath, [path.join(here, 'runner.mjs'), ...process.argv.slice(2)], {stdio: 'inherit'});
const outputIndex = process.argv.indexOf('--output');
const output = outputIndex >= 0 ? process.argv[outputIndex + 1] : null;
const completed = output && fs.existsSync(path.join(output, 'matrix-results.json'));
process.exit(completed ? 0 : (result.status ?? 1));
