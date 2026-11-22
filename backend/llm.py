"""Send ArthMitra coach questions to GroqCloud."""

import json
import logging
import os

import httpx


LOGGER = logging.getLogger(__name__)
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
EDUCATIONAL_DISCLAIMER = "Educational guidance only, not licensed financial advice."
COACH_SYSTEM_PROMPT = (
    "You are ArthMitra's investing coach for beginners in India. Answer any question "
    "about investing, saving, debt, goals, or the user's numbers in simple language. "
    "Use the user's saved data when relevant and quote exact figures from it. Label "
    "every projection as an estimate and state the assumed return rate and time period. "
    "Never promise or guarantee returns. If data is missing, say exactly what is missing "
    "and what the user should add, then still explain the concept. Do not refuse general "
    "investing questions. Keep answers short, with a clear next step. End with one line: "
    "'Educational guidance only, not licensed financial advice.'"
)


class CoachServiceError(RuntimeError):
    """The configured GroqCloud service could not provide a coach answer."""


def ask_groq(question: str, context: dict[str, object]) -> str:
    """Ask GroqCloud using the saved user context and return a safe short answer."""
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        LOGGER.error("GroqCloud coach call failed because LLM_API_KEY is not configured.")
        raise CoachServiceError(
            "The AI coach is not configured. Set LLM_API_KEY on the server and try again."
        )

    messages = [
        {"role": "system", "content": COACH_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Saved financial data (JSON): "
                f"{json.dumps(context, ensure_ascii=False, default=str)}\n\n"
                "When asked about past growth, distinguish saved account-value history "
                "from an estimate. If past_growth_available is false, say that actual "
                "history is unavailable. If a saved two-year estimate is present, offer "
                "or provide it with its amount, assumptions, and period; otherwise state "
                "that a saved monthly amount is missing.\n\n"
                f"User question: {question}"
            ),
        },
    ]
    try:
        response = httpx.post(
            GROQ_CHAT_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": GROQ_MODEL,
                "messages": messages,
                "temperature": 0.3,
                "max_completion_tokens": 500,
            },
            timeout=20.0,
        )
        response.raise_for_status()
        answer = response.json()["choices"][0]["message"]["content"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("GroqCloud returned an empty coach answer.")
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as error:
        LOGGER.error(
            "GroqCloud coach call failed (%s): %s",
            type(error).__name__,
            error,
            exc_info=True,
        )
        raise CoachServiceError(
            "The AI coach could not get an answer from GroqCloud. Please try again."
        ) from error

    answer = answer.strip()
    if not answer.endswith(EDUCATIONAL_DISCLAIMER):
        answer = f"{answer.rstrip()}\n\n{EDUCATIONAL_DISCLAIMER}"
    return answer
