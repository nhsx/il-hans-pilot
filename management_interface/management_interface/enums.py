from enum import Enum


class CSVImportMessages(str, Enum):
    FILE_CORRUPTED_OR_BINARY = "The CSV file is corrupted or binary"
    INVALID_OR_EMPTY_FILE = "You must provide a valid CSV file"
    INVALID_COLUMN_SET = (
        "You must provide a valid CSV file with the following columns: "
        "NHS_NUMBER, BIRTH_DATE, FAMILY_NAME, GIVEN_NAME, PROVIDER_REFERENCE_ID"
    )
    LINE_COUNT_EXCEEDED = "The CSV file line count exceeds maximum number of lines"
    FILE_IMPORTED_SUCCESSFULLY = "Your CSV file has been imported. New Care Recipients created"
