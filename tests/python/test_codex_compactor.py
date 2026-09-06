import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from codex_compactor import CodexCompactor, CodexCompletionError


class CodexCompactorTests(unittest.TestCase):
    def run_fake(self, *, terminal=True, failed=False, raw='{"groups": []}', timeout=False, large=False, text_mode=False):
        with tempfile.TemporaryDirectory() as directory:
            def run(command,**kwargs):
                self.assertEqual('--output-schema' in command, not text_mode)
                self.assertIn('--ignore-user-config',command)
                self.assertIn('--ephemeral',command)
                self.assertEqual(command[command.index('--sandbox')+1],'read-only')
                self.assertNotIn('OPENAI_API_KEY',kwargs['env'])
                self.assertNotIn('OPENROUTER_API_KEY',kwargs['env'])
                if large:
                    self.assertLess(len(kwargs['input']),900000)
                    self.assertEqual((Path(kwargs['cwd'])/'input-data.json').read_text(),'source data '*100000)
                    self.assertIn('inspect every source record',kwargs['input'])
                else:
                    self.assertIn('source data',kwargs['input'])
                if timeout: raise subprocess.TimeoutExpired(command,1)
                Path(command[command.index('--output-last-message')+1]).write_text(raw)
                events=[{'type':'thread.started','thread_id':'test-thread'}]
                if terminal: events.append({'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':5}})
                kwargs['stdout'].write('\n'.join(map(json.dumps,events)))
                kwargs['stdout'].flush()
                return SimpleNamespace(returncode=1 if failed else 0)
            with patch.dict('os.environ',{'OPENAI_API_KEY':'fake-key','OPENROUTER_API_KEY':'fake-key'}):
                adapter=CodexCompactor(Path(directory),run=run)
                return adapter('gpt-6-astra','Return an object','source data '*100000 if large else 'source data',request_options=None if text_mode else {
                    'response_format':{'json_schema':{'schema':{'type':'object'}}}})

    def test_complete_response_uses_subscription_and_schema(self):
        raw,usage=self.run_fake()
        self.assertEqual(json.loads(raw),{'groups':[]})
        self.assertEqual(usage['billing'],'codex_subscription')
        self.assertEqual(usage['api_dollars_charged'],0)
        self.assertEqual(usage['subscription_usage']['input_tokens'],10)

    def test_failures_never_return_partial_success(self):
        for options in ({'terminal':False},{'failed':True},{'raw':'{"partial"'},
                        {'raw':'[]'},{'timeout':True}):
            with self.subTest(options=options),self.assertRaises(CodexCompletionError):
                self.run_fake(**options)

    def test_large_source_is_preserved_in_workspace_input_not_truncated(self):
        raw,usage=self.run_fake(large=True)
        self.assertEqual(json.loads(raw),{'groups':[]})
        self.assertEqual(usage['billing'],'codex_subscription')

    def test_saved_response_replay_requires_identical_request_and_complete_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);saved=base/'saved';saved.mkdir()
            schema={'type':'object'}
            request={'model':'gpt-6-astra','reasoning':'medium','system':'s','user':'u','schema':schema}
            (saved/'request.json').write_text(json.dumps(request))
            (saved/'response.json').write_text('{"groups":[]}')
            (saved/'usage.json').write_text(json.dumps({'cost':0,'billing':'codex_subscription',
                'response_receipt':{'id':'original','finish_reason':'stop'}}))
            def no_call(*args,**kwargs): raise AssertionError('unexpected provider call')
            options={'response_format':{'json_schema':{'schema':schema}}}
            a=CodexCompactor(base/'out',replay_first=saved,run=no_call)
            raw,usage=a('gpt-6-astra','s','u',request_options=options)
            self.assertFalse(usage['new_subscription_usage'])
            self.assertEqual(usage['response_receipt']['id'],'original')
            b=CodexCompactor(base/'other',replay_first=saved,run=no_call)
            with self.assertRaisesRegex(CodexCompletionError,'different request'):
                b('gpt-6-astra','s','changed source',request_options=options)

    def test_plain_encoding_response_uses_subscription_without_json_coercion(self):
        raw,usage=self.run_fake(raw='Send by 5 PM.',text_mode=True)
        self.assertEqual(raw,'Send by 5 PM.')
        self.assertEqual(usage['billing'],'codex_subscription')


class CodexLegislativeSchemaTests(unittest.TestCase):
    def test_real_motion_schemas_use_disjoint_supported_unions(self):
        from codex_compactor import codex_wire_schema
        from legislative_protocol import action_request_options,validate_action
        from test_legislative_protocol import adopted_book,open_add_book
        for role,book in [('A',adopted_book()),('B',open_add_book())]:
            original=action_request_options(role,book)['response_format']['json_schema']['schema']
            saved=json.dumps(original,sort_keys=True)
            projected=codex_wire_schema(original)
            self.assertEqual(json.dumps(original,sort_keys=True),saved)
            self.assertNotIn('"oneOf"',json.dumps(projected))
            self.assertNotIn('"discriminator"',json.dumps(projected))
            self.assertNotIn('"default"',json.dumps(projected))
            def required(node):
                if isinstance(node,dict):
                    if node.get('type')=='object':
                        self.assertEqual(set(node['required']),set(node['properties']))
                        self.assertIs(node['additionalProperties'],False)
                    for v in node.values():required(v)
                elif isinstance(node,list):
                    for v in node:required(v)
            required(projected)
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            validate_action({'deliberation':'Public proposal: Invalid target','motion':{'kind':'REPEAL','target_rule_id':'missing','rationale':'A real explanation'},'measurements':[],'requests':[]},'A',adopted_book())

    def test_overlapping_or_untagged_unions_fail_closed(self):
        from codex_compactor import codex_wire_schema
        branch={'type':'object','properties':{'kind':{'const':'SAME'}},'required':['kind']}
        for schema in [{'oneOf':[{'type':'string'},{'type':'string'}]}, {'oneOf':[branch,branch],'discriminator':{'propertyName':'kind'}}]:
            with self.assertRaises(CodexCompletionError):codex_wire_schema(schema)
