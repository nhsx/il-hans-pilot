from uuid import uuid4

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import CareProviderLocation, CareRecipient, RegisteredManager


def assert_rejects_email(obj, email):
    obj.email = email
    try:
        obj.full_clean()
    except ValidationError as e:
        assert "email" in e.message_dict
        assert "Enter an nhs.net email address" in e.message_dict["email"]


def assert_accepts_email(obj, email):
    obj.email = email
    try:
        obj.full_clean()
    except ValidationError as e:
        assert "email" not in e.message_dict


def create_registered_manager():
    return RegisteredManager(
        given_name="Jehosephat",
        family_name="McGibbons",
        cqc_registered_manager_id="My CQC Registered Manager ID",
    )


def create_care_provider_location(manager=None):
    return CareProviderLocation(
        registered_manager_id=manager.id if (manager and manager.id) else None,
        name="My Location Name",
        email="nosuchaddress@nhs.net",
        ods_code="My Ods Code",
        cqc_location_id="My CQC Location ID",
    )


class RegisteredManagerTests(TestCase):
    def test_rejects_bad_email_domain(self):
        assert_rejects_email(RegisteredManager(), "bad-man@invalid-domain.evil")

    def test_accepts_safe_email_domain(self):
        assert_accepts_email(RegisteredManager(), "good-dr@nhs.net")

    def test_rejects_invalid_email_address_format(self):
        manager = RegisteredManager(email="notanemail.address")
        try:
            manager.full_clean()
        except ValidationError as e:
            assert "email" in e.message_dict

    def test_accepts_data_fields(self):
        manager = create_registered_manager()

        try:
            manager.full_clean()
        except ValidationError as e:
            assert "given_name" not in e.message_dict
            assert "first_name" not in e.message_dict
            assert "cqc_registered_manager_id" not in e.message_dict

    def test_str_method(self):
        manager = create_registered_manager()
        self.assertEqual(
            str(manager), "McGibbons, Jehosephat (My CQC Registered Manager ID)"
        )


class CareProviderLocationTests(TestCase):
    def test_rejects_bad_email_domain(self):
        assert_rejects_email(CareProviderLocation(), "bad-man@invalid-domain.evil")

    def test_accepts_safe_email_domain(self):
        assert_accepts_email(CareProviderLocation(), "good-dr@nhs.net")

    def test_rejects_invalid_email_address_format(self):
        assert_rejects_email(CareProviderLocation(), "notanemail.address")

    def test_accepts_data_fields(self):
        location = create_care_provider_location()

        try:
            location.full_clean()
        except ValidationError as e:
            assert "name" not in e.message_dict
            assert "ods_code" not in e.message_dict
            assert "cqc_location_id" not in e.message_dict

    def test_wont_save_without_a_manager(self):
        location = create_care_provider_location()
        with self.assertRaises(Exception):
            location.save()

    def test_saves_with_a_manager(self):
        manager = create_registered_manager()
        manager.save()
        location = create_care_provider_location(manager=manager)
        location.save()

    def test_str_method(self):
        manager = create_registered_manager()
        manager.save()
        location = create_care_provider_location(manager=manager)
        self.assertEqual(str(location), "My Location Name")


class CareRecipientTests(TestCase):
    def create_registered_manager_object(self):
        return RegisteredManager.objects.create(
            given_name="Jehosephat",
            family_name="McGibbons",
            cqc_registered_manager_id="My CQC Registered Manager ID",
        )

    def create_care_provider_location_object(self, manager):
        return manager.careproviderlocation_set.create(
            name="My Location Name",
            email="nosuchaddress@nhs.net",
            ods_code="My Ods Code",
            cqc_location_id="My CQC Location ID",
        )

    def test_nhs_number_hash_gets_saved(self):
        manager = RegisteredManager.objects.create(
            given_name="Jehosephat",
            family_name="McGibbons",
            cqc_registered_manager_id="My CQC RegsiteredManagerID",
        )
        location = manager.careproviderlocation_set.create(
            name="My Location Name",
            email="nosuchaddress@nhs.net",
            ods_code="My Ods Code",
            cqc_location_id="My CQC Location ID",
        )
        jeff = location.carerecipient_set.create(
            subscription_id=uuid4(), provider_reference_id="foobar"
        )
        jeff.nhs_number = "password"
        jeff.save()

        jeff_comparison = CareRecipient.objects.get(pk=jeff.id)
        self.assertEquals(jeff.nhs_number_hash, jeff_comparison.nhs_number_hash)

    def test_str_method(self):
        manager = self.create_registered_manager_object()
        location = self.create_care_provider_location_object(manager=manager)
        jeff = CareRecipient(
            care_provider_location=location,
            subscription_id=uuid4(),
            provider_reference_id="foobar",
        )
        jeff.nhs_number = "password"
        jeff.save()
        self.assertEqual(str(jeff), '"foobar" (My Location Name)')
