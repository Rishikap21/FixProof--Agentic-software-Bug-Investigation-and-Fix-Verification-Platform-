
import json
import html
import argparse

from pathlib import Path
from datetime import datetime


def safe(value):
    return html.escape(str(value))


def generate_html_report(report_path):

    report_path = Path(report_path).resolve()

    if not report_path.is_file():
        raise FileNotFoundError(
            f"Report not found: {report_path}"
        )

    with open(report_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    issue_classification = data.get("issue_classification", {})
    classification = data.get("classification", {})
    investigation = data.get("investigation", {})
    proposed_fix = data.get("proposed_fix", {})
    before = data.get("before_fix", {})
    after = data.get("after_fix", {})

    status = data.get("verification_status", "UNKNOWN")
    verified = status == "VERIFIED"

    status_label = "VERIFICATION PASSED" if verified else status
    status_color = "#22c55e" if verified else "#f87171"

    category = safe(classification.get(
        "predicted_category", "Unknown"
    ))
    issue_category = safe(issue_classification.get(
        "predicted_label", "Unknown"
    ))

    issue_confidence = issue_classification.get(
        "confidence", "N/A"
    )

    confidence = classification.get("confidence", "N/A")

    bug = safe(data.get(
        "bug_description", "Not available"
    ))

    root_cause = safe(investigation.get(
        "root_cause", "Not available"
    ))

    summary = safe(proposed_fix.get(
        "fix_summary", "Not available"
    ))

    expected = safe(proposed_fix.get(
        "expected_result", "Not available"
    ))

    timestamp = datetime.now().strftime(
        "%d %B %Y | %I:%M %p"
    )

    findings = investigation.get(
        "investigation_findings", []
    )

    relevant_files = investigation.get(
        "relevant_files", []
    )

    changes = proposed_fix.get(
        "proposed_changes", []
    )

    risks = proposed_fix.get("risks", [])

    def list_items(items):

        if not items:
            return "<li>No information available.</li>"

        return "".join(
            f"<li>{safe(item)}</li>"
            for item in items
        )

    def file_items(items):

        if not items:
            return "<p>No relevant files identified.</p>"

        output = ""

        for item in items:
            if isinstance(item, dict):
                output += f"""
                <div class="file-item">
                    <div class="file-icon">PY</div>
                    <div>
                        <strong>{safe(item.get('file', 'Unknown'))}</strong>
                        <p>{safe(item.get('reason', ''))}</p>
                    </div>
                </div>
                """

        return output or "<p>No relevant files identified.</p>"

    def patch_items(items):

        if not items:
            return "<p>No patch was generated.</p>"

        output = ""

        for item in items:

            diff = item.get("unified_diff", "")

            diff_lines = ""

            for line in diff.splitlines():

                if line.startswith("+") and not line.startswith("+++"):
                    css_class = "added"
                elif line.startswith("-") and not line.startswith("---"):
                    css_class = "removed"
                else:
                    css_class = "neutral"

                diff_lines += (
                    f'<div class="{css_class}">'
                    f'{safe(line)}</div>'
                )

            output += f"""
            <div class="patch-card">
                <div class="patch-header">
                    <span>CODE PATCH</span>
                    <strong>{safe(item.get('file', 'Unknown'))}</strong>
                </div>
                <p>{safe(item.get('explanation', ''))}</p>
                <div class="code-block">
                    {diff_lines}
                </div>
            </div>
            """

        return output

    before_passed = before.get("passed", 0)
    before_failed = before.get("failed", 0)
    after_passed = after.get("passed", 0)
    after_failed = after.get("failed", 0)

    html_content = f"""
<!DOCTYPE html>
<html lang="en">

<head>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>FixProof | Verification Report</title>

<style>

:root {{
    --bg: #0b1020;
    --panel: #151d32;
    --panel2: #1c2740;
    --text: #edf2ff;
    --muted: #9aa9c5;
    --purple: #a78bfa;
    --green: #4ade80;
    --red: #fb7185;
    --border: #2b3854;
}}

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    padding: 35px 18px;
    background: var(--bg);
    color: var(--text);
    font-family: Arial, sans-serif;
}}

.container {{
    max-width: 1050px;
    margin: auto;
}}

.topbar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 15px;
    margin-bottom: 28px;
}}

.brand {{
    font-size: 27px;
    font-weight: bold;
    letter-spacing: 2px;
}}

.brand span {{
    color: var(--purple);
}}

.generated {{
    color: var(--muted);
    font-size: 13px;
}}

.hero {{
    background: linear-gradient(135deg, #20264c, #35265f);
    border: 1px solid #55468c;
    border-radius: 18px;
    padding: 38px;
    margin-bottom: 25px;
}}

.eyebrow {{
    color: #c4b5fd;
    letter-spacing: 2px;
    font-size: 11px;
    font-weight: bold;
}}

.hero h1 {{
    font-size: 34px;
    margin: 15px 0 10px;
}}

.hero p {{
    color: #d2d8ec;
    line-height: 1.6;
}}

.status {{
    display: inline-block;
    margin-top: 12px;
    padding: 12px 19px;
    border-radius: 9px;
    border: 1px solid {status_color};
    color: {status_color};
    font-weight: bold;
    background: #101a2b;
}}

.stats {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 15px;
    margin: 25px 0;
}}

.stat {{
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 23px;
    border-radius: 13px;
}}

.stat small {{
    color: var(--muted);
    font-size: 12px;
}}

.stat h2 {{
    font-size: 30px;
    margin: 12px 0 0;
}}

.green {{
    color: var(--green);
}}

.red {{
    color: var(--red);
}}

.purple {{
    color: var(--purple);
}}

.card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 26px;
    margin-bottom: 20px;
}}

.section-heading {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 23px;
}}

.number {{
    width: 35px;
    height: 35px;
    background: #302653;
    color: #c4b5fd;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 9px;
    font-weight: bold;
}}

.section-heading h2 {{
    font-size: 19px;
    margin: 0;
}}

.label {{
    color: var(--muted);
    font-size: 12px;
    margin-bottom: 9px;
    display: block;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

.content {{
    line-height: 1.8;
    color: #d5def0;
    overflow-wrap: anywhere;
}}

.info-box {{
    background: var(--panel2);
    border-left: 3px solid var(--purple);
    padding: 18px;
    border-radius: 7px;
    line-height: 1.8;
}}

.file-item {{
    display: flex;
    align-items: center;
    gap: 15px;
    background: var(--panel2);
    border: 1px solid var(--border);
    padding: 14px;
    margin: 10px 0;
    border-radius: 9px;
}}

.file-icon {{
    background: #302653;
    color: #c4b5fd;
    padding: 10px;
    border-radius: 7px;
    font-size: 11px;
}}

.file-item p {{
    color: var(--muted);
    font-size: 13px;
    margin-bottom: 0;
    overflow-wrap: anywhere;
}}

ul {{
    padding-left: 22px;
    line-height: 1.9;
    color: #d5def0;
}}

.patch-card {{
    background: var(--panel2);
    border: 1px solid var(--border);
    padding: 18px;
    border-radius: 10px;
    margin-top: 15px;
}}

.patch-header {{
    display: flex;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
    color: var(--purple);
    font-size: 12px;
}}

.patch-card p {{
    color: var(--muted);
    line-height: 1.6;
}}

.code-block {{
    background: #090e1b;
    padding: 15px;
    border-radius: 8px;
    overflow-x: auto;
    font-family: Consolas, monospace;
    font-size: 13px;
}}

.code-block div {{
    padding: 5px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
}}

.added {{
    color: #4ade80;
    background: #123024;
}}

.removed {{
    color: #fb7185;
    background: #351c2a;
}}

.neutral {{
    color: #cbd5e1;
}}

.comparison {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 15px;
}}

.test-card {{
    background: var(--panel2);
    border: 1px solid var(--border);
    border-radius: 11px;
    padding: 20px;
}}

.test-card h3 {{
    margin-top: 0;
}}

.test-count {{
    font-size: 34px;
    font-weight: bold;
}}

.test-status {{
    display: inline-block;
    padding: 6px 11px;
    border-radius: 20px;
    font-size: 11px;
    margin-top: 8px;
    background: #102c23;
    color: var(--green);
}}

.final {{
    background: linear-gradient(135deg, #152c32, #172d39);
    border: 1px solid #28664b;
    text-align: center;
}}

.final h2 {{
    color: var(--green);
    font-size: 25px;
}}

.footer {{
    text-align: center;
    color: var(--muted);
    font-size: 12px;
    padding: 25px;
}}

@media(max-width: 750px) {{
    .stats {{
        grid-template-columns: repeat(2, 1fr);
    }}

    .hero h1 {{
        font-size: 26px;
    }}
}}

@media(max-width: 480px) {{
    .stats, .comparison {{
        grid-template-columns: 1fr;
    }}

    .hero, .card {{
        padding: 20px;
    }}
}}

@media print {{
    body {{
        background: white;
        color: #222;
    }}

    .card, .stat, .test-card, .patch-card {{
        background: white;
        color: #222;
        border: 1px solid #ccc;
        break-inside: avoid;
    }}

    .content, ul, .file-item p, .patch-card p {{
        color: #333;
    }}

    .hero {{
        background: #eee;
        color: #222;
    }}

    .hero p, .brand, .hero h1 {{
        color: #222;
    }}

    .code-block {{
        background: #eee;
        color: #222;
    }}

    .code-block div {{
        color: #222;
    }}

    .footer {{
        color: #555;
    }}
}}

</style>

</head>

<body>

<div class="container">

<div class="topbar">

    <div class="brand">
        FIX<span>PROOF</span>
    </div>

    <div class="generated">
        REPORT GENERATED<br>
        {safe(timestamp)}
    </div>

</div>

<section class="hero">

    <div class="eyebrow">AI-POWERED DEBUGGING PLATFORM</div>

    <h1>Verification Report</h1>

    <p>
        Automated bug investigation, intelligent fix generation
        and regression verification.
    </p>

    <div class="status">
        {safe(status_label)}
    </div>

</section>

<div class="stats">

    <div class="stat">
    <small>ISSUE TYPE (NLBSE ML)</small>
    <h2 class="purple">{issue_category}</h2>
    <small>Confidence: {safe(issue_confidence)}%</small>
</div>

<div class="stat">
    <small>TECHNICAL BUG CATEGORY</small>
    <h2 class="purple">{category}</h2>
</div>

    <div class="stat">
        <small>BEFORE FIX</small>
        <h2 class="red">{safe(before.get('failed', 0))}</h2>
        <small>Failed tests</small>
    </div>

    <div class="stat">
        <small>AFTER FIX</small>
        <h2 class="green">{safe(after.get('passed', 0))}</h2>
        <small>Passed tests</small>
    </div>

    <div class="stat">
        <small>ML CONFIDENCE</small>
        <h2 class="purple">{safe(confidence)}%</h2>
    </div>

</div>

<section class="card">

    <div class="section-heading">
        <div class="number">01</div>
        <h2>Bug Details</h2>
    </div>

    <span class="label">Reported issue</span>

    <div class="content">{bug}</div>

</section>

<section class="card">

    <div class="section-heading">
        <div class="number">02</div>
        <h2>AI Investigation</h2>
    </div>

    <span class="label">Root cause analysis</span>

    <div class="info-box">{root_cause}</div>

    <br>

    <span class="label">Investigation confidence</span>

    <p class="content">{safe(investigation.get('confidence', 'N/A'))}</p>

    <span class="label">Relevant source files</span>

    {file_items(relevant_files)}

    <br>

    <span class="label">Investigation findings</span>

    <ul>{list_items(findings)}</ul>

</section>

<section class="card">

    <div class="section-heading">
        <div class="number">03</div>
        <h2>AI-Generated Fix</h2>
    </div>

    <span class="label">Fix explanation</span>

    <div class="content">{summary}</div>

    {patch_items(changes)}

    <br>

    <span class="label">Expected result</span>

    <div class="info-box">{expected}</div>

    <br>

    <span class="label">Potential risks</span>

    <ul>{list_items(risks)}</ul>

</section>

<section class="card">

    <div class="section-heading">
        <div class="number">04</div>
        <h2>Before & After Testing</h2>
    </div>

    <div class="comparison">

        <div class="test-card">
            <h3>Before Fix</h3>
            <div class="test-count red">
                {safe(before_passed)} Passed
            </div>
            <p class="content">
                {safe(before_failed)} Failed
            </p>
            <span class="test-status"
                  style="background:#351c2a;color:#fb7185">
                {safe(before.get('status', 'UNKNOWN'))}
            </span>
        </div>

        <div class="test-card">
            <h3>After Fix</h3>
            <div class="test-count green">
                {safe(after_passed)} Passed
            </div>
            <p class="content">
                {safe(after_failed)} Failed
            </p>
            <span class="test-status">
                {safe(after.get('status', 'UNKNOWN'))}
            </span>
        </div>

    </div>

</section>

<section class="card final">

    <div class="eyebrow">FINAL ASSESSMENT</div>

    <h2>{safe(status_label)}</h2>

    <p class="content">
        {
            "The proposed patch was applied and all recorded tests passed."
            if verified
            else "Verification was not successful. Review the test results and unresolved issues."
        }
    </p>

    <p class="content">
        Human review required:
        <strong>{safe(data.get('human_review_required', True))}</strong>
    </p>

    <p class="content">
        Passing the supplied tests does not guarantee that every
        possible software defect has been eliminated.
    </p>

</section>

<div class="footer">

    <strong>FIXPROOF</strong><br><br>

    Intelligent Software Debugging & Fix Verification<br>

    Generated automatically by the FixProof system.

</div>

</div>

</body>
</html>
"""

    output_path = (
        report_path.parent / "verification_report.html"
    )

    output_path.write_text(
        html_content,
        encoding="utf-8"
    )

    return str(output_path)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "report_path",
        help="Path to verification_report.json"
    )

    args = parser.parse_args()

    try:

        output = generate_html_report(args.report_path)

        print("\nProfessional HTML report generated!")
        print("Location:", output)

    except Exception as error:

        print("\nReport generation failed:")
        print(str(error))
