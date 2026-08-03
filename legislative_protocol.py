"""Typed legislative transport, state-specific schemas, and authoritative receipts."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from functools import reduce
from operator import or_
from typing import Annotated, Any, Literal, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    create_model,
    field_validator,
    model_validator,
)

from rulebook import language_payload
from state_store import snapshot_hash

PROTOCOL_VERSION = "structured-legislature-v1"
MAX_STRUCTURAL_RETRIES = 2
SEMANTIC_FAULT_CUTOVER_TURN = 1506
MAX_SEMANTIC_FAULT_PROMPT_CHARS = 500

Role = Literal["A", "B"]
ActionResultKind = Literal["accepted", "rejected", "structural_failure", "cutover"]
FaultLifecycle = Literal[
    "UNRESOLVED", "REPAIR_PROPOSED", "PENDING_RETEST", "RESOLVED"
]
FailureClass = Literal[
    "OPAQUE_IDENTIFIER",
    "QUANTIFIED_BUNDLE",
    "MEASURED_VALUE",
    "TEMPORAL_CONSTRAINT",
    "EXACT_LABEL",
    "SEMANTIC_RELATIONSHIP",
]
Deliberation = Annotated[
    str,
    Field(
        min_length=12,
        max_length=4000,
        pattern=r"[A-Za-z0-9]",
        description=(
            "Required concise public-facing summary, not private reasoning. "
            "State your conclusion about the current turn in at least 12 "
            "characters including a letter or digit; never leave this field "
            "empty or punctuation-only."
        ),
    ),
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class MeasurementRequest(StrictModel):
    text: str = Field(min_length=1, max_length=500)


class CollaborationRequest(StrictModel):
    kind: Literal["LOOKUP", "RESEARCH", "ASK"]
    question: str = Field(min_length=1, max_length=500)


class ProposeMotion(StrictModel):
    kind: Literal["PROPOSE"]
    text: str = Field(min_length=12, max_length=4000)


class RepealMotion(StrictModel):
    kind: Literal["REPEAL"]
    target_rule_id: str
    rationale: str = Field(min_length=12, max_length=1000)


class ReviseMotion(StrictModel):
    kind: Literal["REVISE"]
    target_rule_id: str
    text: str = Field(min_length=12, max_length=4000)


class AdoptMotion(StrictModel):
    kind: Literal["ADOPT"]
    target_rule_id: str


class RejectMotion(StrictModel):
    kind: Literal["REJECT"]
    target_rule_id: str


class RequestMotion(StrictModel):
    kind: Literal["REQUEST"]
    target_rule_id: str
    focus: str = Field(min_length=12, max_length=1000)


class FaultResponse(StrictModel):
    """Typed proof that Agent A associated one proposal with one private fault."""

    status: Literal["REPAIR_PROPOSED"]
    fault_token: str = Field(min_length=16, max_length=40, pattern=r"fault-[0-9a-f]+")


RecordedMotion = Annotated[
    Union[
        ProposeMotion,
        RepealMotion,
        ReviseMotion,
        AdoptMotion,
        RejectMotion,
        RequestMotion,
    ],
    Field(discriminator="kind"),
]


class LegislativeAction(StrictModel):
    deliberation: Deliberation
    motion: RecordedMotion | None
    fault_response: FaultResponse | None = None
    measurements: list[MeasurementRequest] = Field(max_length=2)
    requests: list[CollaborationRequest] = Field(max_length=3)

    @field_validator("requests")
    @classmethod
    def requests_have_unique_kinds(
        cls, requests: list[CollaborationRequest]
    ) -> list[CollaborationRequest]:
        kinds = [request.kind for request in requests]
        if len(kinds) != len(set(kinds)):
            raise ValueError("at most one LOOKUP, RESEARCH, and ASK request is allowed")
        return requests


class RecordedLegislativeAction(StrictModel):
    """Immutable receipt payload, decoupled from the current input policy."""

    deliberation: str = Field(max_length=4000)
    motion: RecordedMotion | None
    # Historical structured receipts predate semantic-fault attention.
    fault_response: FaultResponse | None = None
    measurements: list[MeasurementRequest] = Field(max_length=2)
    requests: list[CollaborationRequest] = Field(max_length=3)


class OpenMotionState(StrictModel):
    kind: Literal["add", "repeal"]
    target_rule_id: str
    proposed_turn: int


class ActiveLegislativeFeedback(StrictModel):
    """The one unresolved typed request projected for the current motion."""

    kind: Literal["REQUEST"] = "REQUEST"
    target_rule_id: str
    focus: str = Field(min_length=12, max_length=1000)
    request_turn: int = Field(ge=0)


class SemanticFaultEvidence(StrictModel):
    """Exact audit evidence retained only in the internal event projection."""

    exam_turn: int = Field(ge=SEMANTIC_FAULT_CUTOVER_TURN)
    benchmark_id: str = Field(min_length=1, max_length=32)
    benchmark_version: Literal["v2"]
    scoring_version: Literal["v2"]
    atom_id: str = Field(min_length=1, max_length=80)
    classification: Literal["MISSING", "CORRUPTED"]
    expected_meaning: str = Field(min_length=1, max_length=500)
    required_literals: list[str] = Field(default_factory=list, max_length=30)
    decoded_evidence: str
    original: str
    encoded: str
    decoded: str
    language_version: str = Field(min_length=1, max_length=80)
    language_hash: str = Field(min_length=64, max_length=64)

    @model_validator(mode="after")
    def evidence_matches_classification(self) -> "SemanticFaultEvidence":
        if self.classification == "MISSING" and self.decoded_evidence:
            raise ValueError("missing fault evidence cannot carry decoded evidence")
        if self.classification == "CORRUPTED" and not self.decoded_evidence:
            raise ValueError("corrupted fault evidence requires decoded evidence")
        return self


class SemanticFaultLedgerEntry(StrictModel):
    """One event-sourced critical semantic fault and its honest lifecycle."""

    source_identity: str = Field(min_length=1, max_length=200)
    fault_token: str = Field(min_length=16, max_length=40, pattern=r"fault-[0-9a-f]+")
    first_failure_turn: int = Field(ge=SEMANTIC_FAULT_CUTOVER_TURN)
    last_failure_turn: int = Field(ge=SEMANTIC_FAULT_CUTOVER_TURN)
    classification: Literal["MISSING", "CORRUPTED"]
    failure_class: FailureClass
    invariant: str = Field(min_length=12, max_length=240)
    status: FaultLifecycle
    linked_motion_rule_id: str | None = None
    repair_proposed_turn: int | None = Field(default=None, ge=0)
    adoption_turn: int | None = Field(default=None, ge=0)
    resolved_turn: int | None = Field(default=None, ge=0)
    latest_source: SemanticFaultEvidence


class SemanticFaultFeedback(StrictModel):
    """The only semantic-fault data allowed into a model request."""

    fault_token: str = Field(min_length=16, max_length=40, pattern=r"fault-[0-9a-f]+")
    status: Literal["UNRESOLVED", "REPAIR_PROPOSED"]
    classification: Literal["MISSING", "CORRUPTED"]
    failure_class: FailureClass
    invariant: str = Field(min_length=12, max_length=240)

    @model_validator(mode="after")
    def serialized_receipt_is_bounded(self) -> "SemanticFaultFeedback":
        serialized = json.dumps(self.model_dump(mode="json"), separators=(",", ":"))
        if len(serialized) > MAX_SEMANTIC_FAULT_PROMPT_CHARS:
            raise ValueError("semantic fault prompt receipt exceeds its explicit bound")
        return self


class RuleState(StrictModel):
    rule_id: str
    status: str
    pending_repeal: bool


class CanonicalLegislativeState(StrictModel):
    authoritative: Literal[True] = True
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    next_actor: Role
    rulebook_version: str
    rulebook_changes: int
    rulebook_hash: str
    rule_states: list[RuleState]
    open_motion: OpenMotionState | None
    adopted_count: int
    adopted_language_hash: str


class ActionResult(StrictModel):
    result: ActionResultKind
    reason: str = Field(min_length=1, max_length=500)
    attempts: int = Field(ge=0, le=MAX_STRUCTURAL_RETRIES + 1)
    action: LegislativeAction | None


class PostStateReceipt(StrictModel):
    authoritative: Literal[True] = True
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    turn: int = Field(ge=0)
    actor: Role | Literal["harness"]
    attempted_action: RecordedLegislativeAction | None
    result: ActionResultKind
    reason: str = Field(min_length=1, max_length=500)
    attempts: int = Field(ge=0, le=MAX_STRUCTURAL_RETRIES + 1)
    changed_rule_ids: list[str]
    unchanged_rule_ids: list[str]
    current_open_motion: OpenMotionState | None
    adopted_count: int = Field(ge=0)
    adopted_language_hash: str = Field(min_length=64, max_length=64)
    rulebook_version: str
    rulebook_changes: int = Field(ge=0)
    rulebook_hash: str = Field(min_length=64, max_length=64)
    next_actor: Role


class LegislativeRequest(StrictModel):
    authoritative: Literal[True] = True
    protocol_version: Literal[PROTOCOL_VERSION] = PROTOCOL_VERSION
    turn: int = Field(ge=1)
    acting_role: Role
    next_live_test_turn: int = Field(ge=1)
    current_state: CanonicalLegislativeState
    latest_receipt: PostStateReceipt | None
    active_legislative_feedback: ActiveLegislativeFeedback | None
    semantic_fault_feedback: SemanticFaultFeedback | None
    collaboration_input: dict[str, Any] | None


class _ActionEnvelopeBase(LegislativeAction):
    motion: Any


def current_open_motion(rulebook: dict[str, Any]) -> OpenMotionState | None:
    """Return the one canonical open motion, failing closed on state divergence."""
    open_motions: list[OpenMotionState] = []
    for rule in rulebook.get("rules", []):
        if rule.get("status") == "proposed":
            open_motions.append(
                OpenMotionState(
                    kind="add",
                    target_rule_id=str(rule["id"]),
                    proposed_turn=int(rule.get("proposed_turn", -1)),
                )
            )
        pending = rule.get("pending_repeal")
        if isinstance(pending, dict):
            open_motions.append(
                OpenMotionState(
                    kind="repeal",
                    target_rule_id=str(rule["id"]),
                    proposed_turn=int(pending.get("proposed_turn", -1)),
                )
            )
    if len(open_motions) > 1:
        raise ValueError("structured protocol requires at most one open motion")
    return open_motions[0] if open_motions else None


def _literal(values: list[str]) -> Any:
    if not values:
        raise ValueError("cannot build an empty target literal")
    return Literal.__getitem__(tuple(values))


def _targeted_motion(base: type[StrictModel], target_ids: list[str]) -> type[StrictModel]:
    suffix = "_".join(rule_id.replace("-", "_") for rule_id in target_ids)
    return create_model(
        f"{base.__name__}_{suffix}",
        __base__=base,
        target_rule_id=(_literal(target_ids), ...),
    )


def _targeted_fault_response(fault_token: str) -> type[StrictModel]:
    token_suffix = fault_token.removeprefix("fault-")
    return create_model(
        f"FaultResponse_{token_suffix}",
        __base__=FaultResponse,
        fault_token=(Literal.__getitem__((fault_token,)), ...),
    )


def _motion_union(
    motion_types: list[type[StrictModel]], *, allow_none: bool
) -> Any:
    if not motion_types:
        return type(None)
    if len(motion_types) == 1:
        union_type = motion_types[0]
    else:
        union_type = Annotated[
            reduce(or_, motion_types), Field(discriminator="kind")
        ]
    return union_type | None if allow_none else union_type


def state_specific_action_model(
    role: Role,
    rulebook: dict[str, Any],
    *,
    required_fault_token: str | None = None,
) -> type[_ActionEnvelopeBase]:
    """Create the Pydantic action model authorized by the current role and state."""
    open_motion = current_open_motion(rulebook)
    if required_fault_token is not None and (role != "A" or open_motion is not None):
        raise ValueError("a fault response is required only for eligible Agent A state")
    motion_types: list[type[StrictModel]]
    state_name: str
    if role == "A":
        if open_motion:
            motion_types = [
                _targeted_motion(ReviseMotion, [open_motion.target_rule_id])
            ]
            state_name = f"open_{open_motion.target_rule_id}"
        else:
            adopted_ids = [
                str(rule["id"])
                for rule in rulebook.get("rules", [])
                if rule.get("status") == "adopted"
            ]
            motion_types = [ProposeMotion]
            if adopted_ids and required_fault_token is None:
                motion_types.append(_targeted_motion(RepealMotion, adopted_ids))
            state_name = (
                f"fault_{required_fault_token.removeprefix('fault-')}"
                if required_fault_token is not None
                else "no_open_motion"
            )
    elif role == "B":
        if open_motion:
            target_ids = [open_motion.target_rule_id]
            motion_types = [
                _targeted_motion(AdoptMotion, target_ids),
                _targeted_motion(RejectMotion, target_ids),
                _targeted_motion(RequestMotion, target_ids),
            ]
            state_name = f"open_{open_motion.target_rule_id}"
        else:
            motion_types = []
            state_name = "no_open_motion"
    else:
        raise ValueError(f"unknown legislative role: {role}")

    return create_model(
        f"LegislativeAction_{role}_{state_name.replace('-', '_')}",
        __base__=_ActionEnvelopeBase,
        motion=(
            _motion_union(
                motion_types,
                allow_none=not (
                    (role == "B" and open_motion is not None)
                    or required_fault_token is not None
                ),
            ),
            ...,
        ),
        fault_response=(
            _targeted_fault_response(required_fault_token), ...
        )
        if required_fault_token is not None
        else (type(None), None),
    )


def validate_action(
    payload: str | bytes | dict[str, Any],
    role: Role,
    rulebook: dict[str, Any],
    *,
    required_fault_token: str | None = None,
) -> _ActionEnvelopeBase:
    """Strictly validate provider output against the current state-specific model."""
    model = state_specific_action_model(
        role, rulebook, required_fault_token=required_fault_token
    )
    if isinstance(payload, (str, bytes)):
        return model.model_validate_json(payload, strict=True)
    return model.model_validate(payload, strict=True)


def _deterministic_deliberation(
    role: Role, action: _ActionEnvelopeBase
) -> str:
    """Render a public conclusion from an already-validated typed action."""
    motion = action.motion
    if role == "B":
        if motion is None:
            return "Public audit: Agent B recorded no legislative motion this turn."
        target = motion.target_rule_id
        if motion.kind == "ADOPT":
            return (
                f"Public audit: Agent B adopted {target} after validating "
                "the typed motion."
            )
        if motion.kind == "REJECT":
            return (
                f"Public audit: Agent B rejected {target} after validating "
                "the typed motion."
            )
        return f"Public audit: Agent B requested focused work on {target}."

    if motion is None:
        return "Public proposal: Agent A recorded no legislative motion this turn."
    if motion.kind == "PROPOSE":
        return "Public proposal: Agent A submitted one focused rule for audit."
    if motion.kind == "REPEAL":
        return (
            f"Public proposal: Agent A proposed repealing "
            f"{motion.target_rule_id} for audit."
        )
    return (
        f"Public proposal: Agent A revised {motion.target_rule_id} "
        "for another audit."
    )


def validate_action_with_deliberation_fallback(
    payload: str | bytes | dict[str, Any],
    role: Role,
    rulebook: dict[str, Any],
    *,
    required_fault_token: str | None = None,
) -> tuple[_ActionEnvelopeBase, dict[str, Any] | None]:
    """Repair only a missing or malformed public deliberation field.

    The provider's motion, measurements, requests, and complete envelope must
    pass the unchanged state-specific validator before a deterministic public
    sentence is substituted.
    """
    try:
        return validate_action(
            payload,
            role,
            rulebook,
            required_fault_token=required_fault_token,
        ), None
    except ValidationError as original_error:
        allowed_errors = {
            "missing",
            "string_too_short",
            "string_pattern_mismatch",
        }
        errors = original_error.errors(include_url=False)
        if not errors or any(
            tuple(error.get("loc", ())) != ("deliberation",)
            or error.get("type") not in allowed_errors
            for error in errors
        ):
            raise

        if isinstance(payload, (str, bytes)):
            parsed = json.loads(payload)
        else:
            parsed = copy.deepcopy(payload)
        if not isinstance(parsed, dict):
            raise original_error

        # Prove every operative field against the strict state-specific schema
        # before replacing the invalid non-operative public sentence.
        candidate = copy.deepcopy(parsed)
        candidate["deliberation"] = "Public validation placeholder."
        validated = validate_action(
            candidate,
            role,
            rulebook,
            required_fault_token=required_fault_token,
        )
        candidate["deliberation"] = _deterministic_deliberation(role, validated)
        repaired = validate_action(
            candidate,
            role,
            rulebook,
            required_fault_token=required_fault_token,
        )
        return repaired, {
            "applied": True,
            "source": "harness_deterministic_deliberation",
            "provider_error": validation_reason(original_error),
        }


def action_request_options(
    role: Role,
    rulebook: dict[str, Any],
    *,
    required_fault_token: str | None = None,
) -> dict[str, Any]:
    """Return OpenRouter's strict JSON Schema and compatible-provider requirement."""
    model = state_specific_action_model(
        role, rulebook, required_fault_token=required_fault_token
    )
    open_motion = current_open_motion(rulebook)
    state = (
        open_motion.target_rule_id
        if open_motion
        else f"fault_{required_fault_token.removeprefix('fault-')}"
        if required_fault_token
        else "none"
    )
    return {
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": f"legislative_action_{role.lower()}_{state.replace('-', '_')}",
                "strict": True,
                "schema": model.model_json_schema(),
            },
        },
        "provider": {"require_parameters": True},
    }


def canonical_legislative_state(
    rulebook: dict[str, Any], next_actor: Role
) -> CanonicalLegislativeState:
    language = language_payload(rulebook)
    return CanonicalLegislativeState(
        next_actor=next_actor,
        rulebook_version=str(rulebook.get("version", "0.0")),
        rulebook_changes=int(rulebook.get("changes", 0)),
        rulebook_hash=snapshot_hash(rulebook),
        rule_states=[
            RuleState(
                rule_id=str(rule["id"]),
                status=str(rule.get("status", "unknown")),
                pending_repeal=isinstance(rule.get("pending_repeal"), dict),
            )
            for rule in rulebook.get("rules", [])
        ],
        open_motion=current_open_motion(rulebook),
        adopted_count=len(language["rules"]),
        adopted_language_hash=language["hash"],
    )


def prompt_receipt_projection(
    receipt: PostStateReceipt | dict[str, Any],
) -> dict[str, Any]:
    """Project a complete canonical receipt into its non-duplicative prompt view."""
    payload = (
        receipt.model_dump(mode="json")
        if isinstance(receipt, PostStateReceipt)
        else receipt
    )
    return {
        key: payload.get(key)
        for key in (
            "turn",
            "actor",
            "result",
            "reason",
            "attempts",
            "changed_rule_ids",
            "current_open_motion",
            "adopted_count",
            "adopted_language_hash",
            "rulebook_version",
            "rulebook_hash",
            "next_actor",
        )
    }


def prompt_request_projection(request: LegislativeRequest) -> dict[str, Any]:
    """Return the ephemeral model request while keeping the canonical model whole."""
    current_state = request.current_state.model_dump(
        mode="json", exclude={"rule_states"}
    )
    return {
        "authoritative": request.authoritative,
        "protocol_version": request.protocol_version,
        "turn": request.turn,
        "acting_role": request.acting_role,
        "next_live_test_turn": request.next_live_test_turn,
        "current_state": current_state,
        "latest_receipt": (
            prompt_receipt_projection(request.latest_receipt)
            if request.latest_receipt is not None
            else None
        ),
        "active_legislative_feedback": (
            request.active_legislative_feedback.model_dump(mode="json")
            if request.active_legislative_feedback is not None
            else None
        ),
        "semantic_fault_feedback": (
            request.semantic_fault_feedback.model_dump(mode="json")
            if request.semantic_fault_feedback is not None
            else None
        ),
        "collaboration_input": request.collaboration_input,
    }


def _recorded_action(
    action: BaseModel | dict[str, Any] | None
) -> RecordedLegislativeAction | None:
    if action is None:
        return None
    payload = action.model_dump(mode="json") if isinstance(action, BaseModel) else action
    return RecordedLegislativeAction.model_validate(payload, strict=True)


def _rule_changes(
    before_rulebook: dict[str, Any], after_rulebook: dict[str, Any]
) -> tuple[list[str], list[str]]:
    before = {str(rule["id"]): rule for rule in before_rulebook.get("rules", [])}
    after = {str(rule["id"]): rule for rule in after_rulebook.get("rules", [])}
    ordered_ids = list(after)
    ordered_ids.extend(rule_id for rule_id in before if rule_id not in after)
    changed = [
        rule_id for rule_id in ordered_ids if before.get(rule_id) != after.get(rule_id)
    ]
    unchanged = [rule_id for rule_id in ordered_ids if rule_id not in changed]
    return changed, unchanged


def build_post_state_receipt(
    *,
    turn: int,
    role: Role,
    action: BaseModel | dict[str, Any] | None,
    result: ActionResultKind,
    reason: str,
    before_rulebook: dict[str, Any],
    after_rulebook: dict[str, Any],
    next_actor: Role,
    attempts: int,
) -> PostStateReceipt:
    """Build the complete authoritative receipt from independently compared states."""
    changed, unchanged = _rule_changes(before_rulebook, after_rulebook)
    language = language_payload(after_rulebook)
    return PostStateReceipt(
        turn=turn,
        actor=role,
        attempted_action=_recorded_action(action),
        result=result,
        reason=reason,
        attempts=attempts,
        changed_rule_ids=changed,
        unchanged_rule_ids=unchanged,
        current_open_motion=current_open_motion(after_rulebook),
        adopted_count=len(language["rules"]),
        adopted_language_hash=language["hash"],
        rulebook_version=str(after_rulebook.get("version", "0.0")),
        rulebook_changes=int(after_rulebook.get("changes", 0)),
        rulebook_hash=snapshot_hash(after_rulebook),
        next_actor=next_actor,
    )


def build_cutover_receipt(
    rulebook: dict[str, Any], *, turn: int, next_actor: Role
) -> PostStateReceipt:
    return build_post_state_receipt(
        turn=turn,
        role="harness",
        action=None,
        result="cutover",
        reason="structured_protocol_cutover",
        before_rulebook=rulebook,
        after_rulebook=rulebook,
        next_actor=next_actor,
        attempts=0,
    )


def build_legislative_request(
    *,
    role: Role,
    turn: int,
    next_live_test_turn: int,
    rulebook: dict[str, Any],
    latest_receipt: PostStateReceipt | dict[str, Any] | None,
    collaboration_input: dict[str, Any] | None,
    active_legislative_feedback: ActiveLegislativeFeedback | dict[str, Any] | None = None,
    semantic_fault_feedback: SemanticFaultFeedback | dict[str, Any] | None = None,
) -> LegislativeRequest:
    receipt = (
        latest_receipt
        if isinstance(latest_receipt, PostStateReceipt)
        else PostStateReceipt.model_validate(latest_receipt, strict=True)
        if latest_receipt is not None
        else None
    )
    return LegislativeRequest(
        turn=turn,
        acting_role=role,
        next_live_test_turn=next_live_test_turn,
        current_state=canonical_legislative_state(rulebook, role),
        latest_receipt=receipt,
        active_legislative_feedback=(
            active_legislative_feedback
            if isinstance(active_legislative_feedback, ActiveLegislativeFeedback)
            else ActiveLegislativeFeedback.model_validate(
                active_legislative_feedback, strict=True
            )
            if active_legislative_feedback is not None
            else None
        ),
        semantic_fault_feedback=(
            semantic_fault_feedback
            if isinstance(semantic_fault_feedback, SemanticFaultFeedback)
            else SemanticFaultFeedback.model_validate(
                semantic_fault_feedback, strict=True
            )
            if semantic_fault_feedback is not None
            else None
        ),
        collaboration_input=collaboration_input,
    )


def derive_active_legislative_feedback(
    events: list[dict[str, Any]], open_motion: OpenMotionState | None
) -> ActiveLegislativeFeedback | None:
    """Derive, without consuming history, B's latest eligible request for one open motion."""
    if open_motion is None:
        return None
    for event in reversed(events):
        payload = event.get("post_state_receipt")
        if not isinstance(payload, dict):
            continue
        try:
            receipt = PostStateReceipt.model_validate(payload, strict=True)
        except ValidationError:
            continue
        action = receipt.attempted_action
        motion = action.motion if action is not None else None
        if (
            receipt.actor == "B"
            and receipt.result == "accepted"
            and receipt.reason == "focused_work_requested"
            and isinstance(motion, RequestMotion)
            and motion.target_rule_id == open_motion.target_rule_id
            and receipt.current_open_motion is not None
            and receipt.current_open_motion.target_rule_id == open_motion.target_rule_id
            and receipt.current_open_motion.kind == open_motion.kind
        ):
            return ActiveLegislativeFeedback(
                kind="REQUEST",
                target_rule_id=motion.target_rule_id,
                focus=motion.focus,
                request_turn=receipt.turn,
            )
        if (
            receipt.result == "accepted"
            and receipt.current_open_motion is not None
            and receipt.current_open_motion.target_rule_id == open_motion.target_rule_id
            and receipt.current_open_motion.kind == open_motion.kind
            and (
                (open_motion.kind == "add" and isinstance(motion, ProposeMotion))
                or (open_motion.kind == "repeal" and isinstance(motion, RepealMotion))
            )
        ):
            # This is the creation boundary for the currently open motion. An
            # older request for a settled motion with the same rule id must not
            # resurface (most importantly across repeated repeal attempts).
            return None
    return None


_OPAQUE_IDENTIFIER_RE = re.compile(
    r"(?:\b[A-Za-z0-9]+_[A-Za-z0-9_.-]+\b|\b[A-Z]{2,}[A-Z0-9]*-\d+[A-Z0-9-]*\b|#[A-Za-z0-9-]+)"
)
_MEASURED_VALUE_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:%|ppm|kg(?:/ha)?|kilograms?|(?:metric\s+)?tonnes?|tons?|liters?|litres?|lbs?|pounds?|hours?|minutes?|°[FC])\b",
    re.IGNORECASE,
)
_TEMPORAL_RE = re.compile(
    r"(?:\b\d{1,2}:\d{2}\b|\b(?:a\.?m\.?|p\.?m\.?)\b|\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b|\b(?:before|after|until|deadline)\b)",
    re.IGNORECASE,
)
_EXACT_LABEL_RE = re.compile(r"[\"'“”‘’][^\"'“”‘’]{1,80}[\"'“”‘’]")


def _generalize_semantic_fault(expected_meaning: str) -> tuple[FailureClass, str]:
    """Classify literal shape without carrying any source value into the prompt."""
    has_identifier = _OPAQUE_IDENTIFIER_RE.search(expected_meaning) is not None
    has_measurement = _MEASURED_VALUE_RE.search(expected_meaning) is not None
    if has_identifier and has_measurement:
        return (
            "QUANTIFIED_BUNDLE",
            "Preserve every quantity, unit, opaque identifier, and relationship in a measured allocation as one complete bundle.",
        )
    if _TEMPORAL_RE.search(expected_meaning):
        return (
            "TEMPORAL_CONSTRAINT",
            "Preserve complete times, ranges, deadlines, and their ordering relationships without normalizing away precision.",
        )
    if has_measurement:
        return (
            "MEASURED_VALUE",
            "Preserve numeric precision, units, thresholds, and comparison direction as one complete measured fact.",
        )
    if has_identifier:
        return (
            "OPAQUE_IDENTIFIER",
            "Preserve opaque identifiers exactly, including internal punctuation, digits, case, and their semantic role.",
        )
    if _EXACT_LABEL_RE.search(expected_meaning):
        return (
            "EXACT_LABEL",
            "Preserve exact labels and their attachment to the entity or location they identify.",
        )
    return (
        "SEMANTIC_RELATIONSHIP",
        "Preserve the complete critical fact and the relationships between its entities, actions, and constraints.",
    )


def _semantic_fault_identity(
    *, scoring_version: str, benchmark_version: str, benchmark_id: str, atom_id: str
) -> str:
    return f"{scoring_version}:{benchmark_version}:{benchmark_id}:{atom_id}"


def _semantic_fault_token(source_identity: str) -> str:
    digest = hashlib.sha256(
        f"alato-semantic-fault-v1\0{source_identity}".encode("utf-8")
    ).hexdigest()
    return f"fault-{digest[:24]}"


def _validated_v2_exam(event: dict[str, Any]) -> dict[str, Any] | None:
    """Return a fully correlated judge-valid V2 exam or fail closed."""
    turn = event.get("turn")
    required_strings = (
        "benchmark_id",
        "benchmark_version",
        "scoring_version",
        "language_version",
        "language_hash",
        "original",
        "encoded",
        "decoded",
    )
    if not (
        event.get("type") == "test"
        and event.get("era") == "benchmark-v2"
        and type(turn) is int
        and turn >= SEMANTIC_FAULT_CUTOVER_TURN
        and event.get("benchmark_id") in {"B1", "B2", "B3", "B4", "B5"}
        and event.get("benchmark_version") == "v2"
        and event.get("scoring_version") == "v2"
        and event.get("judge_valid") is True
        and event.get("judge_status") == "VALID"
        and all(isinstance(event.get(key), str) for key in required_strings)
        and len(event.get("language_hash", "")) == 64
    ):
        return None

    answer_key = event.get("answer_key")
    atom_results = event.get("atom_results")
    critical_failures = event.get("critical_failures")
    if not all(
        isinstance(value, list)
        for value in (answer_key, atom_results, critical_failures)
    ) or not answer_key:
        return None

    normalized_key: list[dict[str, Any]] = []
    key_ids: list[str] = []
    for atom in answer_key:
        if not (
            isinstance(atom, dict)
            and isinstance(atom.get("id"), str)
            and atom.get("id")
            and isinstance(atom.get("meaning"), str)
            and atom.get("meaning")
            and type(atom.get("critical")) is bool
        ):
            return None
        required_literals = atom.get("required_literals", [])
        if not (
            isinstance(required_literals, list)
            and all(isinstance(value, str) for value in required_literals)
        ):
            return None
        key_ids.append(atom["id"])
        normalized_key.append(
            {
                "id": atom["id"],
                "meaning": atom["meaning"],
                "critical": atom["critical"],
                "required_literals": list(required_literals),
            }
        )
    if len(key_ids) != len(set(key_ids)):
        return None

    normalized_results: list[dict[str, str]] = []
    for item in atom_results:
        if not (
            isinstance(item, dict)
            and isinstance(item.get("id"), str)
            and item.get("verdict") in {"SURVIVED", "MISSING", "CORRUPTED"}
            and isinstance(item.get("evidence"), str)
        ):
            return None
        evidence = item["evidence"]
        if (item["verdict"] == "MISSING") != (evidence == ""):
            return None
        normalized_results.append(
            {
                "id": item["id"],
                "verdict": item["verdict"],
                "evidence": evidence,
            }
        )
    if [item["id"] for item in normalized_results] != key_ids:
        return None

    expected_failures = []
    for atom, result in zip(normalized_key, normalized_results, strict=True):
        if atom["critical"] and result["verdict"] in {"MISSING", "CORRUPTED"}:
            expected_failures.append(
                {
                    "atom_id": atom["id"],
                    "decoded_evidence": result["evidence"],
                    "expected_meaning": atom["meaning"],
                    "verdict": result["verdict"],
                }
            )
    normalized_failures = []
    for failure in critical_failures:
        if not (
            isinstance(failure, dict)
            and isinstance(failure.get("atom_id"), str)
            and isinstance(failure.get("decoded_evidence"), str)
            and isinstance(failure.get("expected_meaning"), str)
            and failure.get("verdict") in {"MISSING", "CORRUPTED"}
        ):
            return None
        normalized_failures.append(
            {
                "atom_id": failure["atom_id"],
                "decoded_evidence": failure["decoded_evidence"],
                "expected_meaning": failure["expected_meaning"],
                "verdict": failure["verdict"],
            }
        )
    if normalized_failures != expected_failures:
        return None

    return {
        "turn": turn,
        "event": event,
        "answer_key": normalized_key,
        "atom_results": normalized_results,
        "critical_failures": normalized_failures,
    }


def _source_evidence(
    exam: dict[str, Any], atom: dict[str, Any], failure: dict[str, str]
) -> SemanticFaultEvidence:
    event = exam["event"]
    return SemanticFaultEvidence(
        exam_turn=exam["turn"],
        benchmark_id=event["benchmark_id"],
        benchmark_version=event["benchmark_version"],
        scoring_version=event["scoring_version"],
        atom_id=atom["id"],
        classification=failure["verdict"],
        expected_meaning=atom["meaning"],
        required_literals=copy.deepcopy(atom["required_literals"]),
        decoded_evidence=failure["decoded_evidence"],
        original=event["original"],
        encoded=event["encoded"],
        decoded=event["decoded"],
        language_version=event["language_version"],
        language_hash=event["language_hash"],
    )


def _apply_exam_to_fault_ledger(
    ledger: dict[str, SemanticFaultLedgerEntry], exam: dict[str, Any]
) -> None:
    event = exam["event"]
    key_by_id = {atom["id"]: atom for atom in exam["answer_key"]}
    failure_by_id = {
        failure["atom_id"]: failure for failure in exam["critical_failures"]
    }
    for atom_id, failure in failure_by_id.items():
        atom = key_by_id[atom_id]
        identity = _semantic_fault_identity(
            scoring_version=event["scoring_version"],
            benchmark_version=event["benchmark_version"],
            benchmark_id=event["benchmark_id"],
            atom_id=atom_id,
        )
        source = _source_evidence(exam, atom, failure)
        existing = ledger.get(identity)
        if existing is None:
            failure_class, invariant = _generalize_semantic_fault(
                source.expected_meaning
            )
            ledger[identity] = SemanticFaultLedgerEntry(
                source_identity=identity,
                fault_token=_semantic_fault_token(identity),
                first_failure_turn=exam["turn"],
                last_failure_turn=exam["turn"],
                classification=source.classification,
                failure_class=failure_class,
                invariant=invariant,
                status="UNRESOLVED",
                latest_source=source,
            )
            continue
        if existing.latest_source.expected_meaning != source.expected_meaning:
            # A same-version answer-key drift has no safe lifecycle interpretation.
            continue
        existing.last_failure_turn = exam["turn"]
        existing.classification = source.classification
        existing.failure_class, existing.invariant = _generalize_semantic_fault(
            source.expected_meaning
        )
        existing.status = "UNRESOLVED"
        existing.resolved_turn = None
        existing.latest_source = source

    result_by_id = {item["id"]: item for item in exam["atom_results"]}
    for identity, entry in ledger.items():
        if not identity.startswith(
            f"{event['scoring_version']}:{event['benchmark_version']}:{event['benchmark_id']}:"
        ):
            continue
        result = result_by_id.get(entry.latest_source.atom_id)
        atom = key_by_id.get(entry.latest_source.atom_id)
        if not result or not atom:
            continue
        if atom["meaning"] != entry.latest_source.expected_meaning:
            continue
        if (
            entry.status == "PENDING_RETEST"
            and entry.adoption_turn is not None
            and exam["turn"] > entry.adoption_turn
            and result["verdict"] == "SURVIVED"
        ):
            entry.status = "RESOLVED"
            entry.resolved_turn = exam["turn"]


def _linked_fault_for_motion(
    ledger: dict[str, SemanticFaultLedgerEntry], target_rule_id: str
) -> SemanticFaultLedgerEntry | None:
    linked = [
        entry
        for entry in ledger.values()
        if entry.linked_motion_rule_id == target_rule_id
        and entry.status == "REPAIR_PROPOSED"
    ]
    return linked[0] if len(linked) == 1 else None


def _apply_legislature_to_fault_ledger(
    ledger: dict[str, SemanticFaultLedgerEntry], event: dict[str, Any]
) -> None:
    payload = event.get("post_state_receipt")
    if not isinstance(payload, dict):
        return
    try:
        receipt = PostStateReceipt.model_validate(payload, strict=True)
    except ValidationError:
        return
    if receipt.turn < SEMANTIC_FAULT_CUTOVER_TURN:
        return
    action = receipt.attempted_action
    motion = action.motion if action is not None else None
    fault_response = action.fault_response if action is not None else None

    if (
        receipt.actor == "A"
        and receipt.result == "accepted"
        and receipt.reason == "proposal_recorded"
        and isinstance(motion, ProposeMotion)
        and fault_response is not None
        and receipt.current_open_motion is not None
        and receipt.current_open_motion.kind == "add"
        and receipt.current_open_motion.proposed_turn == receipt.turn
        and receipt.current_open_motion.target_rule_id in receipt.changed_rule_ids
    ):
        matching = [
            entry
            for entry in ledger.values()
            if entry.fault_token == fault_response.fault_token
            and entry.status == "UNRESOLVED"
        ]
        if len(matching) == 1:
            entry = matching[0]
            entry.status = "REPAIR_PROPOSED"
            entry.linked_motion_rule_id = receipt.current_open_motion.target_rule_id
            entry.repair_proposed_turn = receipt.turn
            entry.adoption_turn = None
            entry.resolved_turn = None
        return

    if receipt.actor != "B" or receipt.result != "accepted" or motion is None:
        return
    target_rule_id = getattr(motion, "target_rule_id", None)
    if not isinstance(target_rule_id, str):
        return
    entry = _linked_fault_for_motion(ledger, target_rule_id)
    if entry is None:
        return
    if isinstance(motion, RequestMotion):
        if (
            receipt.reason == "focused_work_requested"
            and receipt.current_open_motion is not None
            and receipt.current_open_motion.target_rule_id == target_rule_id
        ):
            return
        return
    if receipt.current_open_motion is not None:
        return
    if isinstance(motion, RejectMotion):
        entry.status = "UNRESOLVED"
        entry.adoption_turn = None
        entry.resolved_turn = None
    elif isinstance(motion, AdoptMotion):
        entry.status = "PENDING_RETEST"
        entry.adoption_turn = receipt.turn
        entry.resolved_turn = None


def derive_semantic_fault_ledger(
    events: list[dict[str, Any]],
) -> list[SemanticFaultLedgerEntry]:
    """Reconstruct the bounded private ledger from canonical events only."""
    ledger: dict[str, SemanticFaultLedgerEntry] = {}
    for event in events:
        if not isinstance(event, dict):
            continue
        exam = _validated_v2_exam(event)
        if exam is not None:
            _apply_exam_to_fault_ledger(ledger, exam)
        elif event.get("type") == "legislature":
            _apply_legislature_to_fault_ledger(ledger, event)
    return sorted(
        (entry.model_copy(deep=True) for entry in ledger.values()),
        key=lambda entry: (entry.first_failure_turn, entry.source_identity),
    )


def select_semantic_fault_for_turn(
    ledger: list[SemanticFaultLedgerEntry],
    *,
    role: Role,
    open_motion: OpenMotionState | None,
) -> SemanticFaultLedgerEntry | None:
    """Select one actionable or linked fault without exposing the private queue."""
    if open_motion is not None:
        linked = [
            entry
            for entry in ledger
            if entry.linked_motion_rule_id == open_motion.target_rule_id
            and entry.status == "REPAIR_PROPOSED"
        ]
        return linked[0].model_copy(deep=True) if len(linked) == 1 else None
    if role != "A":
        return None
    unresolved = [entry for entry in ledger if entry.status == "UNRESOLVED"]
    return unresolved[0].model_copy(deep=True) if unresolved else None


def semantic_fault_feedback(
    entry: SemanticFaultLedgerEntry | None,
) -> SemanticFaultFeedback | None:
    if entry is None or entry.status not in {"UNRESOLVED", "REPAIR_PROPOSED"}:
        return None
    return SemanticFaultFeedback(
        fault_token=entry.fault_token,
        status=entry.status,
        classification=entry.classification,
        failure_class=entry.failure_class,
        invariant=entry.invariant,
    )


def validation_reason(error: ValidationError | ValueError) -> str:
    """Return one bounded structural reason without storing provider prose."""
    if isinstance(error, ValidationError):
        first = error.errors(include_url=False)[0]
        location = ".".join(str(part) for part in first.get("loc", ())) or "response"
        return f"{first.get('type', 'validation_error')} at {location}"[:500]
    return f"{error.__class__.__name__}: {error}"[:500]
