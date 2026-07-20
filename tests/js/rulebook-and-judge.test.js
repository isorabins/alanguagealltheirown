const test = require('node:test'); const assert = require('node:assert/strict');
const L = require('../../viewer/api/_lib.js'); const { response } = require('./helpers.js');

test('adopted view excludes every other status and hashes meaning', () => {
  const rb={rules:[{id:'r1',status:'adopted',text_en:'yes'},{id:'r2',status:'proposed',text_en:'no'},{id:'r3',status:'rejected',text_en:'never'}]};
  assert.match(L.renderRulebook(rb),/yes/); assert.doesNotMatch(L.renderRulebook(rb),/no|never/);
  const first=L.languagePayload(rb); rb.rules[1].text_en='changed proposal'; assert.equal(L.languagePayload(rb).hash,first.hash);
  rb.rules[0].text_en='changed adopted'; assert.notEqual(L.languagePayload(rb).hash,first.hash);
});

test('judge refuses incomplete item coverage', async () => {
  const original={call:L.call,getGraderPrompt:L.getGraderPrompt,guard:L.guard};
  L.guard=()=> 'original'; L.getGraderPrompt=async()=> 'grader';
  let count=0; L.call=async()=>({text:++count===1?'1. first\n2. second':'{"mode":"RELAY","items":[{"n":1,"verdict":"SURVIVED"}],"invented":[]}',usage:{}});
  delete require.cache[require.resolve('../../viewer/api/judge.js')]; const handler=require('../../viewer/api/judge.js');
  const res=response(); await handler({method:'POST',body:{text:'original',decoded:'decoded'},headers:{}},res);
  assert.equal(res.statusCode,502); assert.equal(res.body.code,'invalid_judgment'); Object.assign(L,original);
});
