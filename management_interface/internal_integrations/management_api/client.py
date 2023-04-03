import uuid
from datetime import date
from typing import Optional, List

import requests
from fhir.resources.operationoutcome import OperationOutcome

from internal_integrations.management_api.exceptions import ManagementAPIClientError

from internal_integrations.management_api.settings import get_management_api_settings


class ManagementAPIClient:
    def __init__(
        self, base_url: Optional[str] = None, session: Optional[requests.Session] = None
    ):
        self.base_url = base_url or get_management_api_settings().base_url
        self.session = session or requests.Session()

    def create_subscription(
        self,
        patient_given_name: List[str],
        patient_family_name: str,
        nhs_number: str,
        birth_date: date,
    ) -> uuid.UUID:
        body = {
            "resourceType": "Patient",
            "identifier": [
                {
                    "system": "https://fhir.nhs.uk/Id/nhs-number",
                    "value": nhs_number,
                    "extension": [
                        {
                            "url": "https://fhir.hl7.org.uk/StructureDefinition/Extension-UKCore-NHSNumberVerificationStatus",
                            "valueCodeableConcept": {
                                "coding": [
                                    {
                                        "system": "https://fhir.hl7.org.uk/CodeSystem/UKCore-NHSNumberVerificationStatusEngland",
                                        "code": "03",
                                        "display": "Trace required",
                                    }
                                ]
                            },
                        }
                    ],
                }
            ],
            "name": [
                {
                    "use": "usual",
                    "family": patient_family_name,
                    "given": patient_given_name,
                }
            ],
            "birthDate": str(birth_date),
        }
        response = self.session.post(f"{self.base_url}/subscription", json=body)
        if response.status_code >= 400:
            operation_outcome = OperationOutcome(**response.json())
            raise ManagementAPIClientError(operation_outcome.issue[0].diagnostics)

        return uuid.UUID(response.headers.get("X-Subscription-Id"))
