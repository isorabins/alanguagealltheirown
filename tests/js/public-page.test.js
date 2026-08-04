const test=require('node:test'); const assert=require('node:assert/strict'); const fs=require('node:fs'); const path=require('node:path'); const vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'../../viewer/index.html'),'utf8');
const scoringFixtures=JSON.parse(fs.readFileSync(path.join(__dirname,'../fixtures/scoring-v2-events.json'),'utf8'));

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

test('public page explains Scoring V2 and labels immutable history honestly',()=>{
  assert.match(html,/Five corrected development benchmarks repeat/);
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
  const end=script.indexOf('\nvar TURN_MS');
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

  assert.equal(api.bestMessageBodySavingsV2([validFailure,invalid]),46);
  api.render({
    conversation:[validFailure,invalid],
    rulebook:{version:'0.1',rules:[]},collaboration:{},conversations:[],x:{},meta:{updated:'fixture'}
  });

  assert.match(elements.get('metrics').innerHTML,/best message-body savings · V2<b>\+46%/);
  assert.match(elements.get('metrics').innerHTML,/latest semantic coverage · V2<b>63%/);
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
  assert.match(viewer.elements.get('metrics').innerHTML,/best message-body savings · V2<b>\+44%/,
    'the deployed snapshot must render synchronously before refresh settles');
  await new Promise(resolve=>setImmediate(resolve));
  assert.match(viewer.elements.get('metrics').innerHTML,/best message-body savings · V2<b>\+44%/,
    'a failed refresh must not clear the last deployed savings');
  assert.match(viewer.elements.get('exams').innerHTML,/coverage 100%[\s\S]*body savings \+44%/);
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
  assert.match(html,/Lab notebook · research, methods &amp; archive/);
  assert.match(html,/outward web research/);
  assert.match(html,/project lookup/);
  assert.match(html,/function conversationJudgmentHtml/);
  assert.match(html,/raw judgment evidence/);
  assert.doesNotMatch(html,/<div class="judg"><div class="jhead">concrete-outcome judgment<\/div><pre>/);
  assert.match(html,/id="current-proposal"/);
  assert.match(html,/earlier unresolved record/);
});

test('operator questions show their actual text without implying the core loop is blocked',()=>{
  const source=html.match(/function operatorQuestionView\(openAsks\) \{([\s\S]*?)\n\}\n\nvar TURN_MS/);
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

test('stale runtime notice is truthful and self-clearing',()=>{
  assert.match(html,/id="runtime-status"[^>]*aria-live="polite"/);
  assert.match(html,/The scheduled loop is not advancing\./);
  assert.match(html,/public record is preserved at turn/);
  assert.match(html,/path=state%2Fconversation\.json&per_page=1/);
  assert.match(html,/runtimeStatus\.classList\.remove\("visible"\)/);

  const source=html.match(/function runtimeView\(when, now, turn\) \{([\s\S]*?)\n\}\n\nfunction loadState/);
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
