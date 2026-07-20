const test=require('node:test'); const assert=require('node:assert/strict'); const {response}=require('./helpers.js');
const C=require('../../viewer/api/_collaboration.js');

test('login writes persistent secure 30-minute cookie and logout clears it',async()=>{
  const originals={login:C.login,logout:C.logout};
  C.login=async(password)=>{assert.equal(password,'right');return{token:'a'.repeat(64),expires_at:Date.now()+1800000}};
  C.logout=async(req,res)=>C.clearSessionCookie(res);
  delete require.cache[require.resolve('../../viewer/api/human-session.js')]; const handler=require('../../viewer/api/human-session.js');
  let res=response(); await handler({method:'POST',body:{password:'right'},headers:{}},res);
  assert.match(res.headers['set-cookie'],/Max-Age=1800/); assert.match(res.headers['set-cookie'],/HttpOnly/); assert.match(res.headers['set-cookie'],/Secure/); assert.match(res.headers['set-cookie'],/SameSite=Strict/);
  res=response(); await handler({method:'DELETE',headers:{cookie:'alato_human='+('a'.repeat(64))}},res); assert.match(res.headers['set-cookie'],/Max-Age=0/);
  Object.assign(C,originals);
});

test('session check is non-sliding',async()=>{
  const source=require('node:fs').readFileSync(require.resolve('../../viewer/api/_collaboration.js'),'utf8');
  const body=source.slice(source.indexOf('async function session'),source.indexOf('async function requireSession'));
  assert.doesNotMatch(body,/\bSET\b|EXPIRE|SESSION_SECONDS/);
});
