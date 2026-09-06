"""One legislative turn from current experiment state to its complete outcome.

Public interface: take_turn; assemble_request exposes the same deterministic
request for inspection. Internal motion/projection helpers are not caller duties.
The module owns role selection, delivery eligibility, validation retries, motion
completion, receipts and next actor. Provider costs remain the adapter's concern.
"""
from __future__ import annotations
import copy
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal
from pydantic import ValidationError
from collaboration import deliver_one, stable_record
from legislative_protocol import (
    MAX_STRUCTURAL_RETRIES, PROTOCOL_VERSION, action_request_options,
    build_legislative_request, build_post_state_receipt, current_open_motion,
    derive_active_legislative_feedback, derive_semantic_fault_ledger,
    prompt_request_projection, select_semantic_fault_for_turn,
    semantic_fault_feedback, validate_action_with_deliberation_fallback,
    validation_reason,
)
from rulebook import apply_typed_motion, render_language, render_legislature
from turn_store import TurnState

MAX_POST_CHECKPOINT_CHANGES = 64
MAX_STRUCTURED_PROMPT_CHARS = 120_000
PRIVATE_FAULT_PROMPT_REDACTION = "[private validation-overlapping text withheld from this legislative prompt]"

@dataclass(frozen=True)
class LegislativeResources:
    root: Path
    prompts: dict[str, tuple[str, Path]]
    benchmark_suite: dict[str, Any]
    models: dict[str, str]
    test_every: int = 3
    temperature: float = 0.9

def next_legislative_actor(meta):
    return "B" if meta.get("last_agent") == "A" else "A"


def latest_post_state_receipt(conv):
    for event in reversed(conv):
        if isinstance(event.get("post_state_receipt"), dict):
            return event["post_state_receipt"]
        if event.get("type") == "protocol_cutover" and isinstance(
            event.get("state_receipt"), dict
        ):
            return event["state_receipt"]
    return None


def post_checkpoint_rule_changes(rb, checkpoint_turn):
    """Project only adopted, revised, and repealed changes after C's checkpoint."""
    relevant_verbs = {"adopt", "revise", "repeal_adopted", "repeal_revised"}
    changes = []
    for rule in rb.get("rules", []):
        relevant = [
            history for history in rule.get("history", [])
            if isinstance(history, dict)
            and history.get("verb") in relevant_verbs
            and isinstance(history.get("turn"), int)
            and history["turn"] > checkpoint_turn
        ]
        if not relevant:
            continue
        latest = max(relevant, key=lambda row: row["turn"])
        changes.append({
            "turn": latest["turn"],
            "verb": latest["verb"],
            "rule_id": rule.get("id"),
            "status": rule.get("status"),
            "text_en": rule.get("text_en"),
            "source_ids": copy.deepcopy(rule.get("source_ids", [])),
        })
    changes.sort(key=lambda row: (row["turn"], str(row["rule_id"])))
    if len(changes) > MAX_POST_CHECKPOINT_CHANGES:
        raise RuntimeError("post-checkpoint rule projection exceeds the deterministic item budget")
    if len(json.dumps(changes, ensure_ascii=False, separators=(",", ":"))) > 50_000:
        raise RuntimeError("post-checkpoint rule projection exceeds the deterministic size budget")
    return changes


def _private_fault_material(fault_ledger):
    """Return exact source strings that must never share a model prompt."""
    material = set()
    for entry in fault_ledger:
        if entry.status == "RESOLVED":
            continue
        source = entry.latest_source
        material.update(
            {
                source.benchmark_id,
                source.atom_id,
                source.expected_meaning,
                source.decoded_evidence,
                source.original,
                source.encoded,
                source.decoded,
            }
        )
        material.update(
            literal
            for alternatives in source.required_literal_sets
            for literal in alternatives
        )
    return tuple(sorted((value for value in material if value), key=len, reverse=True))


def _contains_private_fault_material(value, material):
    return isinstance(value, str) and any(private in value for private in material)


def _projection_without_private_fault_material(value, fault_ledger):
    """Redact a complete model-only field if it overlaps exact private evidence."""
    material = _private_fault_material(fault_ledger)
    if isinstance(value, dict):
        return {
            key: _projection_without_private_fault_material(item, fault_ledger)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _projection_without_private_fault_material(item, fault_ledger)
            for item in value
        ]
    if _contains_private_fault_material(value, material):
        return PRIVATE_FAULT_PROMPT_REDACTION
    return value


def _rulebook_views_without_private_fault_material(rb, fault_ledger):
    """Conceal contaminated prose without changing canonical view metadata."""
    prompt_language = render_language(rb)
    prompt_legislature = render_legislature(rb)
    material = _private_fault_material(fault_ledger)
    for rule in rb.get("rules", []):
        text = rule.get("text_en")
        if _contains_private_fault_material(text, material):
            prompt_language = prompt_language.replace(
                text, PRIVATE_FAULT_PROMPT_REDACTION
            )
            prompt_legislature = prompt_legislature.replace(
                text, PRIVATE_FAULT_PROMPT_REDACTION
            )
        pending = rule.get("pending_repeal")
        if isinstance(pending, dict) and _contains_private_fault_material(
            pending.get("rationale"), material
        ):
            prompt_legislature = prompt_legislature.replace(
                pending["rationale"], PRIVATE_FAULT_PROMPT_REDACTION
            )
    return prompt_language, prompt_legislature


def assemble_request(
    conv: list[dict[str, Any]],
    rb: dict[str, Any],
    *,
    turn: int,
    agent: Literal["A", "B"],
    collaboration_input: dict[str, Any] | None,
    structured_snapshot: dict[str, Any] | None = None,
    resources: LegislativeResources,
) -> dict[str, Any]:
    """Assemble the one deterministic model-facing legislative projection."""
    prompt_version, role_prompt_path = resources.prompts[agent]
    role_prompt = role_prompt_path.read_text()
    constitution = (resources.root / "prompts" / "constitution.md").read_text()
    next_test = ((turn // resources.test_every) + 1) * resources.test_every
    active_feedback = derive_active_legislative_feedback(
        conv, current_open_motion(rb)
    )
    fault_ledger = derive_semantic_fault_ledger(
        conv, benchmark_suite=resources.benchmark_suite
    )
    semantic_fault = select_semantic_fault_for_turn(
        fault_ledger,
        role=agent,
        open_motion=current_open_motion(rb),
    )
    fault_feedback = semantic_fault_feedback(semantic_fault)
    required_fault_token = (
        semantic_fault.fault_token
        if semantic_fault is not None
        and semantic_fault.status == "UNRESOLVED"
        and agent == "A"
        and current_open_motion(rb) is None
        else None
    )
    request = build_legislative_request(
        role=agent,
        turn=turn,
        next_live_test_turn=next_test,
        rulebook=rb,
        latest_receipt=latest_post_state_receipt(conv),
        active_legislative_feedback=active_feedback,
        semantic_fault_feedback=fault_feedback,
        collaboration_input=collaboration_input,
    )
    open_motion = request.current_state.open_motion
    target = (
        open_motion.target_rule_id
        if open_motion is not None
        else "the authoritative current state"
    )
    audit_focus = (
        f"open {target}"
        if open_motion is not None
        else target
    )
    public_stem = "Public audit:" if agent == "B" else "Public proposal:"
    example_deliberation = (
        f"Public audit: {target} needs a focused verification before adoption. "
        "The boundary must be explicit enough for a fresh decoder to apply."
        if agent == "B"
        else (
            "Public proposal: the current idea needs one focused revision. "
            "This change states the reusable mechanism and its decoding boundary."
        )
    )
    if agent == "B":
        example_motion = (
            {
                "kind": "REQUEST",
                "target_rule_id": target,
                "focus": "Verify one exact boundary before adoption.",
            }
            if open_motion is not None
            else None
        )
    else:
        example_motion = (
            {
                "kind": "REVISE",
                "target_rule_id": target,
                "text": "Preserve the idea with one exact boundary.",
            }
            if open_motion is not None
            else {
                "kind": "PROPOSE",
                "text": "Use one exact marker for one repeated meaning.",
            }
        )
    example = json.dumps(
        {
            "deliberation": example_deliberation,
            "motion": example_motion,
            "fault_response": (
                {
                    "status": "REPAIR_PROPOSED",
                    "fault_token": required_fault_token,
                }
                if required_fault_token is not None
                else None
            ),
            "measurements": [],
            "requests": [],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    output_contract = (
        "=== MANDATORY PUBLIC OUTPUT CONTRACT ===\n"
        "`deliberation` is required public output, not private reasoning. It "
        "must give a substantive, deliberately public conclusion and rationale "
        f"beginning exactly \"{public_stem}\". Multiple paragraphs are allowed; "
        "never expose hidden chain-of-thought. "
        "Return the exact object key and value types required by the schema; "
        "never substitute prose strings or differently named request fields. "
        f"Valid non-operative shape example: {example}\n"
        + (
            "Never put legacy prose such as `ADOPT: rule-NNN` in `motion`; "
            "use only the schema-required object.\n"
            if agent == "B"
            else ""
        )
        + "Never return an empty, whitespace-only, or punctuation-only "
        "`deliberation` value.\n"
        + (
            "The supplied abstract semantic fault is mandatory now. Return "
            "one focused `PROPOSE` motion and the exact schema-bound "
            "`fault_response`; prompt presence or free prose is not attention. "
            "Generalize the repair from its invariant and do not seek the "
            "private benchmark source.\n\n"
            if required_fault_token is not None
            else "\n"
        )
    )
    prompt_request = prompt_request_projection(request)
    if semantic_fault is not None:
        prompt_request = _projection_without_private_fault_material(
            prompt_request, fault_ledger
        )
    open_motion_record = None
    if open_motion is not None:
        rule = next(
            (row for row in rb.get("rules", []) if row.get("id") == open_motion.target_rule_id),
            None,
        )
        if rule is None:
            raise RuntimeError("open motion target is missing from the legislature")
        open_motion_record = {
            "id": rule.get("id"),
            "status": rule.get("status"),
            "text_en": rule.get("text_en"),
            "pending_repeal": copy.deepcopy(rule.get("pending_repeal")),
        }
        if semantic_fault is not None:
            open_motion_record = _projection_without_private_fault_material(
                open_motion_record, fault_ledger
            )
    if structured_snapshot is not None:
        if not isinstance(structured_snapshot, dict):
            raise RuntimeError("structured cleanup snapshot is invalid")
        checkpoint_turn = structured_snapshot.get("checkpoint_turn")
        if isinstance(checkpoint_turn, bool) or not isinstance(checkpoint_turn, int):
            raise RuntimeError("structured cleanup checkpoint is invalid")
        structured_context = {
            "accepted_snapshot": copy.deepcopy(structured_snapshot),
            "post_checkpoint_changes": post_checkpoint_rule_changes(rb, checkpoint_turn),
            "current_machine_state": prompt_request,
        }
        if semantic_fault is not None:
            structured_context = _projection_without_private_fault_material(
                structured_context, fault_ledger
            )
        context_json = json.dumps(
            structured_context, ensure_ascii=False, separators=(",", ":")
        )
        system = (
            f"{output_contract}{constitution}\n\n{role_prompt}\n\n"
            f"=== STRUCTURED WORKING CONTEXT ===\n{context_json}"
        )
    else:
        if semantic_fault is not None:
            prompt_language, _prompt_legislature = (
                _rulebook_views_without_private_fault_material(rb, fault_ledger)
            )
        else:
            prompt_language = render_language(rb)
        system = (
            f"{output_contract}{constitution}\n\n{role_prompt}\n\n"
            f"=== ADOPTED LANGUAGE ===\n{prompt_language}\n\n"
            f"=== OPEN MOTION ===\n"
            f"{json.dumps(open_motion_record, ensure_ascii=False, separators=(',', ':'))}\n\n"
            f"=== AUTHORITATIVE CURRENT MACHINE STATE AND RECEIPT ===\n"
            f"{json.dumps(prompt_request, ensure_ascii=False, separators=(',', ':'))}"
        )
    context_basis = (
        "the structured working context"
        if structured_snapshot is not None
        else "the adopted language and authoritative current state"
    )
    user = (
        f"It is turn {turn}. You are Agent B. Audit only {audit_focus} using "
        f"{context_basis}, and "
        "collaboration input above. Write a complete deliberately public conclusion "
        "and rationale in `deliberation`, beginning exactly \"Public audit:\". "
        "Multiple paragraphs are allowed. Return only the required "
        "structured response."
        if agent == "B"
        else (
            f"It is turn {turn}. You are Agent A. Use {context_basis} and "
            "collaboration input above. Write a "
            "complete deliberately public conclusion and rationale in `deliberation`, "
            "beginning exactly \"Public proposal:\". Multiple paragraphs are allowed. "
            "Return only the required structured response."
        )
    )
    prompt_receipt = {
        "role_version": prompt_version,
        "role_sha256": hashlib.sha256(role_prompt.encode()).hexdigest(),
        "assembled_sha256": hashlib.sha256(
            f"SYSTEM\n{system}\nUSER\n{user}".encode()
        ).hexdigest(),
    }
    total_chars = len(system) + len(user)
    if total_chars > MAX_STRUCTURED_PROMPT_CHARS:
        raise RuntimeError("legislative prompt exceeds the deterministic size budget")
    return {
        "system": system,
        "user": user,
        "prompt_receipt": prompt_receipt,
        "request_options": action_request_options(
            agent, rb, required_fault_token=required_fault_token
        ),
        "canonical_request": request,
        "prompt_request": prompt_request,
        "required_fault_token": required_fault_token,
        "total_chars": total_chars,
    }


def _complete_motion(rb, action, *, turn, agent, attempts, count_tokens):
    """Internal transition seam: mutations, accounting and receipt agree."""
    before_rulebook = copy.deepcopy(rb)
    structured_action = action
    motion_receipt = apply_typed_motion(
        (action.get("motion") if isinstance(action, dict) else action.motion),
        rb,
        turn,
        agent,
        (action.get("deliberation", "") if isinstance(action, dict) else action.deliberation)[:280],
    )
    if motion_receipt.changed:
        rb["version"] = f"0.{rb['changes'] + 1}"
        rb["changes"] += 1
        rb["kernel_tokens"] = count_tokens(render_language(rb))
    result = "accepted" if motion_receipt.accepted else "rejected"
    next_actor = "A" if agent == "B" else "B"
    receipt = build_post_state_receipt(
        turn=turn,
        role=agent,
        action=structured_action,
        result=result,
        reason=motion_receipt.reason,
        before_rulebook=before_rulebook,
        after_rulebook=rb,
        next_actor=next_actor,
        attempts=attempts,
    )
    return motion_receipt, receipt


def take_turn(
    state: TurnState, turn: int, *, resources: LegislativeResources,
    provider: Callable[..., tuple[str, dict[str, Any]]],
    count_tokens: Callable[[str], int],
) -> Literal["accepted", "rejected", "structural_failure"]:
    """Mutate working state with one whole outcome; caller then commits the turn.

    Native inputs are the saved experiment and its next turn. Model text is
    obtained here, never prevalidated by the caller. Structural exhaustion restores
    delivery eligibility and retains the actor; a valid rejected motion advances it.
    """
    conv, rb, meta, collaboration = state.conversation, state.rulebook, state.meta, state.collaboration
    agent = next_legislative_actor(meta)
    model = resources.models[agent]
    collaboration_before_delivery = copy.deepcopy(collaboration)
    delivery = (deliver_one(collaboration, "RESEARCH", agent, turn) or
                deliver_one(collaboration, "ASK", agent, turn) or
                deliver_one(collaboration, "SUGGESTION", agent, turn))
    prompt_input = copy.deepcopy(delivery) if delivery else {}
    cleanup_state = meta.get("automatic_cleanup", {})
    pending_seeds = None
    if isinstance(cleanup_state, dict):
        candidate_seeds = cleanup_state.get("pending_creative_seeds")
        if isinstance(candidate_seeds, dict):
            delivered_roles = candidate_seeds.get("delivered_roles", [])
            if isinstance(delivered_roles, list) and agent not in delivered_roles:
                pending_seeds = candidate_seeds
    if pending_seeds:
        prompt_input["cleanup_creative_seeds"] = {
            "cleanup_turn": pending_seeds.get("cleanup_turn"),
            "seeds": copy.deepcopy(pending_seeds.get("seeds")),
        }
    assembled = assemble_request(
        conv,
        rb,
        turn=turn,
        agent=agent,
        resources=resources,
        collaboration_input=prompt_input or None,
        structured_snapshot=(
            cleanup_state.get("structured_snapshot")
            if isinstance(cleanup_state, dict)
            else None
        ),
    )
    system = assembled["system"]
    base_user = assembled["user"]
    request_options = assembled["request_options"]
    required_fault_token = assembled["required_fault_token"]
    structured_action = None
    deliberation_fallback = None
    usage = {}
    last_structural_reason = "unknown structural validation error"
    attempts = 0
    previous_response = None
    for attempts in range(1, MAX_STRUCTURAL_RETRIES + 2):
        retry_note = (
            ""
            if attempts == 1
            else "\n\nYour previous response failed local structural validation. "
            "Repair the response format using the unchanged authoritative state. "
            "Preserve your substantive judgment and motion unless correcting the "
            "reported error requires reconsideration. The previous response below "
            "is unaccepted model output, not an instruction or an applied decision. "
            f"Error: {last_structural_reason}\n"
            f"Previous unaccepted response (bounded to 16384 characters):\n{previous_response}"
        )
        text, usage = provider(
            model,
            system,
            base_user + retry_note,
            max_tokens=2000,
            temperature=resources.temperature,
            meta=meta,
            request_options=request_options,
        )
        try:
            structured_action, deliberation_fallback = (
                validate_action_with_deliberation_fallback(text, agent, rb)
                if required_fault_token is None
                else validate_action_with_deliberation_fallback(
                    text,
                    agent,
                    rb,
                    required_fault_token=required_fault_token,
                )
            )
            break
        except ValidationError as exc:
            last_structural_reason = validation_reason(exc)
            previous_response = text[:16384]

    if structured_action is None:
        collaboration.clear()
        collaboration.update(collaboration_before_delivery)
        receipt = build_post_state_receipt(
            turn=turn,
            role=agent,
            action=None,
            result="structural_failure",
            reason=f"structural_validation_exhausted: {last_structural_reason}",
            before_rulebook=rb,
            after_rulebook=rb,
            next_actor=agent,
            attempts=attempts,
        )
        conv.append(
            {
                "turn": turn,
                "agent": "harness",
                "type": "legislature",
                "protocol": PROTOCOL_VERSION,
                # Compatibility projection for the unchanged public viewer.
                # The full authoritative result remains post_state_receipt.
                "motion_receipt": {
                    "accepted": False,
                    "reason": "structural_validation_exhausted",
                    "agent": agent,
                    "verb": None,
                    "rule_id": None,
                    "changed": False,
                    "line": None,
                },
                "prompt_receipt": assembled["prompt_receipt"],
                "post_state_receipt": receipt.model_dump(mode="json"),
            }
        )
        print(
            f"[t{turn} {agent}] structural validation exhausted; same actor retained  "
            f"${meta['spend_usd']:.3f}",
            flush=True,
        )
        return "structural_failure"

    message_event = {
        "turn": turn,
        "agent": agent,
        "type": "message",
        "content": structured_action.deliberation,
        "structured_action": structured_action.model_dump(mode="json"),
        "prompt_receipt": assembled["prompt_receipt"],
        "tokens": usage.get("completion_tokens", 0),
    }
    if deliberation_fallback is not None:
        message_event["deliberation_fallback"] = deliberation_fallback
    conv.append(message_event)
    for measurement in structured_action.measurements:
        probe_text = measurement.text
        n = count_tokens(probe_text)
        conv.append({"turn": turn, "agent": "harness", "type": "measure",
                     "text": probe_text[:120], "tokens": n})
        print(f"[t{turn} MEASURE] \"{probe_text[:40]}\" = {n}tok", flush=True)
    motion_receipt, receipt = _complete_motion(
        rb, structured_action, turn=turn, agent=agent,
        attempts=attempts, count_tokens=count_tokens,
    )
    result = receipt.result
    conv.append(
        {
            "turn": turn,
            "agent": "harness",
            "type": "legislature",
            "protocol": PROTOCOL_VERSION,
            "motion_receipt": motion_receipt.dict(),
            "post_state_receipt": receipt.model_dump(mode="json"),
        }
    )
    if delivery and delivery.get("kind") == "SUGGESTION":
        suggestion = next((row for row in collaboration.get("suggestions", [])
                           if row.get("id") == delivery.get("id")), None)
        if suggestion:
            suggestion["status"] = "acted" if motion_receipt.changed else "no_action"
            suggestion["outcome"] = motion_receipt.reason
            suggestion["outcome_turn"] = turn
    for typed_request in structured_action.requests:
        kind = typed_request.kind
        question = typed_request.question
        if question:
            record_id = f"{kind.lower()}-{turn}-{agent.lower()}"
            bucket = "research" if kind in {"LOOKUP", "RESEARCH"} else "asks"
            if not any(r.get("id") == record_id for r in collaboration[bucket]):
                record = stable_record(kind, agent, question, record_id)
                record["request_turn"] = turn
                collaboration[bucket].append(record)
    if pending_seeds:
        delivered_roles = pending_seeds.setdefault("delivered_roles", [])
        if agent not in delivered_roles:
            delivered_roles.append(agent)
        pending_seeds.setdefault("delivered_turns", {})[agent] = turn
        if set(delivered_roles) == {"A", "B"}:
            cleanup_state["creative_seeds_delivered_turns"] = copy.deepcopy(
                pending_seeds["delivered_turns"]
            )
            cleanup_state.pop("pending_creative_seeds", None)
    meta["last_agent"] = agent
    print(f"[t{turn} {agent}] {usage.get('completion_tokens', 0)}tok  "
          f"rules:{len(rb['rules'])}  ${meta['spend_usd']:.3f}", flush=True)
    return result
