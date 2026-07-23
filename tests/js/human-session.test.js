const test=require('node:test'); const assert=require('node:assert/strict'); const {response}=require('./helpers.js');
const C=require('../../viewer/api/_collaboration.js');

test('login writes persistent secure 30-minute cookie and logout clears it',async()=>{
  const originals={login:C.login,logout:C.logout};
  C.login=async(password)=>{assert.equal(password,'right');return{token:'a'.repeat(64),expires_at:Date.now()+1800000}};
  C.logout=async(req,res)=>C.clearSessionCookie(res);
  delete require.cache[require.resolve('../../viewer/api/human-session.js')]; const handler=require('../../viewer/api/human-session.js');
  let res=response(); await handler({method:'POST',body:{password:'right'},headers:{'content-type':'application/json'}},res);
  assert.equal(res.statusCode,204); assert.equal(res.body,null);
  assert.match(res.headers['set-cookie'],/Max-Age=1800/); assert.match(res.headers['set-cookie'],/HttpOnly/); assert.match(res.headers['set-cookie'],/Secure/); assert.match(res.headers['set-cookie'],/SameSite=Strict/);
  res=response(); await handler({method:'DELETE',headers:{cookie:'alato_human='+('a'.repeat(64))}},res); assert.equal(res.statusCode,204); assert.match(res.headers['set-cookie'],/Max-Age=0/);
  Object.assign(C,originals);
});

test('session check is non-sliding',async()=>{
  const source=require('node:fs').readFileSync(require.resolve('../../viewer/api/_collaboration.js'),'utf8');
  const body=source.slice(source.indexOf('async function session'),source.indexOf('async function requireSession'));
  assert.doesNotMatch(body,/\bSET\b|EXPIRE|SESSION_SECONDS/);
  assert.doesNotMatch(source,/session:\$\{token\}/); assert.match(source,/function sessionKey[\s\S]*sha256/);
});

test('direct login rejects a wrong password before touching Redis',async()=>{
  const prior=process.env.HUMAN_PASSWORD; process.env.HUMAN_PASSWORD='right';
  const oldFetch=global.fetch; global.fetch=async()=>{throw new Error('Redis must not be called')};
  try { await assert.rejects(C.login('wrong'),(error)=>error.code==='unauthorized'&&error.status===401&&error.message==='authentication failed'); }
  finally { global.fetch=oldFetch; if(prior===undefined) delete process.env.HUMAN_PASSWORD; else process.env.HUMAN_PASSWORD=prior; }
});

test('expired session is rejected and refresh does not issue a sliding cookie',async()=>{
  const priorUrl=process.env.UPSTASH_REDIS_REST_URL, priorToken=process.env.UPSTASH_REDIS_REST_TOKEN, oldFetch=global.fetch;
  process.env.UPSTASH_REDIS_REST_URL='https://redis.example.test'; process.env.UPSTASH_REDIS_REST_TOKEN='fixture-token';
  global.fetch=async()=>({ok:true,json:async()=>({result:JSON.stringify({created_at:1,expires_at:Date.now()-1})})});
  try{
    const res=response(); const handler=require('../../viewer/api/human-session.js');
    await handler({method:'GET',headers:{cookie:'alato_human='+('a'.repeat(64))}},res);
    assert.equal(res.statusCode,401); assert.equal(res.body.authenticated,false); assert.equal(res.headers['set-cookie'],undefined);
  }finally{
    global.fetch=oldFetch;
    if(priorUrl===undefined)delete process.env.UPSTASH_REDIS_REST_URL;else process.env.UPSTASH_REDIS_REST_URL=priorUrl;
    if(priorToken===undefined)delete process.env.UPSTASH_REDIS_REST_TOKEN;else process.env.UPSTASH_REDIS_REST_TOKEN=priorToken;
  }
});

test('malformed cookie is a generic unauthenticated session without Redis access',async()=>{
  const oldFetch=global.fetch; let called=false; global.fetch=async()=>{called=true;throw new Error('no')};
  try{assert.equal(await C.session({headers:{cookie:'alato_human=%'}}),null);assert.equal(called,false)}
  finally{global.fetch=oldFetch}
});
