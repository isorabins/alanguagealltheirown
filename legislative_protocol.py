"""Typed legislative transport, state-specific schemas, and authoritative receipts."""
from __future__ import annotations

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
)

from rulebook import language_payload
from state_store import snapshot_hash

PROTOCOL_VERSION = "structured-legislature-v1"
MAX_STRUCTURAL_RETRIES = 2

Role = Literal["A", "B"]
ActionResultKind = Literal["accepted", "rejected", "structural_failure", "cutover"]
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
    measurements: list[MeasurementRequest] = Field(max_length=2)
    requests: list[CollaborationRequest] = Field(max_length=3)


class OpenMotionState(StrictModel):
    kind: Literal["add", "repeal"]
    target_rule_id: str
    proposed_turn: int


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
    role: Role, rulebook: dict[str, Any]
) -> type[_ActionEnvelopeBase]:
    """Create the Pydantic action model authorized by the current role and state."""
    open_motion = current_open_motion(rulebook)
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
            if adopted_ids:
                motion_types.append(_targeted_motion(RepealMotion, adopted_ids))
            state_name = "no_open_motion"
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
                allow_none=not (role == "B" and open_motion is not None),
            ),
            ...,
        ),
    )


def validate_action(
    payload: str | bytes | dict[str, Any], role: Role, rulebook: dict[str, Any]
) -> _ActionEnvelopeBase:
    """Strictly validate provider output against the current state-specific model."""
    model = state_specific_action_model(role, rulebook)
    if isinstance(payload, (str, bytes)):
        return model.model_validate_json(payload, strict=True)
    return model.model_validate(payload, strict=True)


def action_request_options(role: Role, rulebook: dict[str, Any]) -> dict[str, Any]:
    """Return OpenRouter's strict JSON Schema and compatible-provider requirement."""
    model = state_specific_action_model(role, rulebook)
    open_motion = current_open_motion(rulebook)
    state = open_motion.target_rule_id if open_motion else "none"
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
        collaboration_input=collaboration_input,
    )


def validation_reason(error: ValidationError | ValueError) -> str:
    """Return one bounded structural reason without storing provider prose."""
    if isinstance(error, ValidationError):
        first = error.errors(include_url=False)[0]
        location = ".".join(str(part) for part in first.get("loc", ())) or "response"
        return f"{first.get('type', 'validation_error')} at {location}"[:500]
    return f"{error.__class__.__name__}: {error}"[:500]
