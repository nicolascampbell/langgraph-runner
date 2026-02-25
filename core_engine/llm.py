import os

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI


def get_llm(provider: str, model_name: str, temperature: float):
    """
    Dynamic factory that returns the appropriate LangChain Chat model
    based on the requested provider. Falls back to OpenAI if the provider's
    API key is missing from the environment.
    """
    provider = provider.lower().strip()

    # Check for keys
    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    google_key = os.environ.get("GOOGLE_API_KEY")

    if provider == "anthropic" and anthropic_key:
         return ChatAnthropic(
             model_name=model_name,
             temperature=temperature,
             api_key=anthropic_key
         )
    elif provider == "google" and google_key:
         return ChatGoogleGenerativeAI(
             model=model_name,
             temperature=temperature,
             api_key=google_key
         )
    elif provider == "openai" and openai_key:
         return ChatOpenAI(
             model=model_name,
             temperature=temperature,
             api_key=openai_key
         )
    else:
         # Fallback to OpenAI if a key is missing or provider is unknown
         print(f"Warning: Provider '{provider}' requested but key is missing (or provider unknown). Falling back to OpenAI gpt-4o-mini.")
         return ChatOpenAI(
             model="gpt-4o-mini",
             temperature=temperature,
             api_key=openai_key
         )
