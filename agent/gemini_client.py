
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors


load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
)

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

client = genai.Client(api_key=API_KEY)


def generate_gemini_response(prompt):

    max_attempts = 3
    delays = [5, 10]

    for attempt in range(max_attempts):

        try:

            print(
                f"\nGemini request: attempt "
                f"{attempt + 1}/{max_attempts}"
            )

            response = client.models.generate_content(
                model=MODEL,
                contents=prompt
            )

            if not response.text:
                raise RuntimeError(
                    "Gemini returned an empty response."
                )

            return response.text

        except errors.APIError as error:

            status_code = getattr(
                error,
                "code",
                None
            )

            if status_code not in (
                408, 429, 500, 502, 503, 504
            ):
                raise

            if attempt == max_attempts - 1:
                raise RuntimeError(
                    "Gemini is currently unavailable "
                    "after multiple attempts. Please try again later."
                ) from error

            wait_time = delays[attempt]

            print(
                f"Gemini temporarily unavailable. "
                f"Retrying in {wait_time} seconds..."
            )

            time.sleep(wait_time)

    raise RuntimeError("Gemini request failed.")
