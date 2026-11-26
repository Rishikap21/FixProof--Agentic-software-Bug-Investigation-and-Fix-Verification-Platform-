
import re
import subprocess
import sys

from pathlib import Path


def run_tests(project_path):

    project = Path(project_path).resolve()

    if not project.exists() or not project.is_dir():
        raise ValueError("Invalid project directory.")

    test_files = (
        list(project.glob("test_*.py")) +
        list(project.glob("*_test.py"))
    )

    if not test_files:
        return {
            "status": "NO_TESTS",
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "return_code": None,
            "output": "No test files found."
        }

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--tb=short",
        "--no-header",
        str(project)
    ]

    try:

        result = subprocess.run(
            command,
            cwd=str(project),
            capture_output=True,
            text=True,
            timeout=60
        )

        output = result.stdout + "\n" + result.stderr

        passed_match = re.search(
            r"(\d+) passed",
            output
        )

        failed_match = re.search(
            r"(\d+) failed",
            output
        )

        error_match = re.search(
            r"(\d+) error",
            output
        )

        passed = (
            int(passed_match.group(1))
            if passed_match else 0
        )

        failed = (
            int(failed_match.group(1))
            if failed_match else 0
        )

        errors = (
            int(error_match.group(1))
            if error_match else 0
        )

        if result.returncode == 0:
            status = "PASSED"

        elif result.returncode == 5:
            status = "NO_TESTS"

        else:
            status = "FAILED"

        return {
            "status": status,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "return_code": result.returncode,
            "output": output
        }

    except subprocess.TimeoutExpired:

        return {
            "status": "TIMEOUT",
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "return_code": None,
            "output": "Test execution exceeded 60 seconds."
        }

    except Exception as error:

        return {
            "status": "ERROR",
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "return_code": None,
            "output": str(error)
        }
