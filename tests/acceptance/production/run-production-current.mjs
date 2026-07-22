#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));

export function childExitStatus(status) {
  return Number.isInteger(status) ? status : 1;
}

function main() {
  const approvalReceipt = process.env.CRABBOX_APPROVAL_RECEIPT;
  if (!approvalReceipt || !path.isAbsolute(approvalReceipt) || !fs.existsSync(approvalReceipt)) {
    console.error('An existing absolute approval receipt in CRABBOX_APPROVAL_RECEIPT is required; the runner cannot create approval.');
    return 2;
  }
  const planIndex = process.argv.indexOf('--plan');
  const planPath = planIndex >= 0 ? process.argv[planIndex + 1] : null;
  if (!planPath || !fs.existsSync(planPath)) {
    console.error('A readable --plan is required.');
    return 2;
  }
  const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
  if (path.resolve(plan.approvalReceipt || '') !== path.resolve(approvalReceipt)) {
    console.error('The plan approval receipt does not match CRABBOX_APPROVAL_RECEIPT.');
    return 2;
  }
  const result = spawnSync(process.execPath, [path.join(here, 'runner.mjs'), ...process.argv.slice(2)], {stdio: 'inherit'});
  return childExitStatus(result.status);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) process.exit(main());
