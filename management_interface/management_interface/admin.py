import csv
from io import TextIOWrapper
from typing import Iterable, List, Tuple, TypedDict
from uuid import UUID

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.html import format_html
from internal_integrations.management_api.client import ManagementAPIClient
from internal_integrations.management_api.exceptions import ManagementAPIClientError

from .configuration import SETTINGS
from .enums import CSVImportMessages
from .forms import CareProviderLocationForm, CareRecipientForm, RegisteredManagerForm
from .models import CareProviderLocation, CareRecipient, RegisteredManager


class _CareRecipientRecord(TypedDict):
    provider_reference_id: str
    given_name: str
    family_name: str
    nhs_number: str
    birth_date: str


def set_obj_created_updated(request, obj, form):
    """
    Updates created_by and updated_by fields if the object was created or changed in admin
    """
    if form.changed_data and obj.created_by:
        obj.updated_by = request.user

    if not obj.created_by:
        obj.created_by = request.user
    return obj


@admin.register(CareRecipient)
class CareRecipientAdmin(admin.ModelAdmin):
    search_fields = (
        "nhs_number_hash",
        "provider_reference_id",
    )
    list_filter = ("care_provider_location_id",)
    list_display = [
        "provider_reference_id",
        "care_provider_location_name",
        "updated_at",
        "updated_by",
    ]
    form = CareRecipientForm

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj=obj)
        if obj is not None:
            fields_to_hide = {"given_name", "family_name", "nhs_number", "birth_date"}
            return [field for field in fields if field not in fields_to_hide]

        return fields

    def care_provider_location_name(self, obj):
        return obj.care_provider_location.name

    def save_model(self, request, obj, form, change):
        obj = set_obj_created_updated(request, obj, form)
        super().save_model(request, obj, form, change)

    def delete_queryset(self, request, queryset: Iterable[CareRecipient]):
        for care_recipient in queryset:
            try:
                ManagementAPIClient().delete_subscription(
                    care_recipient.subscription_id
                )
                care_recipient.delete()
                self.message_user(
                    request,
                    f"{care_recipient} was deleted successfully",
                    level=messages.INFO,
                )
            except ManagementAPIClientError as ex:
                self.message_user(
                    request,
                    f"Could not delete {care_recipient}: {str(ex)}",
                    level=messages.ERROR,
                )

    def delete_model(self, request, obj):
        return self.delete_queryset(request, [obj])

    def message_user(
        self, request, message, level=messages.INFO, extra_tags="", fail_silently=False
    ):
        """
        Django Admin's adds success message by default, which will be confusing
        if only a subset of the objects were deleted successfully. We intercept these default messages
        and take control of messages ourselves.
        """
        if message.startswith("Successfully deleted"):
            return None

        if message.startswith("The") and message.endswith("was deleted successfully."):
            return None

        super().message_user(request, message, level, extra_tags, fail_silently)

    def has_change_permission(self, *args, **kwargs):
        return False


@admin.register(RegisteredManager)
class RegisteredManagerAdmin(admin.ModelAdmin):
    form = RegisteredManagerForm

    def save_model(self, request, obj, form, change):
        obj = set_obj_created_updated(request, obj, form)
        super().save_model(request, obj, form, change)


@admin.register(CareProviderLocation)
class CareProviderLocationAdmin(admin.ModelAdmin):
    form = CareProviderLocationForm
    list_display = (
        "name",
        "bulk_import_button",
    )

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "import_care_recipients/<uuid:care_provider_location_id>",
                self.admin_site.admin_view(self.import_care_recipients),
                name="import_care_recipients",
            ),
        ]
        return my_urls + urls

    def import_care_recipients(self, request, care_provider_location_id: UUID):
        context = dict(
            self.admin_site.each_context(request),
        )
        if request.method == "POST":
            if not self._is_csv_in_request_files(request):
                messages.error(
                    request, message=f"{CSVImportMessages.INVALID_OR_EMPTY_FILE}"
                )
                return redirect("..")

            csv_file = TextIOWrapper(
                request.FILES["csvfile"].file, encoding="utf-8", errors="replace"
            )
            try:
                # because it's not possible to rewind the reader, it's better to store its contents in list for
                # multiple iterations
                csv_data = []
                for row in csv.DictReader(csv_file, delimiter=","):
                    csv_data.append(_CareRecipientRecord(**{k.lower(): v for k, v in row.items()}))  # type: ignore
            except csv.Error:
                messages.error(
                    request, message=f"{CSVImportMessages.FILE_CORRUPTED_OR_BINARY}"
                )
                return redirect("..")

            if not self._is_csv_column_set_valid(csv_data):
                messages.error(
                    request, message=f"{CSVImportMessages.INVALID_COLUMN_SET}"
                )
                return redirect("..")

            if not self._is_csv_line_count_valid(csv_data):
                messages.error(
                    request,
                    message=f"{CSVImportMessages.LINE_COUNT_EXCEEDED}: {SETTINGS.CSV_IMPORT_MAX_LINES}",
                )
                return redirect("..")

            created_care_recipients, errors = self._bulk_create_care_recipients(
                csv_data=csv_data,
                care_provider_location_id=care_provider_location_id,
            )
            messages.info(
                request,
                message=f"{CSVImportMessages.FILE_IMPORTED_SUCCESSFULLY}: {len(created_care_recipients)}",
            )
            for provider_reference_id, error in errors:
                try:
                    raise error
                except IntegrityError:
                    messages.warning(
                        request,
                        message=f"{provider_reference_id}: already exists",
                    )
                except ValidationError as exc:
                    messages.error(
                        request,
                        message=f"{provider_reference_id}: {exc.message}",
                    )

            return redirect("..")

        return TemplateResponse(request, "csv_form.html", context)

    def bulk_import_button(self, obj):
        return format_html(
            "<a href='{}' class='addlink'>{}</a>",
            f"import_care_recipients/{obj.id}",
            f"Import Care Recipients to {obj.name}",
        )

    bulk_import_button.short_description = "Import Care Recipients"  # type: ignore

    def save_model(self, request, obj, form, change):
        obj = set_obj_created_updated(request, obj, form)
        super().save_model(request, obj, form, change)

    def _is_csv_in_request_files(self, request) -> bool:
        return "csvfile" in request.FILES

    def _is_csv_line_count_valid(self, csv_data_list) -> bool:
        return len(csv_data_list) <= SETTINGS.CSV_IMPORT_MAX_LINES

    def _is_csv_column_set_valid(self, csv_data_list) -> bool:
        return set(_CareRecipientRecord.__annotations__) == set(csv_data_list[0])

    def _bulk_create_care_recipients(
        self, csv_data: List[_CareRecipientRecord], care_provider_location_id: UUID
    ) -> (List[CareRecipient], Tuple[str, Exception]):  # type: ignore
        created_care_recipients = []
        errors: List = []
        for counter, care_recipient_record in enumerate(csv_data):
            form = CareRecipientForm(
                data=dict(
                    care_provider_location=care_provider_location_id,
                    **care_recipient_record,
                )
            )
            if form.errors:
                if form.non_field_errors().data:
                    errors.extend(
                        (
                            f"{care_recipient_record['provider_reference_id']} (line {counter})",
                            error,
                        )
                        for error in form.non_field_errors().data
                    )
                for field in form.errors:
                    error_message = (
                        f"Field: {field}, error(s): {' '.join(form.errors[field])}"
                    )
                    errors.append(
                        (
                            f"{care_recipient_record['provider_reference_id']} (line {counter})",
                            ValidationError(error_message),
                        )
                    )
                continue

            try:
                care_recipient = form.save()
                created_care_recipients.append(care_recipient)
            except IntegrityError as exc:
                errors.append(
                    (
                        f"{care_recipient_record['provider_reference_id']} (line {counter})",
                        exc,
                    )
                )

        return created_care_recipients, errors
