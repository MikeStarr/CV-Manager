from cv_manager.brain import CVBrain

print("\nTesting each provider:")
for provider in ["local", "chatgpt", "deepseek", "grok"]:
    b = CVBrain(provider=provider)
    print(f"{provider.upper():10} - Model: {b.model:30} URL: {b.base_url}")
