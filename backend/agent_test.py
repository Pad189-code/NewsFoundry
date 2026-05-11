"""Test PydanticAI + Gemini (appel réel).

Exemple historique avec ``GeminiModel('gemini-1.5-flash', api_key=...)`` :
``api_key`` n'est plus un argument du constructeur, et ``gemini-1.5-flash`` peut
renvoyer 404 sur l'API ``v1beta``. Ici on utilise ``GoogleModel`` + ``GoogleProvider``
(``GOOGLE_API_KEY``), comme recommandé par PydanticAI.

Lancement : ``cd backend`` puis ``uv run python agent_test.py``
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

load_dotenv(Path(__file__).resolve().parent / ".env")

api_key = (os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or "").strip()
if not api_key:
    print("Clé manquante : définissez GOOGLE_API_KEY dans backend/.env.", file=sys.stderr)
    sys.exit(1)

# Même famille que OPENAI_MODEL=google-gla:gemini-2.0-flash dans l'app
model_name = (os.getenv("GEMINI_TEST_MODEL") or "gemini-2.0-flash").strip()
model = GoogleModel(model_name, provider=GoogleProvider(api_key=api_key))

agent = Agent(model=model, system_prompt="Tu es un assistant sarcastique mais utile.")


def run_agent() -> None:
    result = agent.run_sync("Pourquoi est-ce que PostgreSQL est mieux que Excel ?")
    # Réponse du modèle (l'ancien attribut ``.data`` n'existe pas sur AgentRunResult)
    print(result.output)


if __name__ == "__main__":
    run_agent()
