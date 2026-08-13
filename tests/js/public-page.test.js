const test=require('node:test'); const assert=require('node:assert/strict'); const fs=require('node:fs'); const path=require('node:path'); const vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'../../viewer/index.html'),'utf8');
const copyDeck=fs.readFileSync(path.join(__dirname,'../../viewer/prototype-observatory-copy.md'),'utf8');
const scoringFixtures=JSON.parse(fs.readFileSync(path.join(__dirname,'../fixtures/scoring-v2-events.json'),'utf8'));
const observatoryTruth=JSON.parse(fs.readFileSync(path.join(__dirname,'../fixtures/public-observatory-truth.json'),'utf8'));

function viewerDocument() {
  const elements=new Map();
  return {
    elements,
    document:{getElementById(id){
      if(!elements.has(id)) elements.set(id,{
        innerHTML:'',textContent:'',hidden:false,scrollTop:0,scrollHeight:0,
        classList:{add(){},remove(){}},style:{},addEventListener(){}
      });
      return elements.get(id);
    }}
  };
}

test('public viewer inline JavaScript parses',()=>{
  const script=html.match(/<script>\s*([\s\S]*?)<\/script>/);
  assert.ok(script); assert.doesNotThrow(()=>new vm.Script(script[1]));
});

test('public page has mobile disclosure and suggestion placement',()=>{
  assert.match(html,/@media\s*\(max-width:\s*760px\)/); assert.match(html,/id="suggestion-form"/);
  assert.ok(html.indexOf('id="suggestion-form"')>html.indexOf('class="panes"'));
  assert.ok(html.indexOf('id="suggestion-form"')<html.indexOf('id="decisions"'));
  assert.match(html,/<details class="sect">/); assert.match(html,/Full transcript/);
});

test('production Observatory implements locked prototype B hierarchy without prototype controls',()=>{
  for(const id of ['evidence-chain','tx','conversation-exam','language-panel','featured-note','field-note-archive','lab-categories']){
    assert.match(html,new RegExp(`id="${id}"`));
  }
  assert.match(html,/Agent-to-agent communication is growing exponentially/);
  assert.match(html,/exam-flow/);
  assert.match(html,/copy current rulebook/);
  assert.match(html,/Try this with your own agent/);
  assert.doesNotMatch(html,/prototype-switcher|preview trace|prototype simulation|variant-name/);
  assert.doesNotMatch(html,/preserve exact identifiers before compressing surrounding prose/);
});

test('locked opening copy and timer order are preserved',()=>{
  assert.match(html,/That’s crazy\. What if we made a shorthand/);
  assert.match(html,/This is a public experiment reaching toward that goal\./);
  assert.doesNotMatch(html,/public experiment and art project|The agents invent the language|timers-cap/);
  assert.ok(html.indexOf('id="t-turn"') < html.indexOf('id="t-exam"'));
  assert.match(html,/id="t-turn">--:--<\/span><span class="tlab">next turn<\/span>/);
  assert.doesNotMatch(html,/id="t-conversation"|class="tlab">next Conversation<\/span>/);
  assert.match(html,/Scoring V2 calls compression successful only when 100% of the semantic meaning in the conversation survives encoding and decoding\./);
  assert.match(html,/DeepSeek Agent A invents or revises one focused idea\. Kimi Agent B audits it and alone may adopt or reject it\./);
  assert.match(copyDeck,/This is a public experiment reaching toward that goal\./);
  assert.match(html,/id="exam-jump" href="#live-test-section">see last test ↓<\/a>/);
});

test('explanations appear from the meaningful label without visible question marks',()=>{
  assert.match(html,/class="metric info-hover" tabindex="0" data-tip=/);
  assert.match(html,/\.info-hover:hover::after,\.info-hover:focus-visible::after\{display:block\}/);
  assert.doesNotMatch(html,/class="help"|aria-label="Explain |<button[^>]*>\?<\/button>/);
  for(const surface of ['evidence-card pass info-hover','trace-stage info-hover','status-count info-hover']){
    assert.match(html,new RegExp(surface));
  }
  assert.doesNotMatch(html,/exam-stage-head info-hover/);
});

test('latest exam joins every canonical atom to verdict and decoded evidence',()=>{
  assert.match(html,/function latestExamHtml/);
  assert.match(html,/class="exam-flow"/);
  assert.match(html,/atom-evidence/);
  assert.match(html,/01 · Original/);
  assert.match(html,/04 · Semantic audit/);
});

test('Lab Notebook exposes all six source-backed categories',()=>{
  for(const label of ['Complete legislature','Development exams','Conversation archive','Research and human questions','Prompts and judging machinery','Raw public records']){
    assert.match(html,new RegExp(label));
  }
});

function progressApi(){
  const start=html.indexOf('var PUBLIC_PROGRESS_PHASES=');
  const end=html.indexOf('\nfunction render(S)',start);
  assert.ok(start>=0&&end>start,'public exam progress functions must be independently testable');
  return Function(html.slice(start,end)+'\nreturn {validPublicExamProgress,validPublicExamTransition,completedProgressMatchesExam,publicExamProgressView};')();
}

function progressSnapshot(phase='completed'){
  const phases=['exam_started','benchmark_selected','language_loaded','encoder_started','encoder_completed','decoder_started','decoder_completed','judge_started','audit_progress','completed'];
  const active=phases.slice(0,phases.indexOf(phase)+1);
  const snapshot={
    schema_version:1,run_id:'exam-2400-0123456789abcdef',turn:2400,phase,
    updated_at:'2026-08-13T00:00:10Z',benchmark_id:'B1',benchmark_name:'Event prose',
    language_version:'adopted-test',language_hash:'a'.repeat(64),
    receipts:active.map((step,index)=>({phase:step,at:`2026-08-13T00:00:${String(index).padStart(2,'0')}Z`,message:step.replaceAll('_',' ')}))
  };
  if(['encoder_completed','decoder_started','decoder_completed','judge_started','audit_progress','completed'].includes(phase))snapshot.encoded='SAFE ENCODED';
  if(['decoder_completed','judge_started','audit_progress','completed'].includes(phase))snapshot.decoded='Safe decoded response';
  if(['audit_progress','completed'].includes(phase))snapshot.audit={completed:4,total:4,survived:3,corrupted:1,missing:0,inventions:0};
  if(phase==='completed'){
    snapshot.tokens={original:100,encoded:61};
    snapshot.result={judge_valid:true,meaning_pass:false,compression_success:false,semantic_coverage_pct:75,status:'VALID'};
  }
  return snapshot;
}

test('public trace validates bounded snapshots and rejects hostile or mixed data',()=>{
  const api=progressApi(),completed=progressSnapshot();
  assert.equal(api.validPublicExamProgress(completed),true);
  assert.equal(api.validPublicExamProgress({...completed,raw_exception:'secret'}),false);
  assert.equal(api.validPublicExamProgress({...completed,encoded:'x'.repeat(20001)}),false);
  assert.equal(api.validPublicExamProgress({...completed,decoded:'OPENROUTER_API_KEY=do-not-publish'}),false);
  const started=progressSnapshot('exam_started');
  const selected=progressSnapshot('benchmark_selected');
  assert.equal(api.validPublicExamTransition(started,selected),true);
  assert.equal(api.validPublicExamTransition(started,{...selected,run_id:'exam-2401-fedcba9876543210'}),false);
  assert.equal(api.validPublicExamTransition(started,progressSnapshot('encoder_started')),false);
});

test('public trace renders complete interrupted failed stale missing malformed and unavailable truthfully',()=>{
  const api=progressApi(),completed=progressSnapshot();
  const exam={turn:2400,benchmark_id:'B1',language_version:'adopted-test',language_hash:'a'.repeat(64),encoded:'SAFE ENCODED',decoded:'Safe decoded response',orig_tokens:100,enc_tokens:61,judge_valid:true,meaning_pass:false,compression_success:false,semantic_coverage_pct:75};
  assert.equal(api.publicExamProgressView(completed,{latestExam:exam,runtime:{status:'paused'},now:Date.parse('2026-08-13T01:00:00Z')}).state,'verified complete');
  for(const phase of ['interrupted','failed']){
    const snapshot=progressSnapshot('exam_started');
    snapshot.phase=phase;snapshot.error_class=phase==='interrupted'?'interrupted':'provider_timeout';
    snapshot.receipts.push({phase,at:'2026-08-13T00:00:02Z',message:`exam ${phase}`});
    assert.equal(api.publicExamProgressView(snapshot,{now:Date.parse('2026-08-13T00:00:03Z')}).state,phase);
  }
  assert.equal(api.publicExamProgressView(progressSnapshot('encoder_started'),{now:Date.parse('2026-08-13T01:00:00Z')}).state,'stale');
  assert.equal(api.publicExamProgressView(null,{loadStatus:'missing'}).state,'missing');
  assert.equal(api.publicExamProgressView(null,{loadStatus:'malformed'}).state,'malformed');
  assert.equal(api.publicExamProgressView(null,{loadStatus:'unavailable'}).state,'unavailable');
  assert.equal(api.publicExamProgressView({...completed,encoded:'mismatch'},{latestExam:exam}).state,'malformed');
});

test('Watch the Live Test is persisted-state only and matches the locked terminal design',()=>{
  assert.match(html,/id="live-test-section"/);
  assert.match(html,/id="trace-body" role="log" aria-live="polite" tabindex="0"/);
  assert.match(html,/\.trace-body\{height:28rem;overflow:auto/);
  assert.match(html,/\.trace-body::-webkit-scrollbar/);
  assert.match(html,/body\._followPublicProgress=body\.scrollHeight-body\.scrollTop-body\.clientHeight<32/);
  assert.match(html,/if\(renderKey===lastPublicProgressRenderKey\)return view/);
  assert.match(html,/if\(shouldFollow\)body\.scrollTop=body\.scrollHeight;else body\.scrollTop=priorTop/);
  assert.match(html,/class="trace-meta"/);
  assert.match(html,/fact-by-fact judgment evidence/);
  assert.match(html,/class="trace-verdict/);
  assert.match(html,/TEST PASS|TEST FAILURE/);
  assert.match(html,/class="trace-conclusion-grid"/);
  assert.match(html,/message-body savings/);
  assert.match(html,/Expected meaning:/);
  assert.match(html,/Test failed\./);
  assert.match(html,/\.trace-verdict> b\{[^}]*clamp\(\.8rem,1\.25vw,1rem\)/);
  assert.match(html,/@media \(max-width: 760px\)[\s\S]*?\.trace-line\{grid-template-columns:/);
  const refresh=html.slice(html.indexOf('function refreshPublicExamProgress'),html.indexOf('window.ALATO_PUBLIC_PROGRESS'));
  assert.match(refresh,/public-exam-progress\.json/);
  assert.match(refresh,/commits\?sha=main&path=state%2Fpublic-exam-progress\.json&per_page=1/);
  assert.match(refresh,/\(!runtime\|\|runtime\.status==="paused"\)&&publicProgressPathExists!==true/);
  assert.doesNotMatch(refresh,/\/api\/|encode|decode|judge|OPENROUTER|provider/i);
  assert.doesNotMatch(html,/preview trace|prototype simulation|replay trace/);
});

test('public page explains Scoring V2 and labels immutable history honestly',()=>{
  assert.match(html,/Five repeating messages retain original/);
  assert.match(html,/legacy V1/);
  assert.match(html,/V1 and V2 results are not compared/);
  assert.match(html,/INVALID JUDGE RESULT/);
  assert.match(html,/evaluator failure, not a benchmark failure/);
  assert.doesNotMatch(html,/avg savings · last 10 passing/);
  assert.doesNotMatch(html,/avg fidelity · last 10 exams/);
  assert.doesNotMatch(html,/avg fidelity · benchmark cycle/);
});

test('public exact-wiring copy identifies the active V2 judge and legacy V1 prompt',()=>{
  const howStart=html.indexOf('<h2>How This Works</h2>');
  const promptsStart=html.indexOf('<h2>The Prompts</h2>',howStart);
  const how=html.slice(howStart,promptsStart);
  const filesStart=html.indexOf('var files = [');
  const filesEnd=html.indexOf('];',filesStart);
  const promptFiles=html.slice(filesStart,filesEnd+2);

  assert.match(how,/Scoring V2/);
  assert.match(how,/SURVIVED, CORRUPTED, or MISSING/);
  assert.match(how,/decoded evidence/);
  assert.match(how,/deterministic literal/i);
  assert.match(how,/INVALID JUDGE RESULT/);
  assert.match(promptFiles,/\["grader_v2\.md",\s*"active Scoring V2 judge/);
  assert.match(promptFiles,/\["grader\.md",\s*"legacy V1 judge/);
  assert.doesNotMatch(promptFiles,/\["grader\.md",\s*"the judge/);
});

test('viewer selects only the latest valid Scoring V2 result as current',()=>{
  const source=html.match(/function latestValidScoringV2\(tests\) \{([\s\S]*?)\n\}/);
  assert.ok(source,'latestValidScoringV2 must remain independently testable');
  const latestValidScoringV2=Function('tests',source[1]);
  const v1={benchmark_version:'v1',fidelity:100};
  const valid={scoring_version:'v2',judge_valid:true,turn:20,semantic_coverage_pct:90};
  const invalid={scoring_version:'v2',judge_valid:false,turn:21};
  assert.equal(latestValidScoringV2([v1,valid,invalid]),valid);
  assert.equal(latestValidScoringV2([v1,invalid]),null);
});

test('viewer headline savings requires a valid strict success',()=>{
  const source=html.match(/function bestStrictScoringV2\(tests\) \{([\s\S]*?)\n\}/);
  assert.ok(source,'bestStrictScoringV2 must remain independently testable');
  const bestStrictScoringV2=Function('tests',source[1]);
  const best=bestStrictScoringV2(observatoryTruth.tests);
  assert.equal(best.turn,1650);
  assert.equal(best.orig_tokens,469);
  assert.equal(best.enc_tokens,269);
  assert.equal(best.message_body_savings_pct,43);
  assert.equal(best.semantic_coverage_pct,100);
});

test('viewer labels V2, V1, and pre-V1 without comparing scores',()=>{
  const source=html.match(/function scoringLabel\(t\) \{([\s\S]*?)\n\}/);
  assert.ok(source,'scoringLabel must remain independently testable');
  const scoringLabel=Function('t',source[1]);
  assert.equal(scoringLabel({scoring_version:'v2'}),'Scoring V2');
  assert.equal(scoringLabel({benchmark_version:'v1'}),'legacy V1');
  assert.equal(scoringLabel({era:'benchmark-v1'}),'legacy V1');
  assert.equal(scoringLabel({}),'pre-V1 legacy');
  assert.doesNotMatch(html,/versus its previous valid run/);
  assert.doesNotMatch(html,/fidelity_delta/);
});

test('Scoring V2 rendering exposes all separate outcomes and decoded evidence',()=>{
  for(const label of ['meaning pass','compression','semantic coverage','critical failures','inventions','message-body savings','decoded evidence']) {
    assert.match(html,new RegExp(label,'i'));
  }
  assert.match(html,/prior valid V2 result/);
});

test('offline V2 fixtures render inspectable verdicts and invalid-judge separation',()=>{
  const start=html.indexOf('function messageBodySavingsPct(t) {');
  const end=html.indexOf('\n\nfunction render(S)',start);
  assert.ok(start>=0 && end>start,'Scoring V2 renderer must remain independently testable');
  const scoringV2EvidenceHtml=Function(html.slice(start,end)+'\nreturn scoringV2EvidenceHtml;')();
  const valid=scoringV2EvidenceHtml(scoringFixtures.valid_failure);
  assert.match(valid,/meaning pass<b>FAIL/);
  assert.match(valid,/semantic coverage<b>50%/);
  assert.match(valid,/critical failures<b>1/);
  assert.match(valid,/message-body savings<b>\+42%/);
  assert.match(valid,/B2\.01 · CORRUPTED · critical/);
  assert.match(valid,/decoded evidence: “Vessel C18A”/);
  assert.match(valid,/Vessel is cleared &lt;now&gt;/);
  const invalid=scoringV2EvidenceHtml(scoringFixtures.invalid_judge);
  assert.match(invalid,/INVALID JUDGE RESULT/);
  assert.match(invalid,/evaluator failure, not a benchmark failure/);
  assert.match(invalid,/semantic coverage<b>unavailable/);
  assert.match(invalid,/message-body savings<b>\+31%/);
  assert.doesNotMatch(invalid,/meaning pass<b>FAIL/);
});

test('completed V2 exams persist coverage and body savings independently',()=>{
  const script=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
  const end=script.indexOf('\nfunction runtimeView');
  assert.ok(end>0,'viewer render functions must remain independently executable');

  const viewer=viewerDocument();
  const elements=viewer.elements;
  const api=Function('document',script.slice(0,end)+'\nreturn {render,bestMessageBodySavingsV2};')(viewer.document);
  const validFailure={
    type:'test',turn:200,scoring_version:'v2',judge_valid:true,
    benchmark_id:'B3',benchmark_name:'Farming data',meaning_pass:false,
    semantic_coverage_pct:63,message_body_savings_pct:37,
    compression_success:false,orig_tokens:435,enc_tokens:274,
    answer_key:[],atom_results:[],critical_failures:[],inventions:[]
  };
  const invalid={
    type:'test',turn:203,scoring_version:'v2',judge_valid:false,
    benchmark_id:'B4',benchmark_name:'Retail prose',judge_reason:'malformed evidence',
    semantic_coverage_pct:null,message_body_savings_pct:46,
    compression_success:null,orig_tokens:428,enc_tokens:231
  };

  assert.equal(api.bestMessageBodySavingsV2([validFailure,invalid]),null);
  api.render({
    conversation:[validFailure,invalid],
    rulebook:{version:'0.1',rules:[]},collaboration:{},conversations:[],x:{},meta:{updated:'fixture'}
  });

  for(const label of ['rulebook revisions','turns','rules adopted','best strict savings · V2','latest coverage · V2','latest Conversation']) assert.match(elements.get('metrics').innerHTML,new RegExp(label));
  assert.match(elements.get('metrics').innerHTML,/best strict savings · V2[\s\S]*<b>—/);
  assert.match(elements.get('metrics').innerHTML,/latest coverage · V2[\s\S]*<b>63% · fail/);
  assert.match(elements.get('exams').innerHTML,/t203[\s\S]*INVALID JUDGE RESULT[\s\S]*coverage unavailable[\s\S]*body savings \+46%/);
  assert.match(elements.get('exams').innerHTML,/t200[\s\S]*coverage 63%[\s\S]*body savings \+37%/);
  assert.doesNotMatch(elements.get('exams').innerHTML,/&lt;span/,
    'trusted result markup must render as labels, not leak as visible HTML text');
});

test('last deployed savings remain visible when the live refresh fails',async()=>{
  const script=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
  const loadCall=script.indexOf('\nloadState();');
  assert.ok(loadCall>0,'loadState must remain independently executable');
  const viewer=viewerDocument();
  const fallbackExam={
    type:'test',turn:200,scoring_version:'v2',judge_valid:true,
    benchmark_id:'B1',benchmark_name:'Event prose',meaning_pass:true,
    semantic_coverage_pct:100,message_body_savings_pct:44,
    compression_success:true,orig_tokens:469,enc_tokens:263,
    answer_key:[],atom_results:[],critical_failures:[],inventions:[]
  };
  const window={STATE:{
    conversation:[fallbackExam],rulebook:{version:'0.1',rules:[]},
    collaboration:{},conversations:[],x:{},meta:{updated:'deployed fixture'}
  }};
  const failedFetch=()=>Promise.reject(new Error('offline refresh failed'));
  const api=Function('document','window','fetch',
    script.slice(0,loadCall)+'\nreturn {loadState};')(viewer.document,window,failedFetch);

  api.loadState();
  assert.match(viewer.elements.get('metrics').innerHTML,/best strict savings · V2[\s\S]*<b>\+44%/,
    'the deployed snapshot must render synchronously before refresh settles');
  await new Promise(resolve=>setImmediate(resolve));
  assert.match(viewer.elements.get('metrics').innerHTML,/best strict savings · V2[\s\S]*<b>\+44%/,
    'a failed refresh must not clear the last deployed savings');
  assert.match(viewer.elements.get('exams').innerHTML,/coverage 100%[\s\S]*body savings \+44%/);
});

test('failed live refresh dynamically loads and renders the bundled archive',async()=>{
  const script=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
  const loadCall=script.indexOf('\nloadState();');
  assert.ok(loadCall>0,'loadState must remain independently executable');
  const viewer=viewerDocument();
  const appended=[];
  viewer.document.createElement=(tag)=>({tag,src:'',onload:null,onerror:null});
  viewer.document.head={appendChild(node){appended.push(node);}};
  const window={};
  const failedFetch=()=>Promise.reject(new Error('offline refresh failed'));
  const api=Function('document','window','fetch',
    script.slice(0,loadCall)+'\nreturn {loadState};')(viewer.document,window,failedFetch);

  api.loadState();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(appended.length,1);
  assert.equal(appended[0].src,'state.js');
  assert.equal(viewer.elements.get('metrics'),undefined,
    'the historical archive must not be assumed present before its script loads');

  window.STATE={
    conversation:[{
      type:'test',turn:200,scoring_version:'v2',judge_valid:true,
      benchmark_id:'B1',benchmark_name:'Event prose',meaning_pass:true,
      semantic_coverage_pct:100,message_body_savings_pct:44,
      compression_success:true,orig_tokens:469,enc_tokens:263,
      answer_key:[],atom_results:[],critical_failures:[],inventions:[]
    }],
    rulebook:{version:'0.1',rules:[]},collaboration:{},conversations:[],x:{},
    meta:{updated:'deployed fixture'}
  };
  appended[0].onload();
  await new Promise(resolve=>setImmediate(resolve));
  assert.match(viewer.elements.get('metrics').innerHTML,/best strict savings · V2[\s\S]*<b>\+44%/);
  assert.match(viewer.elements.get('exams').innerHTML,/coverage 100%[\s\S]*body savings \+44%/);
});

test('left clock always counts down to the next 15-minute turn',()=>{
  const startup=fs.readFileSync(path.join(__dirname,'../../viewer/startup.js'),'utf8');
  const viewer=viewerDocument();
  const realNow=Date.now;
  Date.now=()=>Date.parse('2026-08-13T00:05:00Z');
  const window={
    PUBLIC_BOOTSTRAP:{
      turn:2403,updated:'2026-08-13T00:00:00Z',metrics:[],
      runtime:{status:'active',turn:2403,next_exam_turn:2406,next_conversation_turn:2418}
    },
    setInterval(){return 1;},setTimeout(){return 1;}
  };
  try {
    Function('window','document',startup)(window,viewer.document);
    assert.equal(viewer.elements.get('t-turn').textContent,'10:00');
    assert.equal(viewer.elements.get('t-exam').textContent,'40:00');
  } finally { Date.now=realNow; }
});

test('headline counters render before the full historical archive loads',()=>{
  const bootstrapTag='<script src="bootstrap.js"></script>';
  const startupTag='<script src="startup.js"></script>';
  assert.ok(html.includes(bootstrapTag));
  assert.ok(html.includes(startupTag));
  assert.ok(html.indexOf(bootstrapTag)<html.indexOf(startupTag));
  assert.ok(html.indexOf(startupTag)<html.indexOf('<script>'));
  assert.doesNotMatch(html,/<script src="state\.js"><\/script>/,
    'the multi-megabyte historical archive must not block initial rendering');
  assert.match(html,/function loadBundledState\(\)/,
    'the deployed archive remains available as a fallback after live fetch failure');
  assert.match(html,/if \(!when && window\.PUBLIC_BOOTSTRAP\) when = window\.PUBLIC_BOOTSTRAP\.updated \|\| null/,
    'a GitHub commit-lookup failure must retain the deployed counter timestamp');

  const startup=fs.readFileSync(path.join(__dirname,'../../viewer/startup.js'),'utf8');
  const viewer=viewerDocument();
  const intervals=[];
  const window={
    PUBLIC_BOOTSTRAP:{
      turn:2193,updated:new Date(Date.now()-5*60*1000).toISOString(),
      metrics:[['turns','2193'],['rules adopted','24']],
      runtime:{status:'active',turn:2193,next_exam_turn:2196,next_conversation_turn:2202}
    },
    setInterval(fn){intervals.push(fn); return 1;},
    setTimeout(){ return 1; }
  };
  Function('window','document',startup)(window,viewer.document);

  assert.match(viewer.elements.get('t-exam').textContent,/^(?:\d\d:\d\d|running now)$/);
  assert.match(viewer.elements.get('t-turn').textContent,/^(?:\d\d:\d\d|running now)$/);
  assert.match(viewer.elements.get('exam-jump').textContent,/^(?:watch next test|watch live test now) ↓$/);
  assert.match(viewer.elements.get('metrics').innerHTML,/turns[\s\S]*<b>2193<\/b>/);
  assert.equal(intervals.length,1,'one lightweight timer owns the countdown refresh');
});

test('paused runtime never advances turn or exam clocks',()=>{
  const startup=fs.readFileSync(path.join(__dirname,'../../viewer/startup.js'),'utf8');
  const viewer=viewerDocument();
  let now=Date.parse('2026-08-13T00:00:00Z');
  const realNow=Date.now;
  Date.now=()=>now;
  const window={
    PUBLIC_BOOTSTRAP:{
      turn:2400,updated:'2026-08-13T00:00:00Z',metrics:[],
      runtime:{status:'paused',turn:2400,message:'Experiment paused at turn 2400. No new turn or exam is running. The public record remains available.',next_exam_turn:null,next_conversation_turn:null}
    },
    setInterval(){return 1;},setTimeout(){return 1;}
  };
  try {
    Function('window','document',startup)(window,viewer.document);
    assert.equal(viewer.elements.get('t-exam').textContent,'Paused');
    assert.equal(viewer.elements.get('t-turn').textContent,'Paused');
    assert.equal(viewer.elements.get('exam-jump').textContent,'see last test ↓');
    assert.equal(viewer.elements.get('runtime-status-detail').textContent,window.PUBLIC_BOOTSTRAP.runtime.message);
    now+=24*60*60*1000;
    window.ALATO_STARTUP.updateCounters();
    assert.equal(viewer.elements.get('t-exam').textContent,'Paused');
    assert.equal(viewer.elements.get('t-turn').textContent,'Paused');
  } finally { Date.now=realNow; }
});

test('full-history runtime status uses the same persisted pause contract',()=>{
  const source=html.match(/function runtimeStatusView\(runtime, when, now, turn\) \{([\s\S]*?)\n\}/);
  assert.ok(source);
  const runtimeView=()=>({visible:false});
  const runtimeStatusView=Function('runtimeView','runtime','when','now','turn',
    source[1])(runtimeView,{
      status:'paused',turn:2400,
      message:'Experiment paused at turn 2400. No new turn or exam is running. The public record remains available.'
    },null,Date.now(),2400);
  assert.equal(runtimeStatusView.visible,true);
  assert.equal(runtimeStatusView.detail,'Experiment paused at turn 2400. No new turn or exam is running. The public record remains available.');
});

test('stale active claims and Composition are absent',()=>{
  for(const phrase of ['dumb script','mindless script','gigawatt','power-grid','Composition','Slack ASK',':online']) assert.doesNotMatch(html,new RegExp(phrase,'i'));
});

test('public explanation includes agent repeal power and preserved history',()=>{
  assert.match(html,/repeal/i); assert.match(html,/<h2>Rule History<\/h2>/i);
});

test('public page fetches only the sanitized collaboration snapshot',()=>{
  assert.match(html,/public-collaboration\.json/); assert.doesNotMatch(html,/getOptional\("collaboration\.json"/);
  assert.match(html,/Iso:.*esc\(r\.answer\)/s);
});

test('public page curates collaboration, judgment, and proposal history',()=>{
  assert.match(html,/id="experiment-status"/);
  assert.doesNotMatch(html,/stale proposal-state deadlock/);
  assert.match(html,/Lab notebook · methods, machinery &amp; complete archive/);
  assert.match(html,/outward web research/);
  assert.match(html,/project lookup/);
  assert.match(html,/function conversationJudgmentHtml/);
  assert.match(html,/raw judgment evidence/);
  assert.doesNotMatch(html,/<div class="judg"><div class="jhead">concrete-outcome judgment<\/div><pre>/);
  assert.match(html,/id="current-proposal"/);
  assert.match(html,/earlier unresolved record/);
});

test('canonical conversation-2322 renders four verdicts, evidence, and six ordered messages',()=>{
  const conversations=JSON.parse(fs.readFileSync(path.join(__dirname,'../../state/conversations.json'),'utf8'));
  const canonical=conversations.find(row=>row.id==='conversation-2322');
  assert.ok(canonical);
  const script=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
  const end=script.indexOf('\nfunction runtimeView');
  const viewer=viewerDocument();
  const render=Function('document',script.slice(0,end)+'\nreturn render;')(viewer.document);
  render({conversation:[],rulebook:{version:'0.1',rules:[]},collaboration:{},conversations:[canonical],x:{},meta:{}});
  const output=viewer.elements.get('conversation-exam').innerHTML;
  for(const row of canonical.judgment.requirements){
    assert.match(output,new RegExp('requirement '+row.id+'[\\s\\S]*PASS[\\s\\S]*'+row.evidence.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')));
  }
  assert.doesNotMatch(output,/No verdict recorded/);
  let cursor=-1;
  canonical.messages.forEach(message=>{
    const next=output.indexOf('speaker '+message.speaker,cursor+1);
    assert.ok(next>cursor,'six messages retain stored speaker order');
    cursor=next;
  });
  assert.match(output,/raw judgment evidence/);
});

test('invalid and malformed Conversation judgments are held, never accepted',()=>{
  assert.match(html,/var held = judgment\.valid !== true/);
  assert.match(html,/judgment held/);
  assert.match(html,/contradictions:/);
});

test('operator questions show their actual text without implying the core loop is blocked',()=>{
  const source=html.match(/function operatorQuestionView\(openAsks\) \{([\s\S]*?)\n\}\n\nfunction runtimeView/);
  assert.ok(source,'operatorQuestionView must remain executable as a pure status decision');
  const operatorQuestionView=Function('openAsks',source[1]);
  const open=[
    {question:'First question',request_turn:1178},
    {question:'What happened in turn 1176?',request_turn:1184}
  ];
  const current=operatorQuestionView(open);
  assert.equal(current.summary,'What happened in turn 1176?');
  assert.match(current.meta,/latest request · turn 1184/);
  assert.match(current.meta,/2 open questions retained/);
  assert.match(current.meta,/core experiment continues autonomously/);
  assert.doesNotMatch(current.summary+current.meta,/deadlock|blocked/i);
  const empty=operatorQuestionView([]);
  assert.equal(empty.summary,'No operator question is waiting.');
  assert.match(empty.meta,/core experiment continues autonomously/);
});

test('public page contains overflow and keyboard-focus safeguards',()=>{
  assert.match(html,/pre\s*\{[^}]*max-width:\s*100%[^}]*white-space:\s*pre-wrap[^}]*overflow-wrap:\s*anywhere/s);
  assert.match(html,/\.archive-list summary\s*\{[^}]*overflow-wrap:\s*anywhere/s);
  assert.match(html,/:focus-visible\s*\{[^}]*outline:\s*2px solid var\(--accent\)/s);
  assert.match(html,/body\s*\{[^}]*width:\s*min\(1100px,\s*100%\)/s);
});

test('major section headings keep the shared vertical rhythm',()=>{
  assert.match(html,/body > h2:first-of-type \{ margin-top: 0; \}/);
  assert.doesNotMatch(html,/\n\s*h2:first-of-type \{/);
});

test('stale runtime notice is truthful and self-clearing',()=>{
  assert.match(html,/id="runtime-status"[^>]*aria-live="polite"/);
  assert.match(html,/The scheduled loop is not advancing\./);
  assert.match(html,/public record is preserved at turn/);
  assert.match(html,/path=state%2Fconversation\.json&per_page=1/);
  assert.match(html,/runtimeStatus\.classList\.remove\("visible"\)/);

  const source=html.match(/function runtimeView\(when, now, turn\) \{([\s\S]*?)\n\}\n\nfunction runtimeStatusView/);
  assert.ok(source,'runtimeView must remain executable as a pure status decision');
  const runtimeView=Function('when','now','turn',source[1]);
  const now=Date.parse('2026-07-31T10:00:00Z');
  const stale=runtimeView('2026-07-31T09:00:00Z',now,1213);
  assert.equal(stale.visible,true);
  assert.match(stale.heading,/not advancing/);
  assert.match(stale.detail,/turn 1213/);
  const fresh=runtimeView('2026-07-31T09:50:00Z',now,1214);
  assert.equal(fresh.visible,false);
  assert.match(fresh.stamp,/live/);
  const unknown=runtimeView(null,now,1213);
  assert.equal(unknown.visible,true);
  assert.match(unknown.heading,/unavailable/);
  assert.doesNotMatch(unknown.stamp,/\blive$/);
});
