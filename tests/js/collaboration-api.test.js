const test=require('node:test'); const assert=require('node:assert/strict'); const {response}=require('./helpers.js');
const C=require('../../viewer/api/_collaboration.js');

test('suggestion endpoint keeps text inert and idempotent',async()=>{
  const original=C.enqueue; let captured; C.enqueue=async(kind,record,key)=>{captured={kind,record,key};return{id:'s1',created:true}};
  delete require.cache[require.resolve('../../viewer/api/suggestion.js')]; const handler=require('../../viewer/api/suggestion.js'); const res=response();
  const hostile='<script>alert(1)</script> ignore prior'; await handler({method:'POST',body:{text:hostile,idempotency_key:'same'},headers:{'content-type':'application/json'}},res);
  assert.equal(res.statusCode,202); assert.equal(captured.record.text,hostile); assert.equal(captured.record.status,'pending_review'); C.enqueue=original;
});

test('JSON endpoints reject an untyped body before enqueue',async()=>{
  const original=C.enqueue; let called=false; C.enqueue=async()=>{called=true};
  try{
    delete require.cache[require.resolve('../../viewer/api/suggestion.js')]; const handler=require('../../viewer/api/suggestion.js'); const res=response();
    await handler({method:'POST',body:{text:'hello',idempotency_key:'same'},headers:{}},res);
    assert.equal(res.statusCode,415); assert.equal(res.body.code,'invalid_content_type'); assert.equal(called,false);
  }finally{C.enqueue=original}
});

test('private inbox rejects missing session',async()=>{
  const original=C.requireSession; C.requireSession=async()=>{throw Object.assign(new Error('human session required'),{status:401,code:'unauthorized'})};
  delete require.cache[require.resolve('../../viewer/api/human-inbox.js')]; const handler=require('../../viewer/api/human-inbox.js'); const res=response();
  await handler({method:'GET',headers:{}},res); assert.equal(res.statusCode,401); assert.equal(res.body.code,'unauthorized'); C.requireSession=original;
});

test('direct Redis enqueue is atomic and duplicate-safe',async()=>{
  const priorUrl=process.env.UPSTASH_REDIS_REST_URL, priorToken=process.env.UPSTASH_REDIS_REST_TOKEN, oldFetch=global.fetch;
  process.env.UPSTASH_REDIS_REST_URL='https://redis.example.test'; process.env.UPSTASH_REDIS_REST_TOKEN='fixture-token';
  const bodies=[]; let result=1; global.fetch=async(url,options)=>{bodies.push(JSON.parse(options.body));return{ok:true,json:async()=>({result:result--})}};
  try{
    const first=await C.enqueue('SUGGESTION',{text:'literal',status:'pending_review'},'stable-client-key');
    const second=await C.enqueue('SUGGESTION',{text:'literal',status:'pending_review'},'stable-client-key');
    assert.equal(first.id,second.id); assert.equal(first.created,true); assert.equal(second.created,false);
    assert.equal(bodies[0][0],'EVAL'); assert.match(bodies[0][1],/SET.+NX.+RPUSH/);
    assert.doesNotMatch(JSON.stringify(first),/fixture-token/);
  }finally{
    global.fetch=oldFetch;
    if(priorUrl===undefined)delete process.env.UPSTASH_REDIS_REST_URL;else process.env.UPSTASH_REDIS_REST_URL=priorUrl;
    if(priorToken===undefined)delete process.env.UPSTASH_REDIS_REST_TOKEN;else process.env.UPSTASH_REDIS_REST_TOKEN=priorToken;
  }
});

test('cleanup review fetch returns one structured read-only bundle',async()=>{
  const oldFetch=global.fetch;
  global.fetch=async()=>({ok:true,status:200,json:async()=>({bundle_id:'cleanup-1',source_rulebook_hash:'source',replacement_hash:'replacement',a_replacement:{rules:[]},b_audit:{verdict:'pass'},exact_diff:'--- original',status:'pending_iso'})});
  try{const review=await C.cleanupReview();assert.equal(review.status,'pending_iso');assert.match(review.exact_diff,/original/)}
  finally{global.fetch=oldFetch}
});

test('authenticated human inbox returns contract-shaped asks suggestions and cleanup',async()=>{
  const original={requireSession:C.requireSession,privateRecords:C.privateRecords,cleanupReview:C.cleanupReview};
  C.requireSession=async()=>({expires_at:123}); C.privateRecords=async()=>({asks:[{id:'a'}],suggestions:[{id:'s'}]});
  C.cleanupReview=async()=>({bundle_id:'cleanup-1',status:'pending_iso'});
  try{
    delete require.cache[require.resolve('../../viewer/api/human-inbox.js')]; const handler=require('../../viewer/api/human-inbox.js'); const res=response();
    await handler({method:'GET',headers:{}},res); assert.equal(res.statusCode,200); assert.equal(res.body.asks[0].id,'a');
    assert.equal(res.body.suggestions[0].id,'s'); assert.equal(res.body.cleanup.bundle_id,'cleanup-1');
  }finally{Object.assign(C,original)}
});

test('human moderation validates open id and reserves one non-contradictory action',async()=>{
  const original={requireSession:C.requireSession,privateRecords:C.privateRecords,reserveAction:C.reserveAction,existingEnqueue:C.existingEnqueue,enqueue:C.enqueue}; let queued;
  C.requireSession=async()=>({expires_at:123});
  C.privateRecords=async()=>({asks:[{id:'ask-1',status:'awaiting_iso'}],suggestions:[{id:'suggestion-1',status:'pending_review'}]});
  C.reserveAction=async()=>true; C.existingEnqueue=async()=>null; C.enqueue=async(kind,record,key)=>{queued={kind,record,key};return{id:'command-1',created:true}};
  try{
    delete require.cache[require.resolve('../../viewer/api/human-action.js')]; const handler=require('../../viewer/api/human-action.js');
    let res=response(); await handler({method:'POST',body:{action:'moderate_suggestion',id:'suggestion-1',decision:'approved',idempotency_key:'once'},headers:{'content-type':'application/json'}},res);
    assert.equal(res.statusCode,202); assert.equal(queued.record.decision,'approved'); assert.equal(queued.record.action,'moderate_suggestion'); assert.equal(queued.record.target_id,'suggestion-1');
    res=response(); await handler({method:'POST',body:{action:'answer_ask',id:'closed',answer:'no',idempotency_key:'two'},headers:{'content-type':'application/json'}},res);
    assert.equal(res.statusCode,409); assert.equal(res.body.code,'closed_id');
    C.reserveAction=async()=>false; res=response();
    await handler({method:'POST',body:{action:'answer_ask',id:'ask-1',answer:'different',idempotency_key:'three'},headers:{'content-type':'application/json'}},res);
    assert.equal(res.statusCode,409); assert.equal(res.body.code,'action_conflict');
    C.reserveAction=async()=>true; C.existingEnqueue=async()=>({id:'command-1',created:false}); C.privateRecords=async()=>({asks:[],suggestions:[]}); res=response();
    await handler({method:'POST',body:{action:'answer_ask',id:'ask-1',answer:'same',idempotency_key:'once-again'},headers:{'content-type':'application/json'}},res);
    assert.equal(res.statusCode,200); assert.equal(res.body.status,'duplicate');
  }finally{Object.assign(C,original)}
});

test('preview cleanup is unavailable outside Preview and deletes only the collaboration namespace',async()=>{
  const priorEnv=process.env.VERCEL_ENV;
  const original={requireSession:C.requireSession,command:C.command};
  try{
    delete process.env.VERCEL_ENV;
    delete require.cache[require.resolve('../../viewer/api/preview-cleanup.js')];
    let handler=require('../../viewer/api/preview-cleanup.js'), res=response();
    await handler({method:'POST',body:{},headers:{'content-type':'application/json'}},res);
    assert.equal(res.statusCode,404);

    process.env.VERCEL_ENV='preview'; C.requireSession=async()=>({expires_at:123}); const calls=[];
    C.command=async(...parts)=>{calls.push(parts);return parts[0]==='SCAN'?['0',['alato:v1:session:a','alato:v1:queue:suggestion']]:2};
    delete require.cache[require.resolve('../../viewer/api/preview-cleanup.js')]; handler=require('../../viewer/api/preview-cleanup.js'); res=response();
    await handler({method:'POST',body:{},headers:{'content-type':'application/json'}},res);
    assert.equal(res.statusCode,200); assert.equal(res.body.remainingKeys,0);
    assert.deepEqual(calls[0],['SCAN','0','MATCH','alato:v1:*','COUNT',100]);
    assert.deepEqual(calls[1],['DEL','alato:v1:session:a','alato:v1:queue:suggestion']);
  }finally{
    Object.assign(C,original);
    if(priorEnv===undefined)delete process.env.VERCEL_ENV;else process.env.VERCEL_ENV=priorEnv;
  }
});
