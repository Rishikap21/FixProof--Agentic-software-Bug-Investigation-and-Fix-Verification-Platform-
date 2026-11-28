
import os
import json
import re

from pathlib import Path

from agent.gemini_client import generate_gemini_response
from agent.prompts import INVESTIGATION_PROMPT


ALLOWED_EXTENSIONS = {
    ".py", ".java", ".js", ".ts",
    ".jsx", ".tsx", ".html", ".css", ".sql"
}

IGNORED_DIRECTORIES = {
    "venv", ".venv", "__pycache__", ".git",
    "node_modules", "dist", "build",
    ".pytest_cache", ".idea"
}

IGNORED_FILES = {
    ".env", "secrets.py", "credentials.py"
}

MAX_FILES = 20
MAX_FILE_SIZE = 50000
MAX_CONTEXT_CHARS = 30000


def read_project_files(project_path):

    root = Path(project_path).resolve()

    if not root.exists() or not root.is_dir():
        raise ValueError("Invalid project directory.")

    source_files = []

    for current_root, directories, filenames in os.walk(root):

        directories[:] = [
            directory for directory in directories
            if directory not in IGNORED_DIRECTORIES
        ]

        for filename in filenames:

            if filename in IGNORED_FILES:
                continue

            file_path = Path(current_root) / filename

            if file_path.is_symlink():
                continue

            if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue

            try:

                resolved = file_path.resolve()

                if not resolved.is_relative_to(root):
                    continue

                if resolved.stat().st_size > MAX_FILE_SIZE:
                    continue

                content = resolved.read_text(
                    encoding="utf-8",
                    errors="replace"
                )

                relative_path = resolved.relative_to(root)

                source_files.append({
                    "file": relative_path.as_posix(),
                    "content": content
                })

            except (OSError, ValueError):
                continue

            if len(source_files) >= MAX_FILES:
                return source_files

    return source_files


def select_relevant_files(source_files, bug_description):

    words = set(
        re.findall(
            r"[a-zA-Z_][a-zA-Z0-9_]{2,}",
            bug_description.lower()
        )
    )

    scored_files = []

    for source in source_files:

        content = source["content"].lower()
        filename = source["file"].lower()

        score = 0

        for word in words:

            if word in filename:
                score += 3

            score += min(content.count(word), 5)

        scored_files.append((score, source))

    scored_files.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return [
        source for score, source
        in scored_files[:MAX_FILES]
    ]


def build_project_context(project_path, bug_description):

    source_files = read_project_files(project_path)

    if not source_files:
        raise ValueError(
            "No supported source files found."
        )

    relevant_files = select_relevant_files(
        source_files,
        bug_description
    )

    context = []
    total_chars = 0

    for source in relevant_files:

        block = (
            f"\nFILE: {source['file']}\n"
            f"CODE:\n{source['content']}\n"
        )

        if total_chars + len(block) > MAX_CONTEXT_CHARS:
            break

        context.append(block)
        total_chars += len(block)

    return "\n".join(context)


def parse_json_response(response_text):

    cleaned = response_text.strip()

    if cleaned.startswith("```"):

        cleaned = re.sub(
            r"^```(?:json)?\s*",
            "",
            cleaned
        )

        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned
        )

    try:
        return json.loads(cleaned)

    except json.JSONDecodeError:

        return {
            "analysis": cleaned,
            "format_warning": (
                "Gemini did not return valid JSON."
            )
        }


def investigate_code(
    bug_description,
    bug_category,
    project_path
):

    project_context = build_project_context(
        project_path,
        bug_description
    )

    prompt = INVESTIGATION_PROMPT.format(
        bug_description=bug_description,
        bug_category=bug_category,
        project_context=project_context
    )

    response_text = generate_gemini_response(prompt)

    investigation = parse_json_response(response_text)

    return {
        "investigation": investigation,
        "project_context": project_context
    }
