import os
from openai import OpenAI
from typing import List, Dict, Any

class CVBrain:
    """Handles the intelligent part of CV tailoring using an LLM."""

    def __init__(self, api_key: str = None, base_url: str = None):
        # Fallback to environment variable or hardcoded LM Studio defaults
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or "lm-studio"
        self.base_url = base_url or "http://localhost:1234/v1"
        
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def generate_tailored_content(
        self, 
        job_spec: str, 
        cv_structure: List[Dict[str, Any]], 
        cv_content_md: str
    ) -> List[Dict[str, Any]]:
        """
        Uses LLM to decide which parts of the CV to update and what the new text should be.
        Returns a list of updates: [{'original_text': '...', 'new_text': '...'}]
        """
        
        system_prompt = (
            "You are a professional CV editor. Your goal is to tailor a CV to match a job specification "
            "using only the provided facts. \n\n"
            "RULES:\n"
            "1. DO NOT invent new experiences, dates, or job titles.\n"
            "2. DO NOT lie about skills or responsibilities.\n"
            "3. Use the 'CVContent.md' as a source of truth for additional achievements/details.\n"
            "4. Focus on rephrasing existing bullet points to highlight relevant keywords from the job spec.\n"
            "5. If an achievement in CVContent.md is highly relevant, integrate it into the appropriate section.\n"
            "6. Return your response ONLY as a valid JSON list of objects."
        )

        user_prompt = (
            f"### JOB SPECIFICATION:\n{job_spec}\n\n"
            f"### CURRENT CV STRUCTURE:\n{cv_structure}\n\n"
            f"### ADDITIONAL ACHIEVEMENTS (from CVContent.md):\n{cv_content_md}\n\n"
            "Identify specific paragraphs in the 'CURRENT CV STRUCTURE' that should be updated "
            "to better align with the job spec. For each update, provide the exact original text "
            "and the new, improved text.\n\n"
            "Return format: [{\"original_text\": \"...\", \"new_text\": \"...\"}]"
        )

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        # Debug: Print the response content to terminal
        print(f"DEBUG: LLM Response Content: {response.choices[0].message.content}")

        # The response might be a JSON object containing the list, or just the list.
        # We'll try to parse it carefully.
        import json
        import re
        raw_content = response.choices[0].message.content

        
        # Try to extract JSON from markdown code blocks if present
        json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', raw_content, re.DOTALL)
        if json_match:
            raw_content = json_match.group(1)

        try:
            data = json.loads(raw_content)
        except json.JSONDecodeError:
            # Fallback: if it's not valid JSON, maybe it's just a string representation of a list?
            # This is a bit risky but helps with robustness.
            return []

        # If the LLM returned {"updates": [...]}, extract the list.
        if isinstance(data, dict):
            for key in data:
                if isinstance(data[key], list):
                    return data[key]
            return [] # Fallback if structure is unexpected
        
        return data if isinstance(data, list) else []

        # If the LLM returned {"updates": [...]}, extract the list.
        if isinstance(data, dict):
            for key in data:
                if isinstance(data[key], list):
                    return data[key]
            return [] # Fallback if structure is unexpected
        
        return data if isinstance(data, list) else []


if __name__ == "__main__":
    # Simple test (requires OPENAI_API_KEY set)
    try:
        brain = CVBrain()
        test_updates = brain.generate_tailored_content(
            "Looking for a Python developer with experience in Streamlit.",
            [{"text": "I know Python", "style": "Normal"}],
            "I have built many web apps using Streamlit and FastAPI."
        )
        print(test_updates)
    except Exception as e:
        print(f"Test failed: {e}")
