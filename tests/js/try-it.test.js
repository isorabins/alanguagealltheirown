const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {response}=require('./helpers.js');
const L=require('../../viewer/api/_lib.js');

const html=fs.readFileSync(path.join(__dirname,'../../viewer/index.html'),'utf8');

test('Try It is visibly disabled and never described as the fixed Scoring V2 exam',()=>{
  assert.match(html,/Try It is unavailable/);
  assert.match(html,/distinct ad-hoc audit/);
  assert.doesNotMatch(html,/id="ti-go"|id="ti-text"|run the exam/);
  assert.doesNotMatch(html,/same encode, decode, and fact-audit path used by the scheduled benchmarks/);
});

for(const [name,modulePath,body] of [
  ['encode','../../viewer/api/encode.js',{text:'x'.repeat(10000)}],
  ['decode','../../viewer/api/decode.js',{encoded:'x'.repeat(10000),rulebook_version:'stale',rulebook_hash:'stale'}],
  ['judge','../../viewer/api/judge.js',{text:'valid input',decoded:'malformed judgment path'}],
]){
  test(`${name} endpoint is unreachable before state or provider work`,async()=>{
    const original={getRulebook:L.getRulebook,call:L.call,tokenCount:L.tokenCount};
    let downstream=0;
    L.getRulebook=async()=>{downstream++;throw new Error('provider unavailable')};
    L.call=async()=>{downstream++;throw new Error('provider unavailable')};
    L.tokenCount=async()=>{downstream++;return 1};
    try{
      delete require.cache[require.resolve(modulePath)];
      const handler=require(modulePath);
      const res=response();
      await handler({method:'POST',body,headers:{'content-type':'application/json'}},res);
      assert.equal(res.statusCode,404);
      assert.equal(res.body.code,'try_it_disabled');
      assert.equal(downstream,0);
    }finally{Object.assign(L,original)}
  });
}
