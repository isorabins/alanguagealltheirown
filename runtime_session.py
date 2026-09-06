"""Bound one live operating session to Astra, a deadline and a durable API cap.

Configuration is local operator data, never a secret. Install under the normal
TurnStore writer lock so separate scheduled turns share one reservation ledger.
No configuration means the historical runner remains unchanged.
"""
from datetime import datetime, timezone
import json
import shutil
import uuid
from pathlib import Path

from codex_compactor import CodexCompactor
from local_cleanup import ReservedTransport, LocalBudgetError


class RuntimeSession:
    def __init__(self, config_path, *, now=None, post=None, compactor=None):
        config = json.loads(Path(config_path).read_text())
        self.expires = datetime.fromisoformat(config['expires_at'])
        if self.expires.tzinfo is None:
            raise ValueError('runtime deadline must include a timezone')
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.evidence = Path(config['codex_evidence']).parent / 'cleanup-evidence'
        options = {} if post is None else {'post': post}
        self.transport = ReservedTransport(config['limit_usd'], config['models'],
            Path(config['ledger']), max_output_tokens=6000, **options)
        self.compactor = compactor or CodexCompactor(Path(config['codex_evidence']),
            executable=config['codex'], reasoning='medium')

    def check(self):
        if self.now() >= self.expires:
            raise LocalBudgetError('approved live session has expired')
        if self.transport.stopped or self.transport.used >= self.transport.limit:
            raise LocalBudgetError('approved live session budget is exhausted or uncertain')

    def post(self, url, **kwargs):
        self.check()
        # Tool fees are outside this text-model reservation. Refuse before any
        # dispatch; the existing research failure path retains a failed receipt.
        body = kwargs.get('json', {})
        if any(key in body for key in ('tools', 'plugins', 'audio', 'images')):
            raise LocalBudgetError('auxiliary service fees are outside this session budget')
        return self.transport(url, **kwargs)

    def compact(self, *args, **kwargs):
        self.check()
        return self.compactor(*args, **kwargs)

    def retain_cleanup(self, output):
        """Preserve the complete admission record before temporary work is removed."""
        destination = self.evidence / uuid.uuid4().hex
        self.evidence.mkdir(parents=True, exist_ok=True)
        shutil.copytree(output, destination)
        return str(destination)
