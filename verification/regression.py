
import json
from pathlib import Path

from agent.workflow import run_fixproof_workflow
from verification.test_runner import run_tests
from verification.report_generator import generate_html_report
from verification.patch_manager import apply_patch, restore_backups


def save_report(report, project_path):
    report_dir = Path(project_path) / ".fixproof_reports"
    report_dir.mkdir(exist_ok=True)

    report_path = report_dir / "verification_report.json"

    report_path.write_text(
        json.dumps(report, indent=4),
        encoding="utf-8"
    )

    return str(report_path)


def verify_fix(bug_description, project_path):

    project = Path(project_path).resolve()

    if not project.is_dir():
        raise ValueError("Invalid project directory.")

    print("\n====================================")
    print("    FIXPROOF VERIFICATION ENGINE")
    print("====================================")

    # STEP 1: AI WORKFLOW
    print("\nSTEP 1: Running AI debugging workflow...")

    workflow_result = run_fixproof_workflow(
        bug_description,
        str(project)
    )

    issue_classification = workflow_result.get(
        "issue_classification", {}
    )
    classification = workflow_result.get("classification", {})
    investigation = workflow_result.get("investigation", {})
    proposed_fix = workflow_result.get("proposed_fix", {})

    if proposed_fix.get("status") != "PATCH_PROPOSED":
        return {
            "verification_status": "NO_SAFE_PATCH",
            "message": "No applicable patch was generated.",
            "issue_classification": issue_classification,
            "classification": classification,
            "investigation": investigation,
            "proposed_fix": proposed_fix
        }

    changes = proposed_fix.get("proposed_changes", [])

    if not changes:
        return {
            "verification_status": "NO_SAFE_PATCH",
            "message": "No validated patch changes were available.",
            "proposed_fix": proposed_fix
        }

    # STEP 2: BASELINE TESTS
    print("\nSTEP 2: Running original project tests...")

    before = run_tests(project)

    print("Before-fix status:", before["status"])
    print("Passed:", before["passed"])
    print("Failed:", before["failed"])

    if before["status"] in ("NO_TESTS", "TIMEOUT", "ERROR"):
        return {
            "verification_status": "BASELINE_UNAVAILABLE",
            "message": "Original tests could not establish a baseline.",
            "before_fix": before
        }

    # STEP 3: HUMAN APPROVAL
    print("\nSTEP 3: Patch approval")

    print("Proposed fix:", proposed_fix.get("fix_summary", "Not available"))

    approval = input(
        "\nDo you approve applying this patch? (y/n): "
    ).strip().lower()

    if approval not in ("y", "yes"):
        return {
            "verification_status": "PATCH_DECLINED",
            "message": "Patch was not applied. Source files remain unchanged.",
            "issue_classification": issue_classification,
            "classification": classification,
            "investigation": investigation,
            "proposed_fix": proposed_fix,
            "before_fix": before,
            "human_review_required": True
        }

    # STEP 4: APPLY PATCH
    print("\nSTEP 4: Applying approved patch...")

    patch_result = apply_patch(
        str(project),
        changes
    )

    print("Patch status:", patch_result["status"])

    # STEP 5: TEST AFTER PATCH
    print("\nSTEP 5: Running tests after patch...")

    after = run_tests(project)

    print("After-fix status:", after["status"])
    print("Passed:", after["passed"])
    print("Failed:", after["failed"])

    # STEP 6: VERIFICATION
    verification_passed = (
        after["status"] == "PASSED"
        and after["passed"] > 0
        and after["failed"] == 0
        and after["errors"] == 0
    )

    if verification_passed:
        final_status = "VERIFIED"
        print("\nFixProof: All tests passed.")

    else:
        print("\nVerification failed.")
        print("Restoring original source files...")

        restore_result = restore_backups(
            patch_result["backups"]
        )

        final_status = "VERIFICATION_FAILED_ROLLED_BACK"

        print("Rollback:", restore_result["status"])

    # STEP 7: REPORT
    report = {
        "project": str(project),
        "bug_description": bug_description,
        "issue_classification": issue_classification,
        "classification": classification,
        "investigation": investigation,
        "proposed_fix": proposed_fix,
        "patch_application": patch_result,
        "before_fix": before,
        "after_fix": after,
        "verification_status": final_status,
        "verification_passed": verification_passed,
        "human_review_required": True
    }

    report_path = save_report(report, project)

    html_report_path = generate_html_report(report_path)

    report["report_path"] = report_path
    report["html_report_path"] = html_report_path

    Path(report_path).write_text(
        json.dumps(report, indent=4),
        encoding="utf-8"
    )

    # Refresh HTML with final report details
    generate_html_report(report_path)

    print("\n====================================")
    print("       VERIFICATION SUMMARY")
    print("====================================")

    print("Before fix:", before["status"])
    print("After fix:", after["status"])
    print("Final status:", final_status)
    print("JSON report:", report_path)
    print("HTML report:", html_report_path)

    return report


if __name__ == "__main__":

    print("\nFIXPROOF AUTOMATED VERIFICATION")

    bug_description = input(
        "\nEnter bug description: "
    ).strip()

    project_path = input(
        "\nEnter project folder path: "
    ).strip().strip('"')

    try:
        result = verify_fix(
            bug_description,
            project_path
        )

        print("\nFINAL RESULT:")

        print(json.dumps({
            "status": result.get(
                "verification_status", "UNKNOWN"
            ),
            "report_path": result.get(
                "report_path", "Report not generated"
            ),
            "html_report_path": result.get(
                "html_report_path", "Report not generated"
            )
        }, indent=4))

    except Exception as error:
        print("\nVerification process failed:")
        print(str(error))
