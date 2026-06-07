"""
Strands-based AI agent for adaptive learning guidance.
Uses OpenAI GPT-4o via Amazon Strands Agents SDK.
"""
import asyncio
import json
import os
import re

from strands import Agent
from strands.models.openai import OpenAIModel

from app.config import settings

# Ensure the env var is set so the OpenAI client can authenticate
os.environ.setdefault("OPENAI_API_KEY", settings.OPENAI_API_KEY)


def _make_agent(system_prompt: str) -> Agent:
    model = OpenAIModel(model_id="gpt-4o")
    return Agent(model=model, system_prompt=system_prompt)


# ---------------------------------------------------------------------------
# Plan generation
# ---------------------------------------------------------------------------

PLAN_SYSTEM_PROMPT = """You are an expert programming tutor specializing in C++ for undergraduate students.
Your job is to analyze a programming task and create a clear, pedagogically sound step-by-step learning plan.

Rules for creating the plan:
1. Focus FIRST on correctness steps — getting the logic right, implementing required methods/classes.
2. Add optimization/cleanup steps LAST (improve code quality, handle edge cases, refactor).
3. Each step should be achievable in 5-15 minutes by an intermediate student.
4. Steps must build on each other — never require something not yet implemented.
5. Keep descriptions concise and actionable — tell the student exactly what to do.
6. Do NOT reveal the complete solution in any step description.
7. Typically 4-8 steps is ideal.

You MUST respond with valid JSON only, no markdown fences, in this exact format:
[
  {
    "title": "Short title (max 60 chars)",
    "description": "What the student should implement in this step.",
    "step_type": "correctness"
  },
  ...
]
"""


async def generate_plan(task_requirements: str, model_solution: str, language: str = "cpp") -> list[dict]:
    """Generate step-by-step plan. Returns list of {title, description, step_type}."""
    prompt = f"""Task requirements:
{task_requirements}

Model solution (for your reference only — do not reveal it):
{model_solution}

Language: {language}

Generate the step-by-step learning plan as JSON."""

    agent = _make_agent(PLAN_SYSTEM_PROMPT)
    result = await asyncio.to_thread(agent, prompt)
    text = str(result)

    # Strip markdown fences if present
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()

    try:
        steps = json.loads(text)
        if not isinstance(steps, list):
            raise ValueError("Expected a list")
        return steps
    except (json.JSONDecodeError, ValueError):
        # Fallback: extract JSON array from text
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise RuntimeError(f"Agent returned invalid plan JSON: {text[:200]}")


# ---------------------------------------------------------------------------
# Step evaluation
# ---------------------------------------------------------------------------

EVAL_SYSTEM_PROMPT = """You are an expert C++ programming tutor evaluating a student's code.
Be encouraging but honest. Focus on whether the current step's goal is achieved.

You MUST respond with valid JSON only (no markdown), in this exact format:
{
  "passed": true/false,
  "feedback": "Concise feedback (2-4 sentences). If passed: praise + what's next. If failed: specific guidance on what's missing or wrong."
}
"""


async def evaluate_step(
    step_title: str,
    step_description: str,
    student_code: str,
    task_requirements: str,
    attempt_number: int = 1,
) -> dict:
    """Returns {passed: bool, feedback: str}."""
    prompt = f"""Task requirements (for context):
{task_requirements}

Current step to evaluate:
Title: {step_title}
What the student should have done: {step_description}

Student's code (attempt #{attempt_number}):
```cpp
{student_code}
```

Does this code satisfy the current step? Respond with JSON."""

    agent = _make_agent(EVAL_SYSTEM_PROMPT)
    result = await asyncio.to_thread(agent, prompt)
    text = str(result)
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()

    try:
        data = json.loads(text)
        return {"passed": bool(data.get("passed", False)), "feedback": data.get("feedback", "")}
    except (json.JSONDecodeError, KeyError):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return {"passed": bool(data.get("passed", False)), "feedback": data.get("feedback", "")}
        return {"passed": False, "feedback": text}


# ---------------------------------------------------------------------------
# Error explanation
# ---------------------------------------------------------------------------

EXPLAIN_SYSTEM_PROMPT = """You are a C++ programming tutor helping a student understand why their code failed.

Rules:
- Explain the root cause of the error in plain language (no jargon).
- Point to the specific line or construct that caused it.
- Give ONE clear, actionable fix — what exactly the student needs to add or change.
- Do not write the full corrected code for them.
- Keep it to 4-6 sentences.
"""


async def explain_test_errors(
    student_code: str,
    errors: list[str],
    task_requirements: str,
) -> str:
    errors_text = "\n---\n".join(errors)
    prompt = f"""Task requirements (for context):
{task_requirements}

Student's code:
```cpp
{student_code}
```

Errors from the test runner:
{errors_text}

Explain what is wrong and how to fix it."""

    agent = _make_agent(EXPLAIN_SYSTEM_PROMPT)
    result = await asyncio.to_thread(agent, prompt)
    return str(result).strip()


# ---------------------------------------------------------------------------
# Hint generation
# ---------------------------------------------------------------------------

HINT_SYSTEM_PROMPT = """You are a helpful C++ programming tutor giving a hint to a student.
Rules:
- Give ONE specific, actionable hint.
- Do NOT give the answer or write code for them.
- Keep it to 2-3 sentences.
- Be encouraging.
"""


async def get_hint(
    step_title: str,
    step_description: str,
    student_code: str,
) -> str:
    prompt = f"""Current step: {step_title}
What the student should implement: {step_description}

Student's current code:
```cpp
{student_code}
```

Give a hint to help them move forward without revealing the solution."""

    agent = _make_agent(HINT_SYSTEM_PROMPT)
    result = await asyncio.to_thread(agent, prompt)
    return str(result).strip()
