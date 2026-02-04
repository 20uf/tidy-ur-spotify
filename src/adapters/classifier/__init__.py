"""LLM classifier adapters and provider registry."""

PROVIDERS = {
    "openai": {
        "name": "OpenAI",
        "default_model": "gpt-4o-mini",
        "label": "OpenAI (GPT)",
        "url": "https://platform.openai.com/api-keys",
    },
    "anthropic": {
        "name": "Anthropic",
        "default_model": "claude-3-haiku-20240307",
        "label": "Anthropic",
        "url": "https://console.anthropic.com",
    },
}

DEFAULT_PROVIDER = "openai"
