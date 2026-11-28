
import os
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "issue_model.pkl")


def classify_issue_report(title, body):
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            "Issue model not found. Run train_model.py first."
        )

    if not title.strip() and not body.strip():
        raise ValueError("Please provide an issue title or description.")

    model = joblib.load(MODEL_PATH)

    text = (title.strip() + " " + body.strip()).strip()

    prediction = model.predict([text])[0]
    probabilities = model.predict_proba([text])[0]

    return {
        "title": title,
        "predicted_label": prediction,
        "confidence": round(float(max(probabilities)) * 100, 2),
        "probabilities": {
            label: round(float(probability) * 100, 2)
            for label, probability in zip(model.classes_, probabilities)
        }
    }


if __name__ == "__main__":
    result = classify_issue_report(
        "Application crashes when opening settings",
        "The application closes unexpectedly every time I open settings."
    )

    print("\nFIXPROOF ISSUE CLASSIFICATION")
    print("-----------------------------")
    print("Predicted category:", result["predicted_label"])
    print("Confidence:", result["confidence"], "%")
    print("Probabilities:", result["probabilities"])
