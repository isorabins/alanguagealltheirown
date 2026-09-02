const test=require('node:test'); const assert=require('node:assert/strict');

test('disabled Try It library exposes no provider call or alternate language authority', () => {
  const L=require('../../viewer/api/_lib.js');
  for(const name of ['call','tokenCount','getRulebook','getGraderPrompt','languagePayload','renderRulebook']) {
    assert.equal(Object.prototype.hasOwnProperty.call(L,name),false,name);
  }
});
