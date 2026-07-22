import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {validatePlan} from '../runner.mjs';
import {childExitStatus} from '../run-production-current.mjs';

const HERE=path.dirname(fileURLToPath(import.meta.url));
const ROOT=path.dirname(HERE);
test('rejects a production plan without immutable approval receipt',()=>assert.throws(()=>validatePlan({schemaVersion:1,target:'production',rows:[{id:1,actions:[],assertions:[]}]}),/approvalReceipt/));
test('requires a visible dwell for production evidence',()=>{
  const approval=path.join(fs.mkdtempSync(path.join(os.tmpdir(),'approval-')),'receipt.txt');
  fs.writeFileSync(approval,'approved outside the runner\n',{mode:0o600});
  const plan=JSON.parse(fs.readFileSync(path.join(ROOT,'production-current-plan.json'),'utf8'));
  plan.approvalReceipt=approval;
  delete plan.visibleDwellMs;
  assert.throws(()=>validatePlan(plan),/visibleDwellMs/);
});
test('rejects a production plan redirected to a fixture',()=>{
  const approval=path.join(fs.mkdtempSync(path.join(os.tmpdir(),'approval-')),'receipt.txt');
  fs.writeFileSync(approval,'approved outside the runner\n',{mode:0o600});
  const plan=JSON.parse(fs.readFileSync(path.join(ROOT,'production-current-plan.json'),'utf8'));
  plan.approvalReceipt=approval;
  plan.fixtureRoot='fixtures/generic-site';
  assert.throws(()=>validatePlan(plan),/fixtureRoot/);
});
test('production wrapper propagates a failed matrix exit status',()=>{
  assert.equal(childExitStatus(1),1);
  assert.equal(childExitStatus(0),0);
  assert.equal(childExitStatus(null),1);
});
test('production wrapper cannot manufacture its own approval receipt',()=>{
  const missing=path.join(fs.mkdtempSync(path.join(os.tmpdir(),'missing-approval-')),'receipt.txt');
  const run=spawnSync(process.execPath,[path.join(ROOT,'run-production-current.mjs'),'--plan',path.join(ROOT,'production-current-plan.json')],{
    encoding:'utf8',
    env:{...process.env,CRABBOX_APPROVAL_RECEIPT:missing},
  });
  assert.notEqual(run.status,0);
  assert.match(run.stderr,/approval receipt/i);
  assert.equal(fs.existsSync(missing),false);
});
test('runs generic fixture through a real browser including restart and cleanup',()=>{
  const browser='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  if(!fs.existsSync(browser)) return;
  const output=fs.mkdtempSync(path.join(os.tmpdir(),'generic-forward-'));
  const run=spawnSync(process.execPath,[path.join(ROOT,'runner.mjs'),'--plan',path.join(ROOT,'fixtures/generic-plan.json'),'--output',output,'--browser',browser,'--headless'],{encoding:'utf8'});
  assert.equal(run.status,0,run.stderr||run.stdout);
  const result=JSON.parse(fs.readFileSync(path.join(output,'matrix-results.json'),'utf8'));
  assert.equal(result.overall,'PASS');
  assert.equal(result.browserRestarts,1);
  assert.ok(result.durationMs >= 0);
  assert.ok(result.browserVisibleMs >= 0);
  assert.ok(fs.existsSync(path.join(output,'03-generic-clean.png')));
});
