
import os
import joblib


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model.pkl")


def load_model():

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            "Trained model not found. "
            "Run train_model.py first."
        )

    return joblib.load(MODEL_PATH)


def classify_bug(description):

    if not isinstance(description, str) or not description.strip():
        raise ValueError("Please provide a valid bug description.")

    model = load_model()

    # Predict bug category
    prediction = model.predict([description])[0]

    # Calculate prediction confidence
    probabilities = model.predict_proba([description])[0]

    confidence = max(probabilities) * 100

    # Return all category probabilities
    category_probabilities = {
        category: round(float(probability) * 100, 2)
        for category, probability in zip(
            model.classes_,
            probabilities
        )
    }

    return {
        "bug_description": description,
        "predicted_category": prediction,
        "confidence": round(confidence, 2),
        "category_probabilities": category_probabilities
    }


if __name__ == "__main__":

    print("\n================================")
    print("    FIXPROOF BUG CLASSIFIER")
    print("================================")

    print("\nEnter a bug description:")

    description = input("> ")

    try:

        result = classify_bug(description)

        print("\nPredicted Bug Category:")
        print(result["predicted_category"])

        print("\nConfidence:")
        print(f'{result["confidence"]}%')

        print("\nAll Category Probabilities:")

        for category, probability in (
            result["category_probabilities"].items()
        ):
            print(f"{category}: {probability}%")

    except Exception as error:

        print("\nClassification failed:")
        print(error)
