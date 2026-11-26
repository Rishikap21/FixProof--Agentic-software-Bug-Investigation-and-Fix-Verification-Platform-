
import json

from pathlib import Path

from agent.gemini_client import generate_gemini_response
from agent.investigator import parse_json_response
from agent.prompts import FIX_GENERATION_PROMPT


def validate_proposed_changes(changes, project_path):

    root = Path(project_path).resolve()

    if not isinstance(changes, list):
        return []

    validated = []

    for change in changes:

        if not isinstance(change, dict):
            continue

        filename = change.get("file", "")
        diff = change.get("unified_diff", "")

        if not isinstance(filename, str):
            continue

        if not isinstance(diff, str):
            continue

        relative_path = Path(filename)

        if relative_path.is_absolute():
            continue

        if ".." in relative_path.parts:
            continue

        target = (root / relative_path).resolve()

        if not target.is_relative_to(root):
            continue

        if not target.is_file():
            continue

        if target.suffix.lower() not in {
            ".py", ".java", ".js", ".ts",
            ".jsx", ".tsx", ".html", ".css", ".sql"
        }:
            continue

        if not diff.strip():
            continue

        validated.append({
            "file": relative_path.as_posix(),
            "explanation": change.get(
                "explanation",
                "Proposed code correction"
            ),
            "unified_diff": diff
        })

    return validated


def generate_fix(
    bug_description,
    bug_category,
    investigation,
    project_context,
    project_path
):

    prompt = FIX_GENERATION_PROMPT.format(
        bug_description=bug_description,
        bug_category=bug_category,
        investigation=json.dumps(
            investigation,
            indent=2
        ),
        project_context=project_context
    )

    response_text = generate_gemini_response(prompt)

    result = parse_json_response(response_text)

    if not isinstance(result, dict):
        raise ValueError(
            "Invalid fix generation response."
        )

    if "proposed_changes" not in result:
        result["proposed_changes"] = []

    result["proposed_changes"] = validate_proposed_changes(
        result["proposed_changes"],
        project_path
    )

    result["requires_human_review"] = True

    result["status"] = (
        "PATCH_PROPOSED"
        if result["proposed_changes"]
        else "NO_SAFE_PATCH"
    )

    return result
