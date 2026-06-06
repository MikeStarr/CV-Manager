import os
import sys
import json
from dotenv import load_dotenv

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cv_manager.brain import CVBrain

def main():
    load_dotenv()
    
    # Initialize the brain using ChatGPT (OpenAI key is in .env)
    brain = CVBrain(provider="chatgpt")
    print(f"Initialized CVBrain with model: {brain.model}")

    job_spec = """
    Senior Project Manager - Financial Services Technology
    We are looking for a Senior Project Manager with strong technology and financial services background to lead delivery of a critical SaaS platform migration.
    Key responsibilities:
    - Establish PMO governance and status reporting across multiple teams.
    - Manage delivery velocity and drive resource management and alignment.
    - Implement structured Entra ID integration and legacy platform decommissioning.
    - Lead large-scale budgets and vendor selections.
    """

    cv_structure = [
        {"text": "Senior Delivery Manager", "style": "Title"},
        {"text": "Professional Summary", "style": "Heading 2"},
        {
            "text": "I am a delivery leader with experience in modernising enterprise-scale platforms in regulated financial environments. I specialise in multi-team delivery, scaled agile practices, and driving high-quality SaaS outcomes.",
            "style": "Normal"
        },
        {"text": "Experience:", "style": "Heading 2"},
        {
            "text": "GTM Readiness: Delivered commercial critical entitlement, licensing, and onboarding workflows that improved customer activation speed and supported downstream CRM and forecasting processes.",
            "style": "Normal"
        },
        {
            "text": "Embedded scaled agile practices and technical design reviews across 15 teams, reducing release lead times from quarterly to fortnightly and improving feedback speed by 85%.",
            "style": "Normal"
        }
    ]

    cv_content_md = """
    We have extra database details:
    - Managed £20m cluster budget at LSEG.
    - Managed user base migration of 300k+ users.
    - Standardised Ways of Working across 15+ teams.
    """

    print("\nCalling generate_tailored_content...")
    result, raw_response = brain.generate_tailored_content(
        job_spec=job_spec,
        cv_structure=cv_structure,
        cv_content_md=cv_content_md,
        return_raw=True
    )

    print("\n=== RAW RESPONSE FROM LLM ===")
    print(raw_response)

    print("\n=== PARSED RESULT ===")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
