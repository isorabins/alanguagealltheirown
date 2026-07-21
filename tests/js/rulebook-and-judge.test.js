const test = require('node:test'); const assert = require('node:assert/strict'); const fs=require('node:fs'); const path=require('node:path');
const L = require('../../viewer/api/_lib.js'); const { response } = require('./helpers.js');

test('adopted view excludes every other status and hashes meaning', () => {
  const rb={rules:[{id:'r1',status:'adopted',text_en:'yes',pending_repeal:{rationale:'not language'}},{id:'r2',status:'proposed',text_en:'no'},{id:'r3',status:'rejected',text_en:'never'},{id:'r4',status:'repealed',text_en:'gone'},{id:'r5',status:'historical',text_en:'old'}]};
  assert.match(L.renderRulebook(rb),/yes/); assert.doesNotMatch(L.renderRulebook(rb),/no|never|gone|old|not language/);
  const first=L.languagePayload(rb); rb.rules[1].text_en='changed proposal'; assert.equal(L.languagePayload(rb).hash,first.hash);
  rb.rules[0].text_en='changed adopted'; assert.notEqual(L.languagePayload(rb).hash,first.hash);
});

test('JavaScript adopted hash matches the canonical Python fixture receipt',()=>{
  const rb=JSON.parse(fs.readFileSync(path.join(__dirname,'../fixtures/mixed-rulebook.json'),'utf8'));
  const view=L.languagePayload(rb);
  assert.equal(view.hash,'4a3d2eb8f3eb5971a03161ca6ce16dfcd48bc16e46c4da566e17818296f2085e');
  assert.equal(view.version,'adopted-4a3d2eb8f3eb');
});

test('judge refuses incomplete item coverage', async () => {
  const original={call:L.call,getGraderPrompt:L.getGraderPrompt,guard:L.guard};
  L.guard=()=> 'original'; L.getGraderPrompt=async()=> 'grader';
  let count=0; L.call=async()=>({text:++count===1?'1. first\n2. second':'{"mode":"RELAY","items":[{"n":1,"verdict":"SURVIVED"}],"invented":[]}',usage:{}});
  delete require.cache[require.resolve('../../viewer/api/judge.js')]; const handler=require('../../viewer/api/judge.js');
  const res=response(); await handler({method:'POST',body:{text:'original',decoded:'decoded'},headers:{'content-type':'application/json'}},res);
  assert.equal(res.statusCode,502); assert.equal(res.body.code,'invalid_judgment'); Object.assign(L,original);
});

test('judge refuses boolean and string-coerced item identifiers', async () => {
  for(const id of [true,'1']){
    const original={call:L.call,getGraderPrompt:L.getGraderPrompt,guard:L.guard};
    L.guard=()=> 'original'; L.getGraderPrompt=async()=> 'grader'; let count=0;
    L.call=async()=>({text:++count===1?'1. first\n2. second':JSON.stringify({mode:'RELAY',items:[{n:id,verdict:'SURVIVED'},{n:2,verdict:'SURVIVED'}],invented:[]}),usage:{}});
    delete require.cache[require.resolve('../../viewer/api/judge.js')]; const handler=require('../../viewer/api/judge.js');
    const res=response(); await handler({method:'POST',body:{text:'original',decoded:'decoded'},headers:{'content-type':'application/json'}},res);
    assert.equal(res.statusCode,502); assert.equal(res.body.code,'invalid_judgment'); Object.assign(L,original);
  }
});
