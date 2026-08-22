from __future__ import annotations

from rest_framework import serializers

from .dcyn import DCYNAmbiguousValueError, to_strict_bool
from .models import StudentOnboardingRecord


# These are the exact binary fields present in the raw onboarding payload.
# Each value must resolve to an explicit YES/NO value through DCYN.
DCYN_BINARY_FIELDS = [
    "has_existing_learning_diagnosis",
    "diagnosis_documentation_uploaded",
    "requires_learning_support_assistant",
    "parent_consent_statement_accepted",
    "guardian_identity_verified",
]


class StudentOnboardingSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentOnboardingRecord
        fields = [
            "student_id",
            "student_full_name",
            "date_of_birth",
            "guardian_full_name",
            "guardian_email",
            "guardian_phone_number",
            "has_existing_learning_diagnosis",
            "diagnosis_type",
            "diagnosis_documentation_uploaded",
            "requires_learning_support_assistant",
            "preferred_support_frequency",
            "parent_consent_statement_accepted",
            "guardian_identity_verified",
            "additional_notes",
            "submitted_at",
        ]

    # Server-generated fields.
    student_id = serializers.UUIDField(
        read_only=True,
    )

    submitted_at = serializers.DateTimeField(
        read_only=True,
    )

    # Exact field limits.
    student_full_name = serializers.CharField(
        min_length=2,
        max_length=120,
        required=True,
        allow_blank=False,
    )

    date_of_birth = serializers.DateField(
        required=True,
    )

    guardian_full_name = serializers.CharField(
        min_length=2,
        max_length=120,
        required=True,
        allow_blank=False,
    )

    guardian_email = serializers.EmailField(
        required=True,
        allow_blank=False,
    )

    guardian_phone_number = serializers.RegexField(
        regex=r"^\+[1-9]\d{7,14}$",
        required=True,
        error_messages={
            "invalid": (
                "Guardian phone number must be in international "
                "E.164 format, for example +254712345678."
            )
        },
    )

    # ------------------------------------------------------------------
    # Raw JSON field name -> Django model field name
    # ------------------------------------------------------------------

    has_existing_learning_diagnosis = serializers.BooleanField(
        source="has_learning_diagnosis",
        required=True,
    )

    diagnosis_type = serializers.CharField(
        min_length=2,
        max_length=100,
        required=True,
        allow_blank=False,
    )

    diagnosis_documentation_uploaded = serializers.BooleanField(
        source="diagnosis_documentation_provided",
        required=True,
    )

    requires_learning_support_assistant = serializers.BooleanField(
        source="requires_lsa_support",
        required=True,
    )

    preferred_support_frequency = serializers.CharField(
        min_length=1,
        max_length=100,
        required=True,
        allow_blank=False,
    )

    parent_consent_statement_accepted = serializers.BooleanField(
        source="parent_consent_given",
        required=True,
    )

    guardian_identity_verified = serializers.BooleanField(
        source="guardian_contact_verified",
        required=True,
    )

    additional_notes = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
    )

    def to_internal_value(self, data):
        """
        Convert all raw binary values through the DCYN library
        before DRF performs normal field validation.

        Ambiguous values such as:
        - Pending
        - N/A
        - Maybe
        - empty values

        are rejected rather than guessed.
        """

        errors = {}
        cleaned = dict(data)

        for field_name in DCYN_BINARY_FIELDS:
            if field_name not in data:
                continue

            try:
                cleaned[field_name] = to_strict_bool(
                    data[field_name],
                    field_name=field_name,
                )

            except DCYNAmbiguousValueError as exc:
                errors[field_name] = str(exc)

        if errors:
            raise serializers.ValidationError(errors)

        return super().to_internal_value(cleaned)

    def validate(self, attrs):
        """
        Cross-field validation.

        These rules prevent logically inconsistent records
        from entering the staging layer.
        """

        # Learning support requires explicit parent consent.
        if (
            attrs.get("requires_lsa_support")
            and not attrs.get("parent_consent_given")
        ):
            raise serializers.ValidationError(
                {
                    "parent_consent_statement_accepted": (
                        "Learning support cannot be requested "
                        "without explicit parent consent."
                    )
                }
            )

        # An existing diagnosis requires documentation.
        if (
            attrs.get("has_learning_diagnosis")
            and not attrs.get("diagnosis_documentation_provided")
        ):
            raise serializers.ValidationError(
                {
                    "diagnosis_documentation_uploaded": (
                        "An existing learning diagnosis requires "
                        "supporting documentation to be provided."
                    )
                }
            )

        return attrs