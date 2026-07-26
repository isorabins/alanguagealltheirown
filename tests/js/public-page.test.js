const test=require('node:test'); const assert=require('node:assert/strict'); const fs=require('node:fs'); const path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../../viewer/index.html'),'utf8');

test('public page has mobile disclosure and suggestion placement',()=>{
  assert.match(html,/@media\s*\(max-width:\s*760px\)/); assert.match(html,/id="suggestion-form"/);
  assert.ok(html.indexOf('id="suggestion-form"')>html.indexOf('class="panes"'));
  assert.ok(html.indexOf('id="suggestion-form"')<html.indexOf('id="decisions"'));
  assert.match(html,/<details class="sect">/); assert.match(html,/Full transcript/);
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
  assert.match(html,/stale proposal-state deadlock/);
  assert.match(html,/Lab notebook · research, methods &amp; archive/);
  assert.match(html,/function conversationJudgmentHtml/);
  assert.match(html,/raw judgment evidence/);
  assert.doesNotMatch(html,/<div class="judg"><div class="jhead">concrete-outcome judgment<\/div><pre>/);
  assert.match(html,/id="current-proposal"/);
  assert.match(html,/earlier unresolved record/);
});

test('public page contains overflow and keyboard-focus safeguards',()=>{
  assert.match(html,/pre\s*\{[^}]*max-width:\s*100%[^}]*white-space:\s*pre-wrap[^}]*overflow-wrap:\s*anywhere/s);
  assert.match(html,/:focus-visible\s*\{[^}]*outline:\s*2px solid var\(--accent\)/s);
  assert.match(html,/body\s*\{[^}]*width:\s*min\(1100px,\s*100%\)/s);
});
