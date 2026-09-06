"""Resume cleanup's exact completed requests under the existing turn writer lock.

Only a source/edition-scoped cleanup uses this cache. Paid transport owns charge
reservations; TurnStore owns adoption. An interrupted call without a response
remains subject to the transport's uncertain-charge stop, never assumed free.
"""
import copy
from pathlib import Path
from state_store import atomic_write_json, load_json, snapshot_hash


class CleanupReplay:
    def __init__(self, directory, *, account):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.account = account
        self.occurrences = {}

    def call(self, provider):
        def invoke(*args, **kwargs):
            request = {'args': args, 'kwargs': {k: v for k, v in kwargs.items() if k != 'meta'}}
            identity = snapshot_hash(request)
            occurrence = self.occurrences.get(identity, 0)
            self.occurrences[identity] = occurrence + 1
            path = self.directory / f'{identity}-{occurrence}.json'
            saved = load_json(path, None)
            if saved is not None:
                if saved['request_hash'] != snapshot_hash(request):
                    raise ValueError('cleanup replay identity mismatch')
                text, usage = copy.deepcopy(saved['result'])
                if usage.get('response_receipt', {}).get('finish_reason') != 'stop':
                    raise ValueError('cleanup replay requires a complete response')
                self.account(kwargs.get('meta'), usage)
                usage['replayed'] = True
                return text, usage
            result = provider(*args, **kwargs)
            if result[1].get('response_receipt', {}).get('finish_reason') == 'stop':
                atomic_write_json(path, {'request_hash': snapshot_hash(request), 'result': result})
            return result
        return invoke

    def tokens(self, counter):
        def count(text, meta):
            path = self.directory / ('tokens-' + snapshot_hash(text) + '.json')
            saved = load_json(path, None)
            if saved is not None:
                return saved['tokens']
            result = counter(text, meta)
            atomic_write_json(path, {'tokens': result})
            return result
        return count
