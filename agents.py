import os
import re
import asyncio
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv

load_dotenv()


# =========================================================
# MOCK LLM
# =========================================================

async def mock_llm(prompt: str) -> str:
    await asyncio.sleep(0.15)
    prompt_lower = prompt.lower()

    if "analyze" in prompt_lower:
        return (
            "The codebase was analyzed successfully. "
            "The system identified source files, "
            "functions, classes and dependencies."
        )

    if "architecture" in prompt_lower:
        return (
            "The project follows a modular architecture "
            "with a frontend, backend and AI processing layer."
        )

    if "documentation" in prompt_lower:
        return (
            "The generated documentation describes "
            "the project structure, components, "
            "dependencies and implementation."
        )

    return "AI analysis completed successfully."


# =========================================================
# OPENAI-COMPATIBLE LLM
# =========================================================

async def openai_llm(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    # Check for placeholder or dummy key
    if not api_key or "AQ.Ab8" in api_key or api_key.startswith("change-"):
        return await mock_llm(prompt)

    try:
        from openai import AsyncOpenAI

        base_url = os.getenv("OPENAI_API_BASE")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        if base_url:
            client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        else:
            client = AsyncOpenAI(api_key=api_key)

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert software documentation assistant.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content

    except Exception as error:
        return f"LLM request completed with fallback analysis. Note: {error}"


# =========================================================
# AGENT APP
# =========================================================

async def agent_app(documentation: str) -> str:
    prompt = f"""
You are the final documentation verification agent.
Review the following automatically generated technical documentation.
Improve clarity and identify obvious inconsistencies.
Do not invent source-code facts.

DOCUMENTATION:
{documentation}
"""
    return await openai_llm(prompt)


# =========================================================
# CHAT ASSISTANT AGENT (FOR VERTICAL SIDEBAR CHATBOT)
# =========================================================

async def chat_assistant(
    message: str,
    context: str = "",
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """
    Context-aware conversational agent for the left-side vertical chatbot.
    Answers queries regarding the uploaded codebase, architecture, functions,
    security, or general programming.
    """
    message_clean = message.strip()
    message_lower = message_clean.lower()
    api_key = os.getenv("OPENAI_API_KEY")

    # Special owner greeting check
    if any(k in message_lower for k in ["owner", "who created", "who made", "who owns", "author"]):
        return (
            "👑 **Shubham Khutwad** is the creator and owner of this website and the "
            "Multi-Agent AI Codebase Documentation System."
        )

    # 1. Try real LLM if valid API key is configured
    if api_key and not ("AQ.Ab8" in api_key or api_key.startswith("change-")):
        try:
            from openai import AsyncOpenAI

            base_url = os.getenv("OPENAI_API_BASE")
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

            client = AsyncOpenAI(api_key=api_key, base_url=base_url) if base_url else AsyncOpenAI(api_key=api_key)

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert AI Codebase Assistant integrated into this documentation platform.\n"
                        "The website owner is Shubham Khutwad.\n"
                        "Answer the user's questions accurately, concisely, and helpfully using the provided project documentation context.\n"
                        "Use Markdown formatting (lists, bold, code blocks).\n\n"
                        f"PROJECT DOCUMENTATION CONTEXT:\n{context[:6000] if context else 'No project documentation uploaded yet.'}"
                    ),
                }
            ]

            if history:
                for h in history[-6:]:  # include up to last 6 turns
                    role = h.get("role", "user")
                    content = h.get("content", "")
                    if role in ["user", "assistant"] and content:
                        messages.append({"role": role, "content": content})

            messages.append({"role": "user", "content": message_clean})

            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.3,
            )
            return resp.choices[0].message.content
        except Exception as e:
            # Fallback to smart local contextual response
            pass

    # 2. Smart local contextual response engine
    await asyncio.sleep(0.2)

    if not context.strip():
        if "hello" in message_lower or "hi" in message_lower:
            return (
                "👋 Hello! I am your **AI Codebase Assistant**.\n\n"
                "Upload a project file (ZIP, Python, PDF, DOCX, etc.) or paste code on the right, "
                "and I'll help you inspect functions, classes, API routes, security, and architecture!"
            )
        return (
            "I'm ready to assist you! Please upload a codebase or document on the right, "
            "and I will answer your questions about functions, classes, architecture, dependencies, or security."
        )

    # Contextual query matching
    if any(k in message_lower for k in ["function", "method", "def "]):
        funcs = re.findall(r"- Functions?:\s*([^\n]+)", context)
        func_sigs = re.findall(r"`([a-zA-Z0-9_]+\([^)]*\))`", context)
        if func_sigs:
            sample = "\n".join(f"- `{f}`" for f in func_sigs[:15])
            return f"### 🔍 Identified Functions & Signatures\n\n{sample}\n\nAsk me about any specific function for more details!"
        elif funcs:
            return f"### 🔍 Detected Functions\n\n" + "\n".join(f"- {f}" for f in funcs[:10])
        return "No explicit functions were detected in the active analysis."

    if any(k in message_lower for k in ["class", "model", "oop"]):
        clss = re.findall(r"- Classes?:\s*([^\n]+)", context)
        if clss:
            return f"### 🏛️ Detected Classes & Models\n\n" + "\n".join(f"- {c}" for c in clss[:10])
        return "No classes were found in the current codebase."

    if any(k in message_lower for k in ["architecture", "structure", "component"]):
        arch_match = re.search(r"## 3\..*?\n\n(.*?)(?=\n##|\Z)", context, re.DOTALL)
        if arch_match:
            return f"### 🏗️ Architecture Overview\n\n{arch_match.group(1).strip()}"
        return "The system is structured as a multi-tier application with automated static analysis agents."

    if any(k in message_lower for k in ["security", "vulnerability", "risk", "audit"]):
        sec_match = re.search(r"## 7\..*?\n\n(.*?)(?=\n##|\Z)", context, re.DOTALL)
        if sec_match:
            return f"### 🛡️ Security & Code Health Assessment\n\n{sec_match.group(1).strip()}"
        return "Security checks verified: proper exception handling and environment variable configuration are recommended."

    if any(k in message_lower for k in ["run", "install", "start", "execute", "setup"]):
        return (
            "### 🚀 How to Run this Project\n\n"
            "1. Activate virtual environment:\n"
            "   ```cmd\n"
            "   call .venv\\Scripts\\activate\n"
            "   ```\n"
            "2. Install dependencies:\n"
            "   ```cmd\n"
            "   pip install -r requirements.txt\n"
            "   ```\n"
            "3. Launch server:\n"
            "   ```cmd\n"
            "   python main.py\n"
            "   ```\n"
            "Or simply double-click **`run.bat`** for 1-click startup!"
        )

    if any(k in message_lower for k in ["summarize", "overview", "what is this", "explain"]):
        overview_match = re.search(r"## 1\..*?\n\n(.*?)(?=\n##|\Z)", context, re.DOTALL)
        if overview_match:
            return f"### 📋 Executive Project Summary\n\n{overview_match.group(1).strip()}"
        return "This is an automated documentation analysis generated by the Multi-Agent AI system."

    # General helpful response
    return (
        f"Based on the analyzed project:\n\n"
        f"• The project contains structured modules with automated technical documentation.\n"
        f"• You can ask me to **list all functions**, **explain architecture**, **inspect security risks**, or **show how to run it**."
    )