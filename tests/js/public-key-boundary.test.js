const test=require('node:test'); const assert=require('node:assert/strict');

test('Try It rejects private-key fallback', async () => {
  const previousPublic=process.env.OPENROUTER_PUBLIC_API_KEY, previousPrivate=process.env.OPENROUTER_API_KEY;
  delete process.env.OPENROUTER_PUBLIC_API_KEY; process.env.OPENROUTER_API_KEY='private-must-not-work';
  delete require.cache[require.resolve('../../viewer/api/_lib.js')]; const L=require('../../viewer/api/_lib.js');
  await assert.rejects(()=>L.call('model',null,'hello',{noRetry:true}),error=>error.code==='public_key_unavailable');
  if(previousPublic===undefined)delete process.env.OPENROUTER_PUBLIC_API_KEY;else process.env.OPENROUTER_PUBLIC_API_KEY=previousPublic;
  if(previousPrivate===undefined)delete process.env.OPENROUTER_API_KEY;else process.env.OPENROUTER_API_KEY=previousPrivate;
});
