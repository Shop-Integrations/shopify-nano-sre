"""LLM utility functions for litellm integration."""

import logging

try:
    import litellm

    litellm.suppress_warnings = True
except ImportError:
    pass

logger = logging.getLogger(__name__)


def is_vision_model(model_name: str) -> bool:
    """
    Check if the model supports vision/image inputs.

    Args:
        model_name: Name of the LLM model

    Returns:
        True if vision model, False otherwise
    """
    vision_keywords = [
        "vision",
        "gpt-4-turbo",
        "gpt-4o",
        "claude-3",
        "llama-3.2",
        "pixtral",
        "gemini",
    ]
    return any(keyword in model_name.lower() for keyword in vision_keywords)


def get_litellm_model_identifier(provider: str, model: str) -> str:
    """
    Get the correct model identifier for litellm.

    Args:
        provider: LLM provider (openai, anthropic, ollama, openrouter)
        model: Model name

    Returns:
        Formatted model identifier for litellm
    """
    # litellm uses provider-specific prefixes
    if provider == "anthropic":
        if not model.startswith("claude"):
            return f"claude-{model}"
        return model
    elif provider == "ollama":
        if not model.startswith("ollama/"):
            return f"ollama/{model}"
        return model
    elif provider == "openrouter":
        if not model.startswith("openrouter/"):
            return f"openrouter/{model}"
        return model
    else:  # openai and others
        return model
