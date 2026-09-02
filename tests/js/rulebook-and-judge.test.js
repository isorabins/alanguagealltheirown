const test = require('node:test'); const assert = require('node:assert/strict');
const L = require('../../viewer/api/_lib.js'); const { response } = require('./helpers.js');

test('disabled judge endpoint rejects incomplete item coverage before provider work', async () => {
  delete require.cache[require.resolve('../../viewer/api/judge.js')]; const handler=require('../../viewer/api/judge.js');
  const res=response(); await handler({method:'POST',body:{text:'original',decoded:'decoded'},headers:{'content-type':'application/json'}},res);
  assert.equal(res.statusCode,404); assert.equal(res.body.code,'try_it_disabled');
});

test('disabled judge endpoint rejects coerced item identifiers before provider work', async () => {
  for(const id of [true,'1']){
    delete require.cache[require.resolve('../../viewer/api/judge.js')]; const handler=require('../../viewer/api/judge.js');
    const res=response(); await handler({method:'POST',body:{text:'original',decoded:'decoded'},headers:{'content-type':'application/json'}},res);
    assert.equal(res.statusCode,404); assert.equal(res.body.code,'try_it_disabled');
  }
});
