import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from codex_compactor import CodexCompactor, CodexCompletionError


class CodexCompactorTests(unittest.TestCase):
    def run_fake(self, *, terminal=True, failed=False, raw='{"groups": []}', timeout=False):
        with tempfile.TemporaryDirectory() as directory:
            def run(command,**kwargs):
                self.assertIn('--output-schema',command)
                self.assertIn('--ignore-user-config',command)
                self.assertIn('--ephemeral',command)
                self.assertEqual(command[command.index('--sandbox')+1],'read-only')
                self.assertNotIn('OPENAI_API_KEY',kwargs['env'])
                self.assertNotIn('OPENROUTER_API_KEY',kwargs['env'])
                self.assertIn('source data',kwargs['input'])
                if timeout: raise subprocess.TimeoutExpired(command,1)
                Path(command[command.index('--output-last-message')+1]).write_text(raw)
                events=[{'type':'thread.started','thread_id':'test-thread'}]
                if terminal: events.append({'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':5}})
                return SimpleNamespace(returncode=1 if failed else 0,
                    stdout='\n'.join(map(json.dumps,events)),stderr='')
            with patch.dict('os.environ',{'OPENAI_API_KEY':'fake-key','OPENROUTER_API_KEY':'fake-key'}):
                adapter=CodexCompactor(Path(directory),run=run)
                return adapter('gpt-6-astra','Return an object','source data',request_options={
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
