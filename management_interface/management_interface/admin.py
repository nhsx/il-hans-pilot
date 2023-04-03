import csv
from io import TextIOWrapper

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
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
    list_display = ["provider_reference_id", "care_provider_location_name", "updated_at", "updated_by"]
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

    def _is_csv_in_request_files(self, request) -> bool:
        return "csvfile" in request.FILES

    def _is_csv_line_count_valid(self, csv_data_list) -> bool:
        return len(csv_data_list) <= SETTINGS.CSV_IMPORT_MAX_LINES

    def _is_csv_column_set_valid(self, csv_data_list) -> bool:
        required_columns = ["NHS_NUMBER", "DOB", "FAMILY_NAME", "GIVEN_NAME", "PROVIDER_REFERENCE"]
        for column in required_columns:
            if column not in csv_data_list[0]:
                return False
        return True

    def _create_bulk_care_recipients(self, csv_data_list, careproviderlocation_id, user_id) -> int:
        care_recipient_created_count = 0
        care_provider_location = CareProviderLocation.objects.get(pk=careproviderlocation_id)
        for care_recipient_dict in csv_data_list:
            if not CareRecipient.objects.filter(
                provider_reference_id=care_recipient_dict["PROVIDER_REFERENCE"]
            ).exists():
                care_recipient = CareRecipient(
                    care_provider_location=care_provider_location,
                    nhs_number=care_recipient_dict["NHS_NUMBER"],
                    provider_reference_id=care_recipient_dict["PROVIDER_REFERENCE"],
                    created_by_id=user_id,
                )
                try:
                    care_recipient.full_clean()
                    care_recipient.save()
                except ValidationError:
                    pass  # add some logging here

                if care_recipient.pk:
                    care_recipient_created_count += 1
        return care_recipient_created_count

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "import_care_recipients/<careproviderlocation_id>",
                self.admin_site.admin_view(self.import_care_recipients),
                name="import_care_recipients",
            ),
        ]
        return my_urls + urls

    def import_care_recipients(self, request, careproviderlocation_id):
        context = dict(
            self.admin_site.each_context(request),
        )
        if request.method == "POST":

            if not self._is_csv_in_request_files(request):
                messages.error(request, message=f"{CSVImportMessages.INVALID_OR_EMPTY_FILE}")
                return redirect("..")

            csv_file = TextIOWrapper(request.FILES["csvfile"].file, encoding="utf-8 ", errors="replace")
            try:
                reader = csv.DictReader(csv_file, delimiter=",")
                # because it's not possible to rewind the reader, it's better to store its contents in list for
                # multiple iterations
                csv_data = []
                for line in reader:
                    csv_data.append(line)
            except csv.Error:
                messages.error(request, message=f"{CSVImportMessages.FILE_CORRUPTED_OR_BINARY}")
                return redirect("..")

            if not self._is_csv_column_set_valid(csv_data):
                messages.error(request, message=f"{CSVImportMessages.INVALID_COLUMN_SET}")
                return redirect("..")

            if not self._is_csv_line_count_valid(csv_data):
                messages.error(
                    request, message=f"{CSVImportMessages.LINE_COUNT_EXCEEDED}: {SETTINGS.CSV_IMPORT_MAX_LINES}"
                )
                return redirect("..")

            care_recipient_created_count = self._create_bulk_care_recipients(
                csv_data_list=csv_data, careproviderlocation_id=careproviderlocation_id, user_id=request.user.id
            )
            messages.info(
                request, message=f"{CSVImportMessages.FILE_IMPORTED_SUCCESSFULLY}: {care_recipient_created_count}"
            )
            return redirect("..")

        return TemplateResponse(request, "csv_form.html", context)

    def bulk_import_button(self, obj):
        return format_html(
            "<a href='{}' class='addlink'>{}</a>",
            f"import_care_recipients/{obj.id}",
            f"Import Care Recipients to {obj.name}",
        )

    def save_model(self, request, obj, form, change):
        obj = set_obj_created_updated(request, obj, form)
        super().save_model(request, obj, form, change)

    bulk_import_button.short_description = "Import Care Recipients"  # type: ignore
    list_display = (
        "name",
        "bulk_import_button",
    )
