import os
import random
from unittest import mock
from unittest.mock import MagicMock
from uuid import uuid4

from django.contrib.admin import AdminSite
from django.test import TestCase

from internal_integrations.management_api.client import ManagementAPIClient
from internal_integrations.management_api.exceptions import ManagementAPIClientError
from .admin import CareRecipientAdmin
from .models import CareProviderLocation, RegisteredManager, CareRecipient


@mock.patch.dict(os.environ, {"MANAGEMENT_API_BASE_URL": "http://tests"})
class CareRecipientAdminTests(TestCase):
    def setUp(self):
        self.care_recipient_admin = CareRecipientAdmin(
            model=CareRecipient, admin_site=AdminSite()
        )
        self.registered_manager = RegisteredManager.objects.create(
            given_name="Jared", family_name="Jaredsky"
        )
        self.location = CareProviderLocation.objects.create(
            name="Test Location", registered_manager_id=self.registered_manager.pk
        )

    def test_delete_care_recipient__single_object__removal_is_successful(self):
        care_recipient = CareRecipient.objects.create(
            care_provider_location=self.location,
            nhs_number_hash="1234567",
            subscription_id=uuid4(),
            provider_reference_id="AX812938",
        )
        with mock.patch.object(
            ManagementAPIClient,
            ManagementAPIClient.delete_subscription.__name__,
            MagicMock(return_value=None),
        ) as delete_subscription_mocked:
            self.care_recipient_admin.delete_model(
                request=MagicMock(), obj=care_recipient
            )

        assert delete_subscription_mocked.call_count == 1
        assert CareRecipient.objects.count() == 0

    def test_delete_care_recipient__single_object__removal_is_unsuccessful(self):
        care_recipient = CareRecipient.objects.create(
            care_provider_location=self.location,
            nhs_number_hash="1234567",
            subscription_id=uuid4(),
            provider_reference_id="AX812938",
        )
        with mock.patch.object(
            ManagementAPIClient,
            ManagementAPIClient.delete_subscription.__name__,
            MagicMock(side_effect=ManagementAPIClientError),
        ) as delete_subscription_mocked:
            self.care_recipient_admin.delete_model(
                request=MagicMock(), obj=care_recipient
            )

        assert delete_subscription_mocked.call_count == 1
        assert CareRecipient.objects.count() == 1

    def test_delete_care_recipient__multiple_objects__removal_is_successful(self):
        [
            CareRecipient.objects.create(
                care_provider_location=self.location,
                nhs_number_hash=str(random.randint(10000000, 99999999)),
                subscription_id=uuid4(),
                provider_reference_id=f"AX{random.randint(10000, 99999)}",
            )
            for _ in range(3)
        ]
        with mock.patch.object(
            ManagementAPIClient,
            ManagementAPIClient.delete_subscription.__name__,
            MagicMock(return_value=None),
        ) as delete_subscription_mocked:
            self.care_recipient_admin.delete_queryset(
                request=MagicMock(), queryset=CareRecipient.objects.get_queryset()
            )

        assert delete_subscription_mocked.call_count == 3
        assert CareRecipient.objects.count() == 0

    def test_delete_care_recipient__multiple_objects__removal_is_unsuccessful(self):
        [
            CareRecipient.objects.create(
                care_provider_location=self.location,
                nhs_number_hash=str(random.randint(10000000, 99999999)),
                subscription_id=uuid4(),
                provider_reference_id=f"AX{random.randint(10000, 99999)}",
            )
            for _ in range(3)
        ]
        with mock.patch.object(
            ManagementAPIClient,
            ManagementAPIClient.delete_subscription.__name__,
            MagicMock(side_effect=ManagementAPIClientError),
        ) as delete_subscription_mocked:
            self.care_recipient_admin.delete_queryset(
                request=MagicMock(), queryset=CareRecipient.objects.get_queryset()
            )

        assert delete_subscription_mocked.call_count == 3
        assert CareRecipient.objects.count() == 3

    def test_delete_care_recipient__multiple_objects__removal_is_partially_successful(
        self,
    ):
        [
            CareRecipient.objects.create(
                care_provider_location=self.location,
                nhs_number_hash=str(random.randint(10000000, 99999999)),
                subscription_id=uuid4(),
                provider_reference_id=f"AX{random.randint(10000, 99999)}",
            )
            for _ in range(3)
        ]
        with mock.patch.object(
            ManagementAPIClient,
            ManagementAPIClient.delete_subscription.__name__,
            MagicMock(side_effect=[None, ManagementAPIClientError, None]),
        ) as delete_subscription_mocked:
            self.care_recipient_admin.delete_queryset(
                request=MagicMock(), queryset=CareRecipient.objects.get_queryset()
            )

        assert delete_subscription_mocked.call_count == 3
        assert CareRecipient.objects.count() == 1
