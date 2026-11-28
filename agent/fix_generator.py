
import json
import difflib
import subprocess
import shutil

from pathlib import Path

from agent.gemini_client import generate_gemini_response
from agent.investigator import parse_json_response
from agent.prompts import FIX_GENERATION_PROMPT


def validate_proposed_changes(changes, project_path):

    root = Path(project_path).resolve()

    if not isinstance(changes, list):
        return []

    if not shutil.which("git"):
        raise RuntimeError("Git is required for patch validation.")

    validated = []
    seen_files = set()

    for change in changes:

        if not isinstance(change, dict):
            continue

        filename = change.get("file", "")
        corrected_code = change.get("corrected_code", "")

        if not isinstance(filename, str):
            continue

        if not isinstance(corrected_code, str):
            continue

        if not filename.strip() or not corrected_code.strip():
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

        # Protect existing test files
        if (
            target.name.lower().startswith("test_")
            or target.stem.lower().endswith("_test")
            or any(
                part.lower() in {"tests", "test", "__tests__"}
                for part in relative_path.parts
            )
        ):
            continue

        if target in seen_files:
            continue

        try:
            original_code = target.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue

        # Normalize line endings
        corrected_code = corrected_code.replace(
            "\r\n", "\n"
        ).replace("\r", "\n")

        if not corrected_code.endswith("\n"):
            corrected_code += "\n"

        if original_code == corrected_code:
            continue

        # Validate Python syntax
        if target.suffix.lower() == ".py":
            try:
                compile(
                    corrected_code,
                    filename,
                    "exec"
                )
            except SyntaxError:
                print(f"Invalid Python syntax: {filename}")
                continue

        # Generate unified diff using Python
        file_path = relative_path.as_posix()

        diff = "".join(
            difflib.unified_diff(
                original_code.splitlines(keepends=True),
                corrected_code.splitlines(keepends=True),
                fromfile=file_path,
                tofile=file_path,
                n=3
            )
        )

        if not diff.strip():
            continue

        # Ensure the patch ends with a newline
        diff = diff.rstrip("\r\n") + "\n"

        # Check patch applicability without modifying files
        try:
            check = subprocess.run(
                [
                    "git",
                    "apply",
                    "-p0",
                    "--check",
                    "-"
                ],
                cwd=root,
                input=diff.encode("utf-8"),
                capture_output=True,
                timeout=15
            )

        except (OSError, subprocess.TimeoutExpired):
            print(f"Patch validation failed: {filename}")
            continue

        if check.returncode != 0:
            print(
                f"Invalid patch for {filename}: "
                + check.stderr.decode(
                    "utf-8",
                    errors="replace"
                )
            )
            continue

        validated.append({
            "file": file_path,
            "explanation": change.get(
                "explanation",
                "Proposed code correction"
            ),
            "unified_diff": diff
        })

        seen_files.add(target)

        print(f"Patch validated successfully: {filename}")

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
