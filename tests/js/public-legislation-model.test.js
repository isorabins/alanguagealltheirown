const test = require('node:test');
const assert = require('node:assert/strict');
const P = require('../../viewer/public-legislation.js');

function model(hash='a'.repeat(64)) {
  return {
    schema_version: 1,
    mode: 'shadow',
    legislation_identity: {version:'adopted-'+hash.slice(0,12),hash},
    adopted_language: {rules:[{id:'rule-001',text_en:'Use !ok.'}]},
    complete_legislature: [{id:'rule-001',status:'adopted',text_en:'Use !ok.'}],
    complete_legislature_identity: 'legislature-1',
    roles: {agent_a:'proposer',agent_b:'mandatory_auditor',agent_c:'evidence_guided_editor',authority:'rule_legislation_module'},
    classifications: {'rule-001':'unknown'},
    budget: {mode:'shadow',monthly_ceiling_usd:'30.00',available_usd:'30.00'},
    runtime_status: {status:'paused',turn:10,legislation_identity:{version:'adopted-'+hash.slice(0,12),hash}},
  };
}

test('one module public model supplies current language, legislature, roles, and budget',()=>{
  const assembled=P.assemble({publicModel:model(),conversation:[],collaboration:{},conversations:[],notes:[]});
  assert.equal(assembled.status,'current');
  assert.equal(assembled.state.rulebook.rules[0].status,'adopted');
  assert.equal(assembled.state.language.hash,'a'.repeat(64));
  assert.equal(assembled.state.legislation.roles.authority,'rule_legislation_module');
  assert.equal(assembled.state.legislation.budget.monthly_ceiling_usd,'30.00');
});

test('runtime or fallback identity mismatch is stale and never merged as current',()=>{
  const mismatchedRuntime=model();
  mismatchedRuntime.runtime_status.legislation_identity.hash='b'.repeat(64);
  assert.equal(P.assemble({publicModel:mismatchedRuntime}).status,'stale_unavailable');
  assert.equal(P.assemble({publicModel:mismatchedRuntime}).state,null);

  const fallback=model();
  const result=P.assemble({publicModel:model(),fallbackModel:fallback});
  assert.equal(result.status,'current');
  fallback.legislation_identity.hash='c'.repeat(64);
  const mismatch=P.assemble({publicModel:null,fallbackModel:fallback,expectedIdentity:model().legislation_identity});
  assert.equal(mismatch.status,'stale_unavailable');
  assert.equal(mismatch.state,null);
});

test('client never derives classifications from rule records',()=>{
  const source=require('node:fs').readFileSync(require('node:path').join(__dirname,'../../viewer/public-legislation.js'),'utf8');
  assert.doesNotMatch(source,/scores|fidelity|classif\w*\s*=/i);
});

test('viewer refuses legacy state without a module-generated public model',()=>{
  const html=fs.readFileSync(path.join(__dirname,'../../viewer/index.html'),'utf8');
  assert.doesNotMatch(html,/if\(candidate\)\{render\(candidate\);return true;\}/);
  assert.match(html,/snapshot has no module-generated legislation model/i);
});

test('public copy names A proposer, B auditor, C evidence editor, and module authority',()=>{
  const html=require('node:fs').readFileSync(require('node:path').join(__dirname,'../../viewer/index.html'),'utf8');
  assert.match(html,/Agent A visibly proposes/);
  assert.match(html,/Agent B must audit every A or C candidate/);
  assert.match(html,/evidence-linked Agent C candidate/);
  assert.match(html,/rule-legislation module alone applies the exact tested artifact/);
  assert.doesNotMatch(html,/B audits[^.]*alone may adopt|only one of them gets the vote/i);
});
