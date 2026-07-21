import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {validatePlan} from '../runner.mjs';

const HERE=path.dirname(fileURLToPath(import.meta.url));
const ROOT=path.dirname(HERE);
test('rejects a production plan without immutable approval receipt',()=>assert.throws(()=>validatePlan({schemaVersion:1,target:'production',rows:[{id:1,actions:[],assertions:[]}]}),/approvalReceipt/));
test('runs generic fixture through a real browser including restart and cleanup',()=>{
  const browser='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  if(!fs.existsSync(browser)) return;
  const output=fs.mkdtempSync(path.join(os.tmpdir(),'generic-forward-'));
  const run=spawnSync(process.execPath,[path.join(ROOT,'runner.mjs'),'--plan',path.join(ROOT,'fixtures/generic-plan.json'),'--output',output,'--browser',browser,'--headless'],{encoding:'utf8'});
  assert.equal(run.status,0,run.stderr||run.stdout);
  const result=JSON.parse(fs.readFileSync(path.join(output,'matrix-results.json'),'utf8'));
  assert.equal(result.overall,'PASS');
  assert.equal(result.browserRestarts,1);
  assert.ok(fs.existsSync(path.join(output,'03-generic-clean.png')));
});
