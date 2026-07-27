"""
Extraction result validator for Bedrock-generated output.

Validates that the raw dictionary from Bedrock contains all seven required keys
before constructing an ExtractionResult instance.

This module:
  - Performs NO logging
  - Performs NO file access
  - Performs NO network access
  - Performs NO AWS calls
  - Performs NO environment-variable access
  - Does NOT mutate raw_dict
  - Does NOT silently invent defaults for missing keys
  - Never includes the complete raw payload in exception messages

Property 2: Bedrock extraction validation accepts iff all required keys present.
Requirements: 1.3, 1.6
"""

from applications_function.models import ExtractionResult


# ---------------------------------------------------------------------------
# Required keys — all seven must be present (value may be None)
# ---------------------------------------------------------------------------

REQUIRED_KEYS: frozenset[str] = frozenset({
    "jobTitle",
    "company",
    "location",
    "skills",
    "responsibilities",
    "languages",
    "experienceLevel",
})


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class ExtractionValidationError(Exception):
    """
    Raised when one or more required keys are missing from the extraction result.

    Attributes:
        missing_keys: The set of key names that were absent from the input dict.
    """

    def __init__(self, missing_keys: set[str]) -> None:
        # Safe message: lists only the missing KEY NAMES, never the raw payload
        self.missing_keys = missing_keys
        keys_str = ", ".join(sorted(missing_keys))
        super().__init__(f"Missing required keys: {keys_str}")


# ---------------------------------------------------------------------------
# Validator
# ---------------------------------------------------------------------------

def validate_extraction_result(raw_dict: dict) -> ExtractionResult:
    """
    Validate a raw dictionary and return an ExtractionResult instance.

    Args:
        raw_dict: The raw structured extraction result (e.g., from Bedrock JSON
                  parsing). This dictionary is NOT mutated.

    Returns:
        An ExtractionResult instance with all seven fields populated.
        Null values are preserved for Optional[str] fields; None is converted
        to an empty list for list[str] fields (type safety).

    Raises:
        ExtractionValidationError: When one or more required keys are missing
            from raw_dict. A missing key is one that is NOT present in the dict
            at all — a key with value None is considered present and valid.

    Notes:
        - Missing key: ``"jobTitle" not in raw_dict`` → error
        - Present with None: ``raw_dict["jobTitle"] is None`` → valid, preserved
        - This distinction is critical: the user can see that Bedrock returned
          null for a field and decide what to do, vs. Bedrock failing to return
          the field entirely (which indicates a schema violation).
    """
    # 1. Check for missing keys (do NOT mutate raw_dict)
    present_keys = set(raw_dict.keys())
    missing = REQUIRED_KEYS - present_keys

    if missing:
        raise ExtractionValidationError(missing_keys=missing)

    # 2. Build ExtractionResult from the raw dict
    #    - Optional[str] fields: preserve None as-is
    #    - list[str] fields: convert None to [] for type safety
    return ExtractionResult(
        jobTitle=raw_dict["jobTitle"],
        company=raw_dict["company"],
        location=raw_dict["location"],
        skills=raw_dict["skills"] if raw_dict["skills"] is not None else [],
        responsibilities=raw_dict["responsibilities"] if raw_dict["responsibilities"] is not None else [],
        languages=raw_dict["languages"] if raw_dict["languages"] is not None else [],
        experienceLevel=raw_dict["experienceLevel"],
    )
