import csv
from io import TextIOWrapper
from typing import List, Tuple, TypedDict
from uuid import UUID

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path
from django.utils.html import format_html

from .configuration import SETTINGS
from .enums import CSVImportMessages
from .forms import CareProviderLocationForm, CareRecipientForm, RegisteredManagerForm
from .models import CareProviderLocation, CareRecipient, RegisteredManager


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

    def care_provider_location_name(self, obj):
        return obj.care_provider_location.name

    def save_model(self, request, obj, form, change):
        obj = set_obj_created_updated(request, obj, form)
        super().save_model(request, obj, form, change)


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
                    csv_data.append(
                        _CareRecipientRecord(**{k.lower(): v for k, v in row.items()})
                    )
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
        self, csv_data: List["_CareRecipientRecord"], care_provider_location_id: UUID
    ) -> (List[CareRecipient], Tuple[str, Exception]):
        created_care_recipients, errors = [], []
        for care_recipient_record in csv_data:
            form = CareRecipientForm(
                data=dict(
                    care_provider_location=care_provider_location_id,
                    **care_recipient_record,
                )
            )
            if form.errors:
                errors.extend(
                    (care_recipient_record["provider_reference_id"], error)
                    for error in form.non_field_errors().data
                )
                continue

            try:
                care_recipient = form.save()
                created_care_recipients.append(care_recipient)
            except IntegrityError as exc:
                errors.append((care_recipient_record["provider_reference_id"], exc))

        return created_care_recipients, errors


class _CareRecipientRecord(TypedDict):
    provider_reference_id: str
    given_name: str
    family_name: str
    nhs_number: str
    birth_date: str
