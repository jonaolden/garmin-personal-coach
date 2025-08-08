"""
LLM Module

Builds prompts, calls the OpenAI API, and validates responses using Pydantic
to propose training plan revisions.
"""

import json
from typing import Any, Dict, List, Optional

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.monitoring import log_event  # Assuming monitoring module is available
from src.settings import Settings  # Import Settings class


# Pydantic model for a single JSON Patch operation
class JsonPatchOperation(BaseModel):
    op: str = Field(
        ...,
        description="The type of operation (e.g., 'add', 'remove', 'replace', 'move', 'copy', 'test')",
    )
    path: str = Field(..., description="The JSON Pointer to the target location")
    value: Optional[Any] = Field(
        None,
        description="The value to add, replace, or test (for 'add', 'replace', 'test' operations)",
    )
    from_: Optional[str] = Field(
        None,
        alias="from",
        description="The JSON Pointer to the source location (for 'move', 'copy' operations)",
    )
    model_config = ConfigDict(populate_by_name=True)


# Pydantic model for the expected LLM response (a list of JSON Patch operations)
class TrainingPlanRevision(BaseModel):
    revision: List[JsonPatchOperation] = Field(
        ...,
        description="A list of RFC6902 JSON Patch operations to apply to the training plan.",
    )


def build_prompt(current_plan_yaml: str, flags: Dict[str, Any]) -> str:
    """
    Builds the prompt for the LLM based on the current plan and analytics flags.
    Args:
        current_plan_yaml (str): The current training plan in YAML format.
        flags (Dict[str, Any]): Dictionary of flags indicating areas for revision.
    Returns: str: The formatted prompt string.
    """
    prompt = f"""
You are an AI assistant specializing in optimizing training plans based on an athlete's recent performance and physiological data.
You will be provided with the athlete's current training plan in YAML format and a set of flags indicating potential issues or areas for adjustment.
Your task is to propose revisions to the training plan in RFC6902 JSON Patch format.

Current Training Plan (YAML):
```yaml
{current_plan_yaml}
```

Analytics Flags:
```json
{json.dumps(flags, indent=2)}
```

Based on the flags, propose specific, actionable changes to the training plan.
For example, if the 'high_atl_ctl_ratio' flag is true, you might propose reducing training volume or intensity in the coming week.
If the 'low_hrv' flag is true, you might suggest adding a rest day or reducing the intensity of planned workouts.
Consider all provided flags, including 'high_atl_ctl_ratio', 'low_hrv', and 'low_tsb', when formulating your revision.

Your response MUST be a JSON object containing a single key, "revision", whose value is a list of RFC6902 JSON Patch operations.
Do NOT include any other text or explanation in your response.
Ensure the JSON Patch operations are valid and target existing paths in the YAML structure.

Example Response:
```json
{{
  "revision": [
    {{ "op": "replace", "path": "/weeks/0/days/0/workout/intensity", "value": "easy" }},
    {{ "op": "add", "path": "/notes/-", "value": "Adjusted intensity due to low HRV" }}
  ]
}}
```
"""
    return prompt


def propose_revision(
    current_plan_yaml: str, flags: Dict[str, Any], settings: Settings
) -> str:
    """
    Proposes a training plan revision based on the current plan and analytics flags using an LLM.
    Args:
        current_plan_yaml (str): The current training plan in YAML format.
        flags (Dict[str, Any]): Dictionary of flags indicating areas for revision.
        settings (Settings): The application settings object.
    Returns: str: An RFC6902 JSON Patch string representing the proposed changes, or an empty string on failure.
    """
    log_event("llm_propose_revision_start", {"flags": flags})

    if not settings.openai_api_key:  # Assuming openai_api_key is in settings
        log_event(
            "llm_propose_revision_error", {"error": "OpenAI API key not configured."}
        )
        print("Error: OpenAI API key not configured.")
        return "[]"

    client = OpenAI(api_key=settings.openai_api_key)  # Initialize OpenAI client

    prompt = build_prompt(current_plan_yaml, flags)
    print("LLM prompt built.")
    # print(prompt) # Uncomment for debugging

    try:
        # TODO: Make model and other parameters configurable via settings
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Or another suitable model
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides training plan revisions in RFC6902 JSON Patch format.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},  # Request JSON object output
        )

        # Assuming the response structure is response.choices[0].message.content
        llm_output_str = response.choices[0].message.content
        log_event("llm_propose_revision_response_received")
        # print("LLM Raw Response:") # Uncomment for debugging
        # print(llm_output_str) # Uncomment for debugging

        # Validate the response using Pydantic
        try:
            llm_output_json = json.loads(llm_output_str)
            validated_response = TrainingPlanRevision(**llm_output_json)
            json_patch = json.dumps(validated_response.revision)
            log_event("llm_propose_revision_success", {"patch": json_patch})
            print("LLM proposed revision (JSON Patch):", json_patch)
            return json_patch

        except json.JSONDecodeError as e:
            log_event(
                "llm_propose_revision_json_decode_error",
                {"error": str(e), "response": llm_output_str},
            )
            print(f"Error decoding LLM response JSON: {e}")
            print("Raw LLM response:", llm_output_str)
            return "[]"
        except ValidationError as e:
            log_event(
                "llm_propose_revision_validation_error",
                {"error": str(e), "response": llm_output_str},
            )
            print(f"LLM response validation failed: {e}")
            print("Raw LLM response:", llm_output_str)
            return "[]"

    except Exception as e:
        log_event("llm_propose_revision_api_error", {"error": str(e)})
        print(f"Error calling OpenAI API: {e}")
        return "[]"


# Pydantic models, OpenAI integration, prompt building, validation, and JSON Patch formatting implemented.
# TODO: Add openai_api_key to settings model and load it.
# TODO: Handle potential API errors more gracefully (e.g., rate limits, invalid key).
# TODO: Make LLM model and other parameters configurable via settings.
