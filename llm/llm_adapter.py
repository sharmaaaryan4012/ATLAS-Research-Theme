"""
Name: Aaryan Sharma, Kirthi Shankar
Project: ATLAS Research Theme
File: llm_adapter.py
Description:
    Gemini adapter that returns strict JSON for LangGraph node protocols.
    Reads API key automatically from config/api.env.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from dotenv import load_dotenv
import google.generativeai as genai


class GeminiJSONAdapter:
    """
    Implements the Protocol expected by your nodes:
      - FieldClassifierLLM
      - FieldValidatorLLM
      - SubfieldClassifierLLM
      - SubfieldValidatorLLM

    Single method: generate_json(prompt) -> dict | None
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": 0.2,
                "top_p": 0.9,
                "top_k": 40,
                "response_mime_type": "application/json",
            },
        )

    @classmethod
    def from_env(cls, model_name: str = "gemini-2.5-flash") -> "GeminiJSONAdapter":
        """
        Load the Gemini API key from config/api.env and return an initialized adapter.
        """
        # Resolve path to config/api.env relative to project root
        env_path = os.path.join(os.path.dirname(__file__), "config", "api.env")
        if not os.path.exists(env_path):
            # fallback for when running from subdir (e.g. src/langgraph/llm_adapter.py)
            env_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "config", "api.env"
            )

        load_dotenv(env_path)

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(f"Missing GEMINI_API_KEY/GOOGLE_API_KEY in {env_path}")

        return cls(api_key=api_key, model_name=model_name)

    def generate_json(self, prompt: str) -> Optional[dict]:
        """
        Calls Gemini and tries to return a dict.
        If parsing fails, returns None so nodes can use their fallback behavior.
        """
        try:
            resp = self.model.generate_content(prompt)
            text = (resp.text or "").strip()

            # If response includes Markdown fences, clean them up
            if text.startswith("```"):
                parts = text.split("```")
                for part in parts:
                    part = part.strip()
                    if part and not part.startswith("json"):
                        text = part
                        break

            return json.loads(text)
        except Exception:
            return None
