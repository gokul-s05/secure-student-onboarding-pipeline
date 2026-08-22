import json
from pathlib import Path

import pytest

from dcyn import DCYNAmbiguousValueError, to_strict_bool


BASE_DIR = Path(__file__).resolve().parent


def load_sample_payload():
    payload_path = BASE_DIR / "sample_raw_payload.json"

    with payload_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def test_sample_payload_exists():
    payload = load_sample_payload()

    assert isinstance(payload, dict)
    assert "student_full_name" in payload
    assert "date_of_birth" in payload
    assert "guardian_email" in payload


@pytest.mark.parametrize(
    "value, expected",
    [
        ("Yes", True),
        ("YES", True),
        ("Y", True),
        ("true", True),
        ("1", True),
        ("No", False),
        ("NO", False),
        ("N", False),
        ("false", False),
        ("0", False),
    ],
)
def test_dcyn_strict_boolean_conversion(value, expected):
    assert to_strict_bool(value, field_name="test_field") is expected


@pytest.mark.parametrize(
    "value",
    [
        "Pending",
        "Maybe",
        "N/A",
        "",
        "unknown",
    ],
)
def test_dcyn_rejects_ambiguous_values(value):
    with pytest.raises(DCYNAmbiguousValueError):
        to_strict_bool(value, field_name="test_field")


def test_sample_payload_contains_ambiguous_identity_status():
    payload = load_sample_payload()

    assert payload["guardian_identity_verified"] == "Pending"


def test_sample_payload_contains_diagnosis_documentation_conflict():
    payload = load_sample_payload()

    assert payload["has_existing_learning_diagnosis"] == "Yes"
    assert payload["diagnosis_documentation_uploaded"] == "No"