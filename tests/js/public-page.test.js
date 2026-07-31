const test=require('node:test'); const assert=require('node:assert/strict'); const fs=require('node:fs'); const path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../../viewer/index.html'),'utf8');

test('public page has mobile disclosure and suggestion placement',()=>{
  assert.match(html,/@media\s*\(max-width:\s*760px\)/); assert.match(html,/id="suggestion-form"/);
  assert.ok(html.indexOf('id="suggestion-form"')>html.indexOf('class="panes"'));
  assert.ok(html.indexOf('id="suggestion-form"')<html.indexOf('id="decisions"'));
  assert.match(html,/<details class="sect">/); assert.match(html,/Full transcript/);
});

test('public page explains fixed benchmarks and labels the earlier era honestly',()=>{
  assert.match(html,/Five fixed benchmark messages now repeat/);
  assert.match(html,/fresh-payload era/);
  assert.match(html,/separate transfer test still checks/);
  assert.doesNotMatch(html,/Every exam is new/);
  assert.doesNotMatch(html,/avg savings · last 10 passing/);
  assert.doesNotMatch(html,/avg fidelity · last 10 exams/);
});

test('benchmark cycle metrics require five valid benchmark ids',()=>{
  const source=html.match(/function latestCompletedBenchmarkCycle\(tests\) \{([\s\S]*?)\n\}\n\nfunction benchmarkComparisonView/);
  assert.ok(source,'latestCompletedBenchmarkCycle must remain independently testable');
  const latestCompletedBenchmarkCycle=Function('tests',source[1]);
  const cycle1=['B1','B2','B3','B4','B5'].map((id,index)=>({
    benchmark_version:'v1',benchmark_id:id,benchmark_cycle:1,
    fidelity:80+index,token_delta_pct:-10*(index+1)
  }));
  const complete=latestCompletedBenchmarkCycle(cycle1);
  assert.equal(complete.cycle,1);
  assert.equal(complete.avgTokenDeltaPct,-30);
  assert.equal(complete.avgFidelity,82);
  assert.equal(latestCompletedBenchmarkCycle(cycle1.concat([{
    benchmark_version:'v1',benchmark_id:'B1',benchmark_cycle:2,
    fidelity:100,token_delta_pct:-90
  }])).cycle,1);
  assert.equal(latestCompletedBenchmarkCycle([]),null);
});

test('benchmark comparison uses the recorded same-message baseline',()=>{
  const source=html.match(/function benchmarkComparisonView\(t\) \{([\s\S]*?)\n\}\n\nfunction render/);
  assert.ok(source,'benchmarkComparisonView must remain independently testable');
  const benchmarkComparisonView=Function('t',source[1]);
  const view=benchmarkComparisonView({
    benchmark_id:'B3',prior_turn:1179,prior_fidelity:68,fidelity:91,
    fidelity_delta:23,prior_token_delta_pct:-29,token_delta_pct:-34,
    savings_delta_pct:5
  });
  assert.deepEqual(view,{
    valid:true,id:'B3',priorTurn:1179,priorFidelity:68,fidelity:91,
    fidelityDelta:23,priorSavings:29,savings:34,savingsDelta:5
  });
  assert.deepEqual(benchmarkComparisonView({
    benchmark_id:'B3',prior_turn:1179,fidelity_delta:null
  }),{valid:false,id:'B3',priorTurn:1179});
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
