import os
from dotenv import load_dotenv
from core_engine.llm import get_llm
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

def test_models():
    print("Testing Anthropic...")
    try:
        llm = get_llm("anthropic", "claude-3-haiku-20240307", 0.7)
        resp = llm.invoke([HumanMessage(content="Say hi")])
        print(resp.content)
    except Exception as e:
        print(f"Anthropic Exception: {e}")

    print("\nTesting Google...")
    try:
        llm = get_llm("google", "gemini-1.5-flash", 0.7)
        resp = llm.invoke([HumanMessage(content="Say hi")])
        print(resp.content)
    except Exception as e:
        print(f"Google Exception: {e}")

if __name__ == "__main__":
    test_models()
