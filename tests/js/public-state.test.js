const test=require('node:test');
const assert=require('node:assert/strict');
const {createReader,validSnapshot}=require('../../viewer/public-state.js');
const A='a'.repeat(40),B='b'.repeat(40);
const date='2026-09-05T01:00:00Z';
function state(turn){return {conversation:[{turn,type:'message',agent:'A',content:'Turn '+turn}],rulebook:{rules:[]},meta:{runtime:{turn,status:'active'}},metrics:[['turns',String(turn)]]};}
function response(value,status=200){return {ok:status===200,status,json:async()=>value,text:async()=>typeof value==='string'?value:JSON.stringify(value)};}
function archive(s){return 'window.STATE = '+JSON.stringify(s)+';\n';}
function head(sha){return response([{sha,commit:{committer:{date}}}]);}
function deferred(){let resolve;const promise=new Promise(r=>resolve=r);return {resolve,promise};}

test('all public state and progress reads use one immutable repository revision',async()=>{
 const urls=[],seen=[],progress=[],runtime=[];
 const reader=createReader({initial:state(0),onSnapshot:s=>seen.push(s),onProgress:(s,status)=>progress.push([s,status]),onRuntime:(...x)=>runtime.push(x),fetch:async url=>{
  urls.push(url);
  if(url.includes('api.github.com'))return head(A);
  if(url.endsWith('preview.json'))return response(state(1));
  if(url.endsWith('state.js'))return response(archive(state(1)));
  if(url.endsWith('public-exam-progress.json'))return response({turn:1});
  throw Error(url);
 }});
 await reader.refresh();
 assert.equal(seen.at(-1).meta.runtime.turn,1);
 assert.deepEqual(runtime.at(-1),[date,1,{turn:1,status:'active'}]);
 assert.equal(progress.at(-1)[1],'ok');
 for(const url of urls.filter(u=>u.includes('raw.githubusercontent')))assert.ok(url.includes('/'+A+'/'));
 assert.ok(!urls.some(u=>u.includes('/main/')));
});

test('a mixed-turn snapshot cannot replace a coherent last good view',async()=>{
 const mixed=state(1);mixed.meta.runtime.turn=2;
 assert.equal(validSnapshot(mixed),false);
 const seen=[];
 const reader=createReader({initial:state(0),onSnapshot:s=>seen.push(s),fetch:async url=>url.includes('api.github.com')?head(A):url.endsWith('state.js')?response(archive(mixed)):response(mixed)});
 await reader.refresh();
 assert.deepEqual(seen.map(s=>s.conversation.at(-1).turn),[0]);
});

test('a delayed older refresh cannot replace the newer revision or its progress',async()=>{
 const old=deferred(),seen=[];let calls=0;
 const reader=createReader({initial:state(0),onSnapshot:s=>seen.push(s),fetch:async url=>{
  if(url.includes('api.github.com'))return head(url.includes('sha=main') ? (++calls===1?A:B) : (url.includes('sha='+A)?A:B));
  if(url.includes('/'+A+'/')&&url.endsWith('preview.json'))return old.promise;
  const turn=url.includes('/'+A+'/')?1:2;
  return url.endsWith('state.js')?response(archive(state(turn))):response(state(turn));
 }});
 const first=reader.refresh();await new Promise(r=>setImmediate(r));
 await reader.refresh();old.resolve(response(state(1)));await first;
 assert.equal(seen.at(-1).meta.runtime.turn,2);
 const acceptedTwo=seen.findIndex(s=>s.meta.runtime.turn===2);
 assert.ok(seen.slice(acceptedTwo).every(s=>s.meta.runtime.turn===2));
});

test('failed canonical refresh keeps deployed evidence and reads legacy archive without executing it',async()=>{
 const seen=[];
 const reader=createReader({onSnapshot:s=>seen.push(s),fetch:async url=>{
  if(url==='state.js')return response(archive(state(7)));
  return response(null,503);
 }});
 await reader.refresh();
 assert.equal(seen.at(-1).meta.runtime.turn,7);
});

test('current preview and truthful runtime arrive while full archive is still pending',async()=>{
 const full=deferred(),seen=[],runtime=[];
 const reader=createReader({initial:state(0),onSnapshot:s=>seen.push(s),onRuntime:(...x)=>runtime.push(x),fetch:async url=>{
  if(url.includes('api.github.com'))return head(A);
  if(url.endsWith('state.js'))return full.promise;
  return response(state(9));
 }});
 const work=reader.refresh();await new Promise(r=>setImmediate(r));
 assert.equal(seen.at(-1).meta.runtime.turn,9);
 assert.equal(runtime.at(-1)[1],9);
 full.resolve(response(archive(state(9))));await work;
});

test('missing progress has an explicit result without disturbing the visible state',async()=>{
 const progress=[],seen=[];
 const reader=createReader({initial:state(0),onSnapshot:s=>seen.push(s),onProgress:(s,status)=>progress.push(status),fetch:async url=>{
  if(url.includes('api.github.com'))return head(A);
  if(url.endsWith('public-exam-progress.json'))return response(null,404);
  return url.endsWith('state.js')?response(archive(state(9))):response(state(9));
 }});
 await reader.refresh();assert.equal(progress.at(-1),'missing');assert.equal(seen.at(-1).meta.runtime.turn,9);
});


test('successful deployed preview still loads the complete historical archive',async()=>{
 for(const local of [true,false]) {
  const seen=[],urls=[];
  const reader=createReader({local,onSnapshot:s=>seen.push(s),fetch:async url=>{
   urls.push(url);
   if(url==='preview.json')return response(state(30));
   if(url==='state.js'){const full=state(30);full.conversation.unshift({turn:1});return response(archive(full));}
   return response(null,503);
  }});
  await reader.refresh();
  assert.equal(seen.at(-1).conversation[0].turn,1);
  assert.ok(urls.includes('state.js'));
 }
});

test('ongoing refresh discovers a new revision but never downgrades or downloads the same archive twice',async()=>{
 let latest=A;const urls=[],seen=[];
 const reader=createReader({initial:state(0),onSnapshot:s=>seen.push(s),fetch:async url=>{
  urls.push(url);
  if(url.includes('api.github.com'))return head(latest);
  const turn=latest===A?1:2;
  return url.endsWith('state.js')?response(archive(state(turn))):response(state(turn));
 }});
 await reader.refresh();const count=seen.length;
 await reader.refresh();assert.equal(seen.length,count);
 assert.equal(urls.filter(u=>u.endsWith('state.js')).length,1);
 latest=B;await reader.refresh();assert.equal(seen.at(-1).meta.runtime.turn,2);
 assert.ok(urls.filter(u=>u.endsWith('public-exam-progress.json')).at(-1).includes(B));
 assert.ok(urls.some(u=>u.includes('sha=main')&&!u.includes('path=')));
 assert.ok(urls.some(u=>u.includes('sha='+B)&&u.includes('path=')));
});

test('deployed fallback explicitly reports unknown live freshness',async()=>{
 const runtime=[];
 const reader=createReader({local:true,onSnapshot(){},onRuntime:(...x)=>runtime.push(x),fetch:async url=>url==='state.js'?response(archive(state(7))):response(state(7))});
 await reader.refresh();
 assert.deepEqual(runtime.at(-1),[null,7,{turn:7,status:'active'}]);
});

test('notes-only head update uses pinned notes and does not invent a newer turn time',async()=>{
 const runtime=[],seen=[];
 const reader=createReader({initial:state(0),onSnapshot:s=>seen.push(s),onRuntime:(...x)=>runtime.push(x),fetch:async url=>{
  if(url.includes('api.github.com'))return url.includes('path=')?head(A):response([{sha:B,commit:{committer:{date:'2026-09-06T01:00:00Z'}}}]);
  if(url.endsWith('/notes.json'))return response([{text:'A new human note'}]);
  return url.endsWith('state.js')?response(archive(state(9))):response(state(9));
 }});
 await reader.refresh();
 assert.equal(seen.at(-1).notes[0].text,'A new human note');
 assert.equal(runtime.at(-1)[0],date);
});

test('failed newer archive preserves an already complete last-good revision',async()=>{
 let latest=A;const seen=[];
 const reader=createReader({initial:state(0),onSnapshot:(s,meta)=>seen.push([s,meta]),fetch:async url=>{
  if(url.includes('api.github.com'))return head(latest);
  if(latest===B&&url.endsWith('state.js'))return response(null,503);
  const data=state(latest===A?1:2);data.conversation.unshift({turn:0});
  return url.endsWith('state.js')?response(archive(data)):response(data);
 }});
 await reader.refresh();latest=B;await reader.refresh();
 assert.equal(seen.at(-1)[0].meta.runtime.turn,1);
 assert.equal(seen.at(-1)[1].revision,A);
 assert.equal(seen.at(-1)[0].conversation.length,2);
});


test('legacy archives without runtime metadata remain readable without inventing live status',async()=>{
 const legacy=state(7);delete legacy.meta.runtime;
 const runtime=[],seen=[];
 const reader=createReader({local:true,onSnapshot:s=>seen.push(s),onRuntime:(...x)=>runtime.push(x),fetch:async url=>url==='state.js'?response(archive(legacy)):response(null,404)});
 await reader.refresh();
 assert.equal(seen.at(-1).conversation.at(-1).turn,7);
 assert.deepEqual(runtime.at(-1),[null,7,{}]);
});

test('canonical preview plus failed archive loads an available complete deployed snapshot',async()=>{
 const seen=[],urls=[];
 const reader=createReader({onSnapshot:(s,m)=>seen.push([s,m]),fetch:async url=>{
  urls.push(url);
  if(url.includes('api.github.com'))return head(A);
  if(url.includes(A)&&url.endsWith('preview.json'))return response(state(30));
  if(url==='state.js'){const full=state(29);full.conversation.unshift({turn:1});return response(archive(full));}
  return response(null,503);
 }});
 await reader.refresh();
 assert.ok(urls.includes('state.js'));
 assert.equal(seen.at(-1)[0].conversation[0].turn,1);
 assert.equal(seen.at(-1)[1].complete,true);
 assert.equal(seen.at(-1)[1].source,'deployed');
 assert.equal(seen.at(-1)[1].revision,null);
 assert.equal(seen[0][1].complete,false);
});

test('unavailable full archives leave the canonical preview explicitly incomplete',async()=>{
 const seen=[];
 const reader=createReader({onSnapshot:(s,m)=>seen.push([s,m]),fetch:async url=>{
  if(url.includes('api.github.com'))return head(A);
  if(url.includes(A)&&url.endsWith('preview.json'))return response(state(30));
  return response(null,503);
 }});
 await reader.refresh();
 assert.equal(seen.at(-1)[0].meta.runtime.turn,30);
 assert.equal(seen.at(-1)[1].complete,false);
});

test('rate-limited head uses one complete current archive with persisted completion time',async()=>{
 const seen=[],runtime=[],progress=[],urls=[];let turn=10;
 const reader=createReader({initial:state(4),onSnapshot:(s,m)=>seen.push([s,m]),onRuntime:(...r)=>runtime.push(r),onProgress:(s,status)=>progress.push(status),fetch:async url=>{
  urls.push(url);
  if(url.includes('api.github.com'))return response(null,403);
  const s=state(turn);s.meta.updated=date;s.conversation.unshift({turn:1});
  return url.endsWith('state.js')?response(archive(s)):response(s);
 }});
 await reader.refresh();
 assert.equal(seen.at(-1)[0].conversation[0].turn,1);
 assert.deepEqual(seen.at(-1)[1],{source:'canonical-unpinned',revision:null,complete:true});
 assert.equal(runtime.at(-1)[0],date);assert.equal(progress.at(-1),'unavailable');
 await reader.refresh();assert.equal(urls.filter(u=>u.endsWith('state.js')).length,1);
 turn=11;await reader.refresh();assert.equal(seen.at(-1)[0].meta.runtime.turn,11);
 assert.ok(!urls.some(u=>u.endsWith('public-exam-progress.json')));
});

test('lagging or failed unpinned archive retries and later stale pinned head cannot roll it back',async()=>{
 const seen=[];let phase='lag';
 const reader=createReader({initial:state(4),onSnapshot:(s,m)=>seen.push([s,m]),fetch:async url=>{
  if(url.includes('api.github.com'))return phase==='pinned'?head(A):response(null,403);
  if(url==='preview.json'||url==='state.js')return response(null,503);
  const turn=phase==='pinned'?8:url.endsWith('preview.json')?10:phase==='lag'?9:10;
  return url.endsWith('state.js')?response(archive(state(turn))):response(state(turn));
 }});
 await reader.refresh();assert.equal(seen.at(-1)[0].meta.runtime.turn,4);
 phase='good';await reader.refresh();assert.equal(seen.at(-1)[0].meta.runtime.turn,10);
 phase='pinned';await reader.refresh();assert.equal(seen.at(-1)[0].meta.runtime.turn,10);
 assert.equal(seen.at(-1)[1].source,'canonical-unpinned');
});

test('unpinned fallback never invents completion time when source time is missing or invalid',async()=>{
 for(const updated of [undefined,'invalid']) {
  const runtime=[];
  const reader=createReader({onSnapshot(){},onRuntime:(...r)=>runtime.push(r),fetch:async url=>{
   if(url.includes('api.github.com'))return response(null,403);
   const s=state(10);s.meta.updated=updated;
   return url.endsWith('state.js')?response(archive(s)):response(s);
  }});
  await reader.refresh();assert.equal(runtime.at(-1)[0],null);
 }
});

test('same-turn runtime changes retry a lagging archive and publish only matching full evidence',async()=>{
 let phase='initial',downloads=0;const seen=[];
 const reader=createReader({onSnapshot:s=>seen.push(s),fetch:async url=>{
  if(url.includes('api.github.com'))return response(null,403);
  const s=state(10);s.meta.updated=date;
  if(phase!=='initial'&&(url.endsWith('preview.json')||phase==='matching'))s.meta.runtime.status='paused';
  if(url.endsWith('state.js')){downloads++;return response(archive(s));}
  return response(s);
 }});
 await reader.refresh();phase='lag';await reader.refresh();assert.equal(seen.at(-1).meta.runtime.status,'active');
 phase='matching';await reader.refresh();assert.equal(seen.at(-1).meta.runtime.status,'paused');
 await reader.refresh();assert.equal(downloads,3);
});

test('failed raw archive preserves the complete last-good snapshot and retries later',async()=>{
 let phase=0;const seen=[];
 const reader=createReader({onSnapshot:(s,m)=>seen.push([s,m]),fetch:async url=>{
  if(url.includes('api.github.com'))return response(null,403);
  if(phase===1&&url.endsWith('state.js'))return response(null,503);
  const s=state(phase===0?10:11);
  return url.endsWith('state.js')?response(archive(s)):response(s);
 }});
 await reader.refresh();phase=1;await reader.refresh();assert.equal(seen.at(-1)[0].meta.runtime.turn,10);assert.equal(seen.at(-1)[1].complete,true);
 phase=2;await reader.refresh();assert.equal(seen.at(-1)[0].meta.runtime.turn,11);
});
