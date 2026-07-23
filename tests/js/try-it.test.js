const test=require('node:test'); const assert=require('node:assert/strict'); const {response}=require('./helpers.js');
const L=require('../../viewer/api/_lib.js');

test('decode stops before provider call on version mismatch',async()=>{
  const original={guard:L.guard,getRulebook:L.getRulebook,call:L.call}; let called=false;
  L.guard=()=> 'encoded'; L.getRulebook=async()=>({rules:[{id:'r1',status:'adopted',text_en:'law'}]}); L.call=async()=>{called=true;return{text:'decoded'}};
  delete require.cache[require.resolve('../../viewer/api/decode.js')]; const handler=require('../../viewer/api/decode.js'); const res=response();
  await handler({method:'POST',body:{encoded:'encoded',rulebook_version:'old',rulebook_hash:'old'},headers:{'content-type':'application/json'}},res);
  assert.equal(res.statusCode,409); assert.equal(res.body.code,'rulebook_changed'); assert.equal(called,false); Object.assign(L,original);
});

test('provider outcomes classify allowance separately',()=>{
  assert.equal(L.classifyProvider(402,{error:{message:'payment'}}),'allowance_exhausted');
  assert.equal(L.classifyProvider(429,{error:{message:'busy'}}),'provider_rate_limited');
  assert.equal(L.classifyProvider(503,{error:{message:'down'}}),'provider_unavailable');
  assert.equal(L.classifyProvider(401,{error:{message:'bad key'}}),'provider_auth_error');
});

test('normal encode and decode retain one language version without exposing rules',async()=>{
  const rb={rules:[{id:'rule-001',status:'adopted',text_en:'Use one marker.'},{id:'rule-002',status:'proposed',text_en:'private proposal'}]};
  const original={guard:L.guard,getRulebook:L.getRulebook,call:L.call,tokenCount:L.tokenCount};
  L.guard=(req,res,field)=>req.body[field]; L.getRulebook=async()=>rb; L.tokenCount=async(text)=>text==='hello'?2:1;
  L.call=async(model,system,user)=>({text:user==='hello'?'ENC':'hello',usage:{}});
  try{
    delete require.cache[require.resolve('../../viewer/api/encode.js')]; const encode=require('../../viewer/api/encode.js');
    let res=response(); await encode({method:'POST',body:{text:'hello'},headers:{'content-type':'application/json'}},res);
    assert.equal(res.statusCode,200); assert.match(res.body.journey_id,/^[0-9a-f-]{36}$/); assert.ok(res.body.rulebook_version); assert.ok(res.body.rulebook_hash); assert.equal(JSON.stringify(res.body).includes('Use one marker.'),false);
    const encoded=res.body;
    delete require.cache[require.resolve('../../viewer/api/decode.js')]; const decode=require('../../viewer/api/decode.js');
    res=response(); await decode({method:'POST',body:{encoded:encoded.encoded,rulebook_version:encoded.rulebook_version,rulebook_hash:encoded.rulebook_hash},headers:{'content-type':'application/json'}},res);
    assert.equal(res.statusCode,200); assert.equal(res.body.decoded,'hello'); assert.equal(res.body.rulebook_hash,encoded.rulebook_hash);
  }finally{Object.assign(L,original)}
});

test('cold rulebook fetch failure has its own unavailable outcome',async()=>{
  const oldFetch=global.fetch; global.fetch=async()=>({ok:false,status:503,json:async()=>({})});
  try{await assert.rejects(L.getRulebook(true),(error)=>error.code==='rulebook_unavailable'&&error.status===503)}
  finally{global.fetch=oldFetch}
});
