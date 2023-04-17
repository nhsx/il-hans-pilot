from unittest import mock
from unittest.mock import MagicMock
from uuid import uuid4

from django.test import TestCase

from .forms import CareRecipientForm
from .models import CareProviderLocation, RegisteredManager


class CareRecipientFormTests(TestCase):
    def setUp(self):
        self.registered_manager = RegisteredManager.objects.create(
            given_name="Jared", family_name="Jaredsky"
        )
        self.location = CareProviderLocation.objects.create(
            name="Test Location", registered_manager_id=self.registered_manager.pk
        )

    def test_form_displays_necessary_fields(self):
        form = CareRecipientForm()
        form_html_lowered = str(form).lower()
        assert "family name" in form_html_lowered
        assert "given name" in form_html_lowered
        assert "nhs number" in form_html_lowered
        assert "birth" in form_html_lowered

    def test_creating_care_recipient(self):
        subscription_id = uuid4()
        with mock.patch.object(
            CareRecipientForm,
            CareRecipientForm._create_subscription.__name__,
            MagicMock(return_value=subscription_id),
        ) as _create_subscription_mocked:
            form = CareRecipientForm(
                data=dict(
                    provider_reference_id="PRVDRFID",
                    given_name="John",
                    family_name="Doe",
                    nhs_number="123456789",
                    care_provider_location=self.location.pk,
                    birth_date="1990-01-01",
                )
            )
            assert not form.errors
            assert form.is_valid()

        assert _create_subscription_mocked.call_count == 1

    def test_cannot_create_multiple_care_recipients_with_the_same_nhs_number(self):
        subscription_id = uuid4()

        with mock.patch.object(
            CareRecipientForm,
            CareRecipientForm._create_subscription.__name__,
            MagicMock(return_value=subscription_id),
        ) as _create_subscription_mocked:
            form = CareRecipientForm(
                data=dict(
                    provider_reference_id="PRVDRFID",
                    given_name="John",
                    family_name="Doe",
                    nhs_number="123456789",
                    care_provider_location=self.location.pk,
                    birth_date="1990-01-01",
                )
            )
            assert form.is_valid()
            form.save()

            form2 = CareRecipientForm(
                data=dict(
                    provider_reference_id="RANDOM_REFERENCE_ID",
                    given_name="John",
                    family_name="Doe",
                    nhs_number="123456789",
                    care_provider_location=self.location.pk,
                    birth_date="1990-01-01",
                )
            )
            assert not form2.is_valid()
            assert "already exists" in str(form2.errors)
            assert "PRVDRFID" in str(form2.errors)
