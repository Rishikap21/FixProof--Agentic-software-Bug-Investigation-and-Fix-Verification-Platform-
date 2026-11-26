
import json

from typing import TypedDict
from pathlib import Path

from langgraph.graph import StateGraph, START, END

from ml.classifier import classify_bug
from ml.issue_classifier import classify_issue_report

from agent.investigator import investigate_code
from agent.fix_generator import generate_fix


class FixProofState(TypedDict):

    bug_description: str
    project_path: str

    issue_classification: dict
    classification: dict
    investigation: dict
    project_context: str
    proposed_fix: dict

    status: str
    error: str


# STEP 1: REAL-DATA ISSUE CLASSIFICATION
def issue_classification_node(state: FixProofState):

    print("\n[1/4] Classifying issue using real-data ML model...")

    result = classify_issue_report(
        title=state["bug_description"],
        body=""
    )

    print("Issue type:", result["predicted_label"])
    print("Confidence:", result["confidence"], "%")

    return {
        "issue_classification": result,
        "status": "ISSUE_CLASSIFIED"
    }


# STEP 2: TECHNICAL BUG CLASSIFICATION
def classification_node(state: FixProofState):

    print("\n[2/4] Classifying technical bug...")

    result = classify_bug(
        state["bug_description"]
    )

    print("Technical category:", result["predicted_category"])

    return {
        "classification": result,
        "status": "CLASSIFIED"
    }


# STEP 3: AI INVESTIGATION
def investigation_node(state: FixProofState):

    print("\n[3/4] Investigating source code...")

    result = investigate_code(
        bug_description=state["bug_description"],
        bug_category=state["classification"]["predicted_category"],
        project_path=state["project_path"]
    )

    print("Code investigation completed.")

    return {
        "investigation": result["investigation"],
        "project_context": result["project_context"],
        "status": "INVESTIGATED"
    }


# STEP 4: FIX GENERATION
def fix_generation_node(state: FixProofState):

    print("\n[4/4] Generating proposed fix...")

    result = generate_fix(
        bug_description=state["bug_description"],
        bug_category=state["classification"]["predicted_category"],
        investigation=state["investigation"],
        project_context=state["project_context"],
        project_path=state["project_path"]
    )

    print("Fix generation completed.")

    return {
        "proposed_fix": result,
        "status": result["status"]
    }


# BUILD LANGGRAPH WORKFLOW
def build_workflow():

    graph = StateGraph(FixProofState)

    graph.add_node("issue_classification", issue_classification_node)
    graph.add_node("classification", classification_node)
    graph.add_node("investigation", investigation_node)
    graph.add_node("fix_generation", fix_generation_node)

    graph.add_edge(START, "issue_classification")
    graph.add_edge("issue_classification", "classification")
    graph.add_edge("classification", "investigation")
    graph.add_edge("investigation", "fix_generation")
    graph.add_edge("fix_generation", END)

    return graph.compile()


# RUN COMPLETE FIXPROOF WORKFLOW
def run_fixproof_workflow(bug_description, project_path):

    if not bug_description.strip():
        raise ValueError("Bug description cannot be empty.")

    project_path = str(Path(project_path).resolve())

    if not Path(project_path).is_dir():
        raise ValueError("Invalid project directory.")

    initial_state = {
        "bug_description": bug_description,
        "project_path": project_path,
        "issue_classification": {},
        "classification": {},
        "investigation": {},
        "project_context": "",
        "proposed_fix": {},
        "status": "STARTED",
        "error": ""
    }

    workflow = build_workflow()

    return workflow.invoke(initial_state)


if __name__ == "__main__":

    print("\n====================================")
    print("       FIXPROOF AGENTIC SYSTEM")
    print("====================================")

    bug_description = input(
        "\nEnter your bug description: "
    ).strip()

    project_path = input(
        "\nEnter project folder path: "
    ).strip().strip('"')

    try:

        result = run_fixproof_workflow(
            bug_description,
            project_path
        )

        print("\n====================================")
        print("         WORKFLOW RESULTS")
        print("====================================")

        print("\nREAL-DATA ISSUE CLASSIFICATION:")
        print(json.dumps(result["issue_classification"], indent=4))

        print("\nTECHNICAL BUG CLASSIFICATION:")
        print(json.dumps(result["classification"], indent=4))

        print("\nAI INVESTIGATION:")
        print(json.dumps(result["investigation"], indent=4))

        print("\nPROPOSED FIX:")
        print(json.dumps(result["proposed_fix"], indent=4))

        print("\nFinal Status:")
        print(result["status"])

        print(
            "\nNOTE: The proposed patch has not been applied "
            "or verified by this workflow."
        )

    except Exception as error:

        print("\nWorkflow failed:")
        print(str(error))
