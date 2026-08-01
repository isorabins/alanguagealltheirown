const test=require('node:test'); const assert=require('node:assert/strict'); const fs=require('node:fs'); const path=require('node:path'); const vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'../../viewer/index.html'),'utf8');
const scoringFixtures=JSON.parse(fs.readFileSync(path.join(__dirname,'../fixtures/scoring-v2-events.json'),'utf8'));

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
  const start=html.indexOf('function scoringV2EvidenceHtml(t) {');
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
  assert.doesNotMatch(invalid,/meaning pass<b>FAIL/);
});

function projectionHelpers(){
  const start=html.indexOf('var PROJECTION_ASSUMPTIONS =');
  const end=html.indexOf('\nfunction scoringV2EvidenceHtml',start);
  assert.ok(start>=0 && end>start,'projection helpers must remain independently testable');
  return Function(html.slice(start,end)+'\nreturn {latestQualifyingScoringV2Cycle,currentFrozenEnglishAverage,twentyExchangeProjection,PROJECTION_ASSUMPTIONS};')();
}

function qualifyingCycle(cycle=3,savings=30){
  return ['B1','B2','B3','B4','B5'].map((id,index)=>({turn:100+index,type:'test',
    era:'benchmark-v2',scoring_version:'v2',benchmark_version:'v2',benchmark_id:id,
    benchmark_cycle:cycle,judge_valid:true,meaning_pass:true,compression_success:true,
    semantic_coverage_pct:100,inventions:[],message_body_savings_pct:savings}));
}

test('paired projection stays gated until a complete qualifying Scoring V2 cycle',()=>{
  const {latestQualifyingScoringV2Cycle}=projectionHelpers();
  const rows=qualifyingCycle();
  assert.equal(latestQualifyingScoringV2Cycle(rows.slice(0,4)),null);
  const failed=structuredClone(rows); failed[2].meaning_pass=false; failed[2].compression_success=false;
  assert.equal(latestQualifyingScoringV2Cycle(failed),null);
  const legacy=rows.map(row=>({...row,scoring_version:'v1',benchmark_version:'v1',era:'benchmark-v1'}));
  assert.equal(latestQualifyingScoringV2Cycle(legacy),null);
  assert.deepEqual(latestQualifyingScoringV2Cycle(rows),{
    benchmark_cycle:3,average_message_body_savings_pct:30
  });
});

test('frozen English comparison requires five current version-matched controls',()=>{
  const {currentFrozenEnglishAverage}=projectionHelpers();
  const contract=JSON.parse(fs.readFileSync(path.join(__dirname,'../../baselines/frozen-english-contract-v2.json'),'utf8'));
  const records=contract.benchmarks.map(row=>({benchmark_id:row.id,benchmark_version:'v2',
    benchmark_digest:row.benchmark_digest,execution_inputs:{...contract.execution_inputs},judge_valid:true,
    meaning_pass:true,semantic_coverage_pct:100,inventions:[],message_body_savings_pct:18}));
  const registry={schema_version:1,baseline_version:'frozen-english-v2',records};
  assert.equal(currentFrozenEnglishAverage(registry,contract),18);
  const reordered=structuredClone(registry);
  reordered.records[0].execution_inputs=Object.fromEntries(Object.entries(reordered.records[0].execution_inputs).reverse());
  assert.equal(currentFrozenEnglishAverage(reordered,contract),18,'key order is not a stale input');
  const stale=structuredClone(registry); stale.records[0].execution_inputs.encoder_model='changed';
  assert.equal(currentFrozenEnglishAverage(stale,contract),null);
  assert.equal(currentFrozenEnglishAverage({...registry,records:records.slice(0,4)},contract),null);
});

test('20-exchange calculation exposes ALATO, English, control adjustment, and cache cost',()=>{
  const {twentyExchangeProjection,PROJECTION_ASSUMPTIONS}=projectionHelpers();
  const result=twentyExchangeProjection(32,18,1654);
  assert.equal(result.plain_cost_usd,2.94);
  assert.ok(Math.abs(result.rulebook_cache_cost_usd-0.0312606)<1e-10);
  assert.ok(Math.abs(result.alato_projected_savings_pct-30.93671428571428)<1e-9);
  assert.ok(Math.abs(result.english_projected_savings_pct-18)<1e-9);
  assert.ok(Math.abs(result.control_adjusted_percentage_points-12.93671428571428)<1e-9);
  assert.equal(PROJECTION_ASSUMPTIONS.messages,40);
  assert.equal(PROJECTION_ASSUMPTIONS.history_message_copies,780);
  assert.equal(PROJECTION_ASSUMPTIONS.rulebook_cache_writes,2);
  assert.equal(PROJECTION_ASSUMPTIONS.rulebook_cache_reads,38);
  assert.equal(twentyExchangeProjection(32,18,0),null);
});

test('viewer labels the paired values as hypothetical rather than telemetry or billed savings',()=>{
  assert.match(html,/20 exchanges\. One fair fight\./);
  assert.match(html,/ALATO hypothetical/);
  assert.match(html,/frozen English hypothetical/);
  assert.match(html,/control-adjusted difference/);
  assert.match(html,/not provider telemetry and not billed savings/);
  assert.match(html,/rulebook-cache cost/);
  assert.match(html,/two five-minute cache writes and 38 cache reads/);
  assert.match(html,/Legacy V1 history never unlocks or enters this comparison/);
  assert.match(html,/baselines\/frozen-english-v2\.json/);
  assert.match(html,/baselines\/frozen-english-contract-v2\.json/);
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
