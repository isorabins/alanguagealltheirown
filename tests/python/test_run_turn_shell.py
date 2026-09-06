"""The real shell's commit seam preserves only loop-owned generated state."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).parents[2]


class ShellCommitTests(unittest.TestCase):
    def test_consumed_notice_deletion_is_committed_and_foreign_index_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            def git(*args):
                return subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True, text=True).stdout
            git('init', '-q')
            git('config', 'user.name', 'test')
            git('config', 'user.email', 'test@example.com')
            (repo/'state').mkdir()
            (repo/'state/conversation.json').write_text('[{"turn":1}]')
            (repo/'state/pending-notice.txt').write_text('notice')
            (repo/'foreign.txt').write_text('original')
            git('add', '-A'); git('commit', '-qm', 'baseline')
            (repo/'state/pending-notice.txt').unlink()
            (repo/'state/conversation.json').write_text('[{"turn":2}]')
            (repo/'foreign.txt').write_text('user work')
            git('add', 'foreign.txt')
            helper = (ROOT/'run_turn.sh').read_text().split('main() {')[0] + '\nrecord_turn\n'
            subprocess.run(['bash', '-c', helper], cwd=repo, check=True)
            changed = git('diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD').splitlines()
            self.assertEqual(changed, ['state/conversation.json', 'state/pending-notice.txt'])
            self.assertEqual(git('diff', '--cached', '--name-only').strip(), 'foreign.txt')
            self.assertEqual(git('show', 'HEAD:foreign.txt'), 'original')
            self.assertFalse(git('diff', '--name-only', '--', 'state'))
