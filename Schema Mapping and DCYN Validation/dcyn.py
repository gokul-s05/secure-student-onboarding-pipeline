"""
DCYN (Deconstruct-to-Clean-Yes/No) library.

Purpose: raw onboarding payloads arrive with human-entered, inconsistent
values for what should be binary facts — "Yes", "yes", "Y", "Pending",
"N/A", "true", empty string, and so on. Task 3's brief is explicit: the
downstream serializer must have "exact field validation limits to entirely
eliminate human judgment."

So this library's one job is to take a raw value and either:
  (a) return a strict Python bool, or
  (b) raise DCYNAmbiguousValueError

It deliberately does NOT guess on anything ambiguous ("Pending", "N/A",
"Maybe", empty string). A missing or unclear answer is not the same as
"No" — silently defaulting an unclear consent field to False would be
its own kind of data integrity bug, arguably worse than rejecting it
outright, because it fabricates a fact nobody actually confirmed.
"""

from __future__ import annotations


class DCYNAmbiguousValueError(ValueError):
    """Raised when an incoming value cannot be resolved to a strict Yes/No
    without the system making an assumption on the submitter's behalf."""


# JUDGMENT CALL: this is an explicit allowlist, not a fuzzy matcher. Adding
# a new accepted spelling (e.g. "Affirmative") means editing this set on
# purpose, not silently making the library more permissive over time.
_TRUE_VALUES = {"yes", "y", "true", "1"}
_FALSE_VALUES = {"no", "n", "false", "0"}


def to_strict_bool(raw_value: object, *, field_name: str) -> bool:
    """
    Deconstruct a raw incoming value into a strict boolean.

    Args:
        raw_value: the untrusted value as it arrived in the payload —
            could be a string, bool, None, or anything else a client sent.
        field_name: name of the field being validated, used only to produce
            a useful error message (never used for logic branching).

    Returns:
        True or False.

    Raises:
        DCYNAmbiguousValueError: if the value is missing, empty, or not in
            the explicit allowlist above (e.g. "Pending", "N/A", "Maybe").
    """
    if isinstance(raw_value, bool):
        # Already a real boolean (e.g. payload sent JSON `true`/`false`
        # natively rather than as a string) — nothing to deconstruct.
        return raw_value

    if raw_value is None:
        raise DCYNAmbiguousValueError(
            f"Field '{field_name}' is missing. A binary Yes/No field cannot "
            f"be defaulted — the submitter must provide an explicit answer."
        )

    normalized = str(raw_value).strip().lower()

    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False

    raise DCYNAmbiguousValueError(
        f"Field '{field_name}' has value '{raw_value}', which is not a "
        f"recognized Yes/No answer. Accepted values: "
        f"{sorted(_TRUE_VALUES | _FALSE_VALUES)}. This field cannot be "
        f"silently interpreted — the record must be rejected and returned "
        f"to the submitter for correction."
    )


def deconstruct_payload(raw_payload: dict, *, binary_fields: list[str]) -> dict:
    """
    Apply to_strict_bool across every field named in `binary_fields`,
    leaving all other fields in the payload untouched.

    Collects ALL ambiguous-field errors before raising, rather than
    failing on the first one — so a submitter (or the serializer calling
    this) gets a complete list of what needs correcting in one pass,
    instead of a frustrating one-error-at-a-time loop.
    """
    result = dict(raw_payload)
    errors: dict[str, str] = {}

    for field in binary_fields:
        try:
            result[field] = to_strict_bool(raw_payload.get(field), field_name=field)
        except DCYNAmbiguousValueError as exc:
            errors[field] = str(exc)

    if errors:
        raise DCYNAmbiguousValueError(str(errors))

    return result
