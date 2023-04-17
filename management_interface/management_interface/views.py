from http import HTTPStatus

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from fhir.resources.contactpoint import ContactPoint
from fhir.resources.operationoutcome import OperationOutcome, OperationOutcomeIssue
from fhir.resources.organization import Organization

from .models import CareProviderLocation


def failure_response(status, code, diagnostics):
    operation_outcome_issue = OperationOutcomeIssue(
        severity="error",
        code=code,
        diagnostics=diagnostics,
    )
    operation_outcome = OperationOutcome(issue=[operation_outcome_issue])
    return JsonResponse(operation_outcome.dict(), status=status)


@csrf_exempt
def care_provider_search(request):
    if request.method == "POST":
        try:
            nhs_number_hash = request.POST["_careRecipientPseudoId"]
        except KeyError:
            return failure_response(
                status=HTTPStatus.BAD_REQUEST,
                code="required",
                diagnostics="Required search parameter was missing: _careRecipientPseudoId",
            )

        try:
            care_provider = CareProviderLocation.objects.get(
                carerecipient__nhs_number_hash=nhs_number_hash
            )
        except CareProviderLocation.DoesNotExist:
            return failure_response(
                status=HTTPStatus.NOT_FOUND,
                code="not-found",
                diagnostics="No subscription was found on the system for the given pseudonymous identifier",
            )

        fhir_contact_point = ContactPoint(
            system="email", value=care_provider.email, use="work"
        )
        fhir_organization = Organization(
            name=care_provider.name, telecom=[fhir_contact_point]
        )
        return JsonResponse(fhir_organization.dict())

    # if not allowed method was used on this endpoint
    else:
        return failure_response(
            status=HTTPStatus.METHOD_NOT_ALLOWED,
            code="not-allowed",
            diagnostics="Method not allowed - _search only supports POST",
        )
