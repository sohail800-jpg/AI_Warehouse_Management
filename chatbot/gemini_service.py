
from django.conf import settings
from google import genai
from google.genai import types


def ask_gemini(question, warehouse_data=""):

    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=types.HttpOptions(timeout=30000)
    )

    prompt = f"""
    You are an AI Warehouse Assistant.

    Warehouse information:
    {warehouse_data}

    User question:
    {question}

    Answer briefly and clearly.
    Never invent warehouse stock information.
    """

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=128
        )
    )

    return response.text
