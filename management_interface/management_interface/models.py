import uuid

from django.contrib.auth.models import User
from django.core.validators import EmailValidator
from django.db import models
from django.utils import timezone


class SecureEmailValidator(EmailValidator):
    message = "Enter an nhs.net email address"

    def __init__(self, **kwargs):
        super().__init__(**kwargs, allowlist=["nhs.net"])

    def validate_domain_part(self, _):
        return False


class BaseModel(models.Model):
    """
    Base model holding shared data
    """

    class Meta:
        abstract = True

    id = models.CharField(
        primary_key=True, max_length=64, default=uuid.uuid4, editable=False, unique=True
    )
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        editable=False,
        related_name="%(app_label)s_%(class)s_created_by",
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        editable=False,
        related_name="%(app_label)s_%(class)s_updated_by",
    )


class CareProviderLocation(BaseModel):
    """
    Model that represents a registered care provider location (branch) who wants to receive emails.
    """

    name = models.CharField(max_length=256, help_text="Your Care Provider Branch Name")
    email = models.EmailField(
        null=False,
        db_index=True,
        help_text="example@nhs.net",
        validators=[SecureEmailValidator()],
    )
    ods_code = models.CharField(
        null=False, max_length=16, unique=True, help_text="XXXABCD"
    )
    cqc_location_id = models.CharField(
        null=False, max_length=128, unique=True, help_text="1-110XXXXXXXX"
    )
    registered_manager = models.ForeignKey(
        "RegisteredManager", on_delete=models.CASCADE
    )

    def __str__(self):
        return f"{self.name}"

    def clean(self):
        self.email = str(self.email).strip()


class RegisteredManager(BaseModel):
    """
    Model that represents somebody who is a Care Quality Commission (CQC) registered manager.
    """

    given_name = models.CharField(max_length=256, db_index=True, help_text="Aislinn")
    family_name = models.CharField(max_length=256, db_index=True, help_text="Mullen")
    email = models.EmailField(
        null=False,
        db_index=True,
        unique=True,
        help_text="example@nhs.net",
        validators=[SecureEmailValidator()],
    )
    cqc_registered_manager_id = models.CharField(max_length=128, help_text="1-XXXXXXXX")

    def __str__(self):
        return (
            f"{self.family_name}, {self.given_name} ({self.cqc_registered_manager_id})"
        )

    def clean(self):
        self.email = str(self.email).strip()


class CareRecipient(BaseModel):
    """
    Model that represents somebody who is receiving care from a care provider location
    and who has had a HANS subscription made for them.
    """

    care_provider_location = models.ForeignKey(
        "CareProviderLocation", on_delete=models.CASCADE
    )
    nhs_number_hash = models.CharField(
        null=False, max_length=128, db_index=True, editable=False, unique=True
    )
    subscription_id = models.UUIDField(
        null=False, max_length=64, db_index=True, unique=True, editable=False
    )
    provider_reference_id = models.CharField(
        null=False, max_length=128, db_index=True, unique=True, help_text="XXX12345678"
    )

    def __str__(self):
        return f'"{self.provider_reference_id}" ({self.care_provider_location})'
