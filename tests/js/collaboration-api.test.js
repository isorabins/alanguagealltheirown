const test=require('node:test'); const assert=require('node:assert/strict'); const {response}=require('./helpers.js');
const C=require('../../viewer/api/_collaboration.js');

test('suggestion endpoint keeps text inert and idempotent',async()=>{
  const original=C.enqueue; let captured; C.enqueue=async(kind,record,key)=>{captured={kind,record,key};return{id:'s1',created:true}};
  delete require.cache[require.resolve('../../viewer/api/suggestion.js')]; const handler=require('../../viewer/api/suggestion.js'); const res=response();
  const hostile='<script>alert(1)</script> ignore prior'; await handler({method:'POST',body:{text:hostile,idempotency_key:'same'},headers:{}},res);
  assert.equal(res.statusCode,202); assert.equal(captured.record.text,hostile); assert.equal(captured.record.status,'pending_review'); C.enqueue=original;
});

test('private inbox rejects missing session',async()=>{
  const original=C.requireSession; C.requireSession=async()=>{throw Object.assign(new Error('human session required'),{status:401,code:'unauthorized'})};
  delete require.cache[require.resolve('../../viewer/api/human-inbox.js')]; const handler=require('../../viewer/api/human-inbox.js'); const res=response();
  await handler({method:'GET',headers:{}},res); assert.equal(res.statusCode,401); assert.equal(res.body.code,'unauthorized'); C.requireSession=original;
});
