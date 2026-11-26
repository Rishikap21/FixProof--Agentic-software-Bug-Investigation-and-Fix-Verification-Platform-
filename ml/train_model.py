
import os
import json
import re
import pandas as pd
import joblib

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score
)


# -----------------------------------------
# FIXPROOF REAL-DATA ML TRAINING
# -----------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(
    BASE_DIR, "nlbse_dataset", "data"
)

TRAIN_PATH = os.path.join(DATA_DIR, "issues_train.csv")
TEST_PATH = os.path.join(DATA_DIR, "issues_test.csv")

MODEL_DIR = os.path.join(BASE_DIR, "models")
REPO_MODEL_DIR = os.path.join(MODEL_DIR, "repository_models")
REPORT_DIR = os.path.join(BASE_DIR, "evaluation")

LABELS = ["bug", "feature", "question"]


def create_model():
    """Create the text-classification pipeline."""

    return Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                lowercase=True,
                stop_words="english",
                ngram_range=(1, 2),
                max_features=20000,
                min_df=2,
                sublinear_tf=True
            )
        ),
        (
            "classifier",
            LogisticRegression(
                max_iter=3000,
                random_state=42
            )
        )
    ])


def prepare_data(data):
    """Clean the issue-report text."""

    required_columns = {"repo", "label", "title", "body"}

    if not required_columns.issubset(data.columns):
        raise ValueError(
            "Dataset must contain repo, label, title and body columns."
        )

    data = data.copy()

    for column in ["repo", "label", "title", "body"]:
        data[column] = data[column].fillna("").astype(str).str.strip()

    data["text"] = (
        data["title"] + " " + data["body"]
    ).str.strip()

    data = data[
        (data["repo"] != "") &
        (data["label"] != "") &
        (data["text"] != "")
    ]

    return data


def evaluate_model(model, test_data, model_name):
    """Evaluate a trained model and return its metrics."""

    X_test = test_data["text"]
    y_test = test_data["label"]

    predictions = model.predict(X_test)

    accuracy = accuracy_score(y_test, predictions)
    macro_f1 = f1_score(
        y_test,
        predictions,
        labels=LABELS,
        average="macro",
        zero_division=0
    )

    report = classification_report(
        y_test,
        predictions,
        labels=LABELS,
        target_names=LABELS,
        output_dict=True,
        zero_division=0
    )

    matrix = confusion_matrix(
        y_test,
        predictions,
        labels=LABELS
    )

    print("\n-----------------------------------------")
    print("MODEL:", model_name)
    print("-----------------------------------------")
    print(f"Accuracy: {accuracy * 100:.2f}%")
    print(f"Macro F1: {macro_f1:.4f}")

    print("\nClassification Report:")
    print(
        classification_report(
            y_test,
            predictions,
            labels=LABELS,
            target_names=LABELS,
            zero_division=0
        )
    )

    print("Confusion Matrix:")
    print(matrix)

    return {
        "model": model_name,
        "accuracy": round(float(accuracy), 4),
        "macro_f1": round(float(macro_f1), 4),
        "classification_report": report,
        "confusion_matrix": matrix.tolist(),
        "labels": LABELS
    }


def train_model():

    print("\n=========================================")
    print("       FIXPROOF REAL-DATA ML TRAINING")
    print("=========================================")

    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(REPO_MODEL_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)

    # Load the official training and testing datasets.
    print("\nLoading datasets...")

    if not os.path.exists(TRAIN_PATH):
        raise FileNotFoundError(
            f"Training dataset not found: {TRAIN_PATH}"
        )

    if not os.path.exists(TEST_PATH):
        raise FileNotFoundError(
            f"Testing dataset not found: {TEST_PATH}"
        )

    train_data = prepare_data(pd.read_csv(TRAIN_PATH))
    test_data = prepare_data(pd.read_csv(TEST_PATH))

    print("Training records:", len(train_data))
    print("Testing records:", len(test_data))

    print("\nTraining label distribution:")
    print(train_data["label"].value_counts())

    print("\nTesting label distribution:")
    print(test_data["label"].value_counts())

    if set(train_data["label"].unique()) != set(LABELS):
        raise ValueError("Training data must contain all three labels.")

    if set(test_data["label"].unique()) != set(LABELS):
        raise ValueError("Testing data must contain all three labels.")

    results = {}

    # -----------------------------------------
    # 1. GENERAL MODEL: ALL REPOSITORIES
    # -----------------------------------------

    print("\n\nTraining general model on all repositories...")

    general_model = create_model()

    general_model.fit(
        train_data["text"],
        train_data["label"]
    )

    general_model_path = os.path.join(
        MODEL_DIR, "issue_model.pkl"
    )

    joblib.dump(general_model, general_model_path)

    print("General model saved:", general_model_path)

    results["general_model"] = evaluate_model(
        general_model,
        test_data,
        "General Model - All Repositories"
    )

    # -----------------------------------------
    # 2. INDIVIDUAL REPOSITORY MODELS
    # -----------------------------------------

    print("\n\nTraining individual repository models...")

    repository_results = {}

    repositories = sorted(train_data["repo"].unique())

    for repo in repositories:

        print("\n=========================================")
        print("Repository:", repo)
        print("=========================================")

        repo_train = train_data[
            train_data["repo"] == repo
        ]

        repo_test = test_data[
            test_data["repo"] == repo
        ]

        if repo_train.empty or repo_test.empty:
            print("Skipping repository: missing training or test records.")
            continue

        if set(repo_train["label"].unique()) != set(LABELS):
            print("Skipping repository: not all labels are present.")
            continue

        repo_model = create_model()

        repo_model.fit(
            repo_train["text"],
            repo_train["label"]
        )

        safe_name = re.sub(
            r"[^a-zA-Z0-9_-]",
            "_",
            repo
        )

        model_path = os.path.join(
            REPO_MODEL_DIR,
            safe_name + ".pkl"
        )

        joblib.dump(repo_model, model_path)

        print("Repository model saved:", model_path)

        repository_results[repo] = evaluate_model(
            repo_model,
            repo_test,
            repo
        )

    results["repository_models"] = repository_results

    # -----------------------------------------
    # 3. SAVE EVALUATION RESULTS
    # -----------------------------------------

    report_path = os.path.join(
        REPORT_DIR,
        "issue_classification_report.json"
    )

    with open(report_path, "w", encoding="utf-8") as file:
        json.dump(results, file, indent=4)

    print("\n=========================================")
    print("       TRAINING COMPLETED")
    print("=========================================")

    print("\nGeneral model:", general_model_path)
    print("Repository models:", REPO_MODEL_DIR)
    print("Evaluation report:", report_path)

    print("\nGeneral model accuracy:",
          f"{results['general_model']['accuracy'] * 100:.2f}%")

    print("General model macro F1:",
          results["general_model"]["macro_f1"])

    print("\nAll models and evaluation results saved successfully.")


if __name__ == "__main__":
    train_model()
