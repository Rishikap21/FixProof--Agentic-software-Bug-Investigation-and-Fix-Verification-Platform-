
import re
import shutil

from pathlib import Path
from datetime import datetime


ALLOWED_EXTENSIONS = {
    ".py", ".java", ".js", ".ts",
    ".jsx", ".tsx", ".html", ".css", ".sql"
}


def validate_target(project_path, filename):

    root = Path(project_path).resolve()
    relative = Path(filename)

    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Unsafe patch file path.")

    target = (root / relative).resolve()

    if not target.is_relative_to(root):
        raise ValueError("Patch points outside the project.")

    if target.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported file type.")

    if not target.is_file():
        raise FileNotFoundError(
            f"Patch target does not exist: {filename}"
        )

    if target.is_symlink():
        raise ValueError("Symbolic links are not allowed.")

    return target


def apply_unified_diff(original_text, diff_text):

    lines = original_text.splitlines(keepends=True)
    diff_lines = diff_text.splitlines()

    i = 0
    hunks_found = 0

    while i < len(diff_lines):

        line = diff_lines[i]

        if not line.startswith("@@"):
            i += 1
            continue

        hunks_found += 1

        i += 1

        old_lines = []
        new_lines = []

        while i < len(diff_lines):

            current = diff_lines[i]

            if current.startswith("@@"):
                break

            if current.startswith("--- "):
                break

            if current.startswith("+++ "):
                break

            if current.startswith("\\"):
                i += 1
                continue

            if current.startswith(" "):
                content = current[1:] + "\n"
                old_lines.append(content)
                new_lines.append(content)

            elif current.startswith("-"):
                old_lines.append(current[1:] + "\n")

            elif current.startswith("+"):
                new_lines.append(current[1:] + "\n")

            else:
                break

            i += 1

        if not old_lines and not new_lines:
            raise ValueError("Empty patch hunk.")

        normalized_lines = [
            item.rstrip("\r\n") for item in lines
        ]

        normalized_old = [
            item.rstrip("\r\n") for item in old_lines
        ]

        matches = []

        if old_lines:

            for start in range(
                len(lines) - len(old_lines) + 1
            ):

                section = normalized_lines[
                    start:start + len(old_lines)
                ]

                if section == normalized_old:
                    matches.append(start)

        else:
            raise ValueError(
                "Insertion-only patches are not supported."
            )

        if len(matches) != 1:
            raise ValueError(
                "Patch context did not match uniquely. "
                "No changes were made."
            )

        start = matches[0]
        end = start + len(old_lines)

        lines[start:end] = new_lines

    if hunks_found == 0:
        raise ValueError("No valid unified diff hunks found.")

    return "".join(lines)


def apply_patch(project_path, changes):

    if not changes:
        raise ValueError("No proposed changes to apply.")

    root = Path(project_path).resolve()

    backup_dir = root / ".fixproof_backups"

    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S_%f"
    )

    backups = []

    # Validate every patch before modifying anything
    validated = []

    for change in changes:

        filename = change.get("file", "")
        diff = change.get("unified_diff", "")

        target = validate_target(root, filename)

        if not isinstance(diff, str) or not diff.strip():
            raise ValueError("Invalid patch content.")

        original_text = target.read_text(
            encoding="utf-8"
        )

        updated_text = apply_unified_diff(
            original_text,
            diff
        )

        validated.append({
            "target": target,
            "filename": filename,
            "original": original_text,
            "updated": updated_text
        })

    try:

        for item in validated:

            target = item["target"]

            backup = backup_dir / (
                f"{timestamp}_{target.name}.bak"
            )

            shutil.copy2(target, backup)

            backups.append({
                "file": item["filename"],
                "target": str(target),
                "backup": str(backup)
            })

            target.write_text(
                item["updated"],
                encoding="utf-8"
            )

    except Exception:

        for item in reversed(validated):

            target = item["target"]

            if target.exists():
                target.write_text(
                    item["original"],
                    encoding="utf-8"
                )

        raise

    return {
        "status": "PATCH_APPLIED",
        "files_modified": [
            item["filename"] for item in validated
        ],
        "backups": backups
    }


def restore_backups(backups):

    restored = []

    for item in reversed(backups):

        target = Path(item["target"])
        backup = Path(item["backup"])

        if not backup.is_file():
            raise FileNotFoundError(
                f"Backup not found: {backup}"
            )

        shutil.copy2(backup, target)

        restored.append(item["file"])

    return {
        "status": "RESTORED",
        "files_restored": restored
    }
