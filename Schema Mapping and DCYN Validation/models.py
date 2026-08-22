from __future__ import annotations

import uuid

from django.db import models


class StudentOnboardingRecord(models.Model):
    student_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    student_full_name = models.CharField(max_length=120)
    date_of_birth = models.DateField()

    guardian_full_name = models.CharField(max_length=120)
    guardian_email = models.EmailField()
    guardian_phone_number = models.CharField(max_length=16)

    has_learning_diagnosis = models.BooleanField()
    diagnosis_type = models.CharField(max_length=100)
    diagnosis_documentation_provided = models.BooleanField()

    requires_lsa_support = models.BooleanField()
    preferred_support_frequency = models.CharField(max_length=100)

    parent_consent_given = models.BooleanField()
    guardian_contact_verified = models.BooleanField()

    additional_notes = models.TextField(
        max_length=1000,
        blank=True,
    )

    submitted_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "student_onboarding"
        ordering = ["-submitted_at"]

    def __str__(self) -> str:
        return f"{self.student_full_name} ({self.student_id})"