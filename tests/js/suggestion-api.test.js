const test=require('node:test'); const assert=require('node:assert/strict'); const fs=require('node:fs'); const path=require('node:path'); const C=require('../../viewer/api/_collaboration.js');

test('suggestion bounds reject empty and oversized text without interpreting markup',()=>{
  assert.throws(()=>C.cleanText('',600),/1-600/); assert.throws(()=>C.cleanText('x'.repeat(601),600),/1-600/);
  assert.equal(C.cleanText('<b>literal</b>',600),'<b>literal</b>');
  assert.equal(C.cleanText('  first\r\n  second  ',600),'first\n  second');
});

test('hostile fixture remains inert data and oversized input is rejected',()=>{
  const rows=JSON.parse(fs.readFileSync(path.join(__dirname,'../fixtures/suggestions/hostile.json'),'utf8'));
  for(const row of rows) assert.equal(C.cleanText(row.text,600),row.text);
  assert.throws(()=>C.cleanText('x'.repeat(601),600),/1-600/);
});
