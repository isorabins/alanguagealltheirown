const test=require('node:test'); const assert=require('node:assert/strict'); const {response}=require('./helpers.js');
const L=require('../../viewer/api/_lib.js');

test('decode stops before provider call on version mismatch',async()=>{
  const original={guard:L.guard,getRulebook:L.getRulebook,call:L.call}; let called=false;
  L.guard=()=> 'encoded'; L.getRulebook=async()=>({rules:[{id:'r1',status:'adopted',text_en:'law'}]}); L.call=async()=>{called=true;return{text:'decoded'}};
  delete require.cache[require.resolve('../../viewer/api/decode.js')]; const handler=require('../../viewer/api/decode.js'); const res=response();
  await handler({method:'POST',body:{encoded:'encoded',rulebook_version:'old',rulebook_hash:'old'},headers:{}},res);
  assert.equal(res.statusCode,409); assert.equal(res.body.code,'rulebook_changed'); assert.equal(called,false); Object.assign(L,original);
});

test('provider outcomes classify allowance separately',()=>{
  assert.equal(L.classifyProvider(402,{error:{message:'payment'}}),'allowance_exhausted');
  assert.equal(L.classifyProvider(429,{error:{message:'busy'}}),'provider_rate_limited');
  assert.equal(L.classifyProvider(503,{error:{message:'down'}}),'provider_unavailable');
  assert.equal(L.classifyProvider(401,{error:{message:'bad key'}}),'provider_auth_error');
});
