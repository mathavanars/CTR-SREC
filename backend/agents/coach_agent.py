"""
coach_agent.py
Personalised AI Chat Coach grounded in profile figures and local financial knowledge.
"""
from typing import Dict, Any, List
import os
import glob
from llm_client import llm_client

class CoachAgent:
    def __init__(self, knowledge_dir: str = "knowledge"):
        self.knowledge_dir = knowledge_dir
        self.knowledge_cache = self._load_knowledge()

    def _load_knowledge(self) -> str:
        texts = []
        pattern = os.path.join(os.path.dirname(__file__), "..", "knowledge", "*.md")
        files = glob.glob(pattern)
        for filepath in files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    texts.append(f.read())
            except Exception:
                pass
        return "\n\n".join(texts)

    def respond(
        self,
        user_message: str,
        user_profile: Dict[str, Any],
        full_analysis: Dict[str, Any],
        language: str = "en"
    ) -> Dict[str, Any]:
        reply = llm_client.generate_chat_response(
            user_message=user_message,
            user_profile=user_profile,
            analysis_data=full_analysis,
            knowledge_context=self.knowledge_cache,
            language=language
        )
        return {
            "reply": reply,
            "language": language,
            "context_used": ["Profile Cashflow", "Debt Matrix", "Emergency Cushion", "Local Finance Knowledge"]
        }
