const test=require('node:test'); const assert=require('node:assert/strict'); const C=require('../../viewer/api/_collaboration.js');

test('suggestion bounds reject empty and oversized text without interpreting markup',()=>{
  assert.throws(()=>C.cleanText('',600),/1-600/); assert.throws(()=>C.cleanText('x'.repeat(601),600),/1-600/);
  assert.equal(C.cleanText('<b>literal</b>',600),'<b>literal</b>');
});
