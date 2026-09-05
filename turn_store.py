"""One durable turn across the existing canonical JSON files.

The single writer stages a checksummed redo record before replacing any canonical
file. An interrupted commit is completed before state is returned to the runner.
Provider charges remain in their independent receipt ledger; this module does not
promise to undo or deduplicate model calls made before a turn was prepared.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
from typing import Any, Iterator

from state_store import atomic_write_json, load_json, snapshot_hash


class TurnRecoveryError(RuntimeError):
    """Pending work cannot be trusted; leave it intact and stop the writer."""


@dataclass
class TurnState:
    """Working experiment plus its last validated terminal trace.

    ``consumed_notice`` is exact inbox text to acknowledge only on commit;
    load leaves it unset. The completed trace is durable locally and its public
    file is rebuildable, so optional publication failure cannot cancel a turn.
    """
    conversation: list[dict[str, Any]]
    rulebook: dict[str, Any]
    meta: dict[str, Any]
    collaboration: dict[str, Any]
    conversations: list[dict[str, Any]]
    public_exam_progress: dict[str, Any] | None = None
    consumed_notice: str | None = None

    @property
    def next_turn(self) -> int:
        return self.conversation[-1]["turn"] + 1 if self.conversation else 1


_FILES = {
    "conversation.json": "conversation",
    "rulebook.json": "rulebook",
    "meta.json": "meta",
    "collaboration.json": "collaboration",
    "conversations.json": "conversations",
}


class TurnStore:
    """Load and commit complete turns during one exclusive writer session.

    Use ``with store.writer():`` across load, model work and commit. A failed
    commit is indeterminate until the next load replays its prepared record.
    Public page projections are derived; the completed exam trace travels with
    the canonical turn so publication cannot lose the result on interruption.
    """

    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.pending = self.directory / "turn-commit.local.json"
        self._locked = False
        self.recovered = False

    @contextmanager
    def writer(self) -> Iterator[TurnStore]:
        self.directory.mkdir(parents=True, exist_ok=True)
        with (self.directory / "turn-writer.local.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise TurnRecoveryError("another turn writer is active") from error
            self._locked = True
            try:
                yield self
            finally:
                self._locked = False
                fcntl.flock(lock, fcntl.LOCK_UN)

    def _require_writer(self) -> None:
        if not self._locked:
            raise TurnRecoveryError("load and commit require an exclusive writer")

    def _materialize(self, files: dict[str, Any]) -> None:
        for name, value in files.items():
            path = self.directory / name
            if name == "pending-notice.txt":
                # Different replacement notice content must not be acknowledged.
                if path.exists() and path.read_text() == value:
                    path.unlink()
            else:
                atomic_write_json(path, value)
        # Persist notice acknowledgments before forgetting the redo record.
        self._sync_directory()
        self.pending.unlink()
        self._sync_directory()

    def _sync_directory(self) -> None:
        fd = os.open(self.directory, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _recover(self) -> None:
        if not self.pending.exists():
            return
        try:
            record = load_json(self.pending, None)
        except (ValueError, OSError) as error:
            raise TurnRecoveryError("unreadable pending turn; recovery stopped") from error
        if (not isinstance(record, dict) or record.get("schema_version") != 1
                or not isinstance(record.get("files"), dict)
                or not set(_FILES).issubset(record["files"])
                or not set(record["files"]).issubset(set(_FILES) | {"public-exam-completed.local.json", "pending-notice.txt"})
                or record.get("hash") != snapshot_hash(record["files"])):
            raise TurnRecoveryError("invalid pending turn; recovery stopped")
        self._materialize(record["files"])
        self.recovered = True

    def load(self, defaults: TurnState) -> TurnState:
        """Recover prepared work, otherwise adopt existing JSON without rewriting it."""
        self._require_writer()
        self._recover()
        # A missing or malformed legacy optional trace must not stop the experiment.
        from public_exam_progress import validate_snapshot
        try:
            trace_path = self.directory / "public-exam-completed.local.json"
            if not trace_path.exists():
                trace_path = self.directory / "public-exam-progress.json"
            progress = validate_snapshot(load_json(trace_path, None))
            if progress["phase"] != "completed":
                progress = None
        except (ValueError, OSError):
            progress = None
        return TurnState(public_exam_progress=progress, **{
            field: load_json(self.directory / name, getattr(defaults, field))
            for name, field in _FILES.items()
        })

    def commit(self, state: TurnState) -> None:
        """Prepare a complete turn and its terminal public exam, then recoverably save."""
        self._require_writer()
        if self.pending.exists():
            raise TurnRecoveryError("recover the pending turn before committing")
        files = {name: getattr(state, field) for name, field in _FILES.items()}
        if state.public_exam_progress is not None:
            from public_exam_progress import validate_snapshot
            progress = validate_snapshot(state.public_exam_progress)
            if progress["phase"] != "completed":
                raise TurnRecoveryError("only completed public exam evidence can be committed")
            files["public-exam-completed.local.json"] = progress
        if state.consumed_notice is not None:
            files["pending-notice.txt"] = state.consumed_notice
        atomic_write_json(self.pending, {
            "schema_version": 1, "files": files, "hash": snapshot_hash(files),
        })
        self._materialize(files)
