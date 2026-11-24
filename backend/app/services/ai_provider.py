"""AI providers (Phase 8). The app works fully with the offline provider; the
Claude provider is optional, OFF by default, and only used when an administrator
sets YANA_AI_PROVIDER=claude (with IT approval) and installs the `anthropic` SDK.

Providers only *propose*; nothing is saved until a planner accepts it.
"""

from __future__ import annotations

import importlib.util
import logging
from abc import ABC, abstractmethod
from datetime import date

from app.core.config import get_settings
from app.engines.text_extract import ExtractedRequirements, extract

log = logging.getLogger("yana.ai")


class AIUnavailable(Exception):
    """The provider could not answer (network, quota, refusal...). Callers fall back to the offline reader."""


class AIProvider(ABC):
    name: str
    label: str
    sends_data_off_device: bool

    @abstractmethod
    def extract_requirements(self, text: str, *, today: date, known_countries: list[str], known_cities: list[str]) -> ExtractedRequirements: ...


class OfflineProvider(AIProvider):
    name = "offline"
    label = "Offline reader (runs on this computer)"
    sends_data_off_device = False

    def extract_requirements(self, text, *, today, known_countries, known_cities):
        return extract(text, today=today, known_countries=known_countries, known_cities=known_cities)


SYSTEM_PROMPT = """You read emails from travel agents to a European destination management company (DMC) and extract the \
customer's travel requirements into the given schema.

Rules:
- Extract only what the text states or clearly implies. Leave a field empty when it is not mentioned; never guess.
- Dates: today is {today}. Resolve dates without a year to the next future occurrence. If only a start date and a trip \
length are given, departure = start + (days - 1).
- adults/children: when only a total is given ("family of 6") and children are mentioned, adults = total - children.
- countries/cities: copy place names as written. Prefer these known names where they match: {places}.
- Food: "veg"/"pure veg" with Indian travellers means indian_vegetarian; Jain means indian_jain.
- budget: per person when the text says pp/per person/each, otherwise a total; currency as an ISO code.
- special_requests: short phrases for accessibility, celebrations, infants, allergies or other notes.
- evidence: for each filled field, a short exact quote from the email."""


class ClaudeProvider(AIProvider):
    name = "claude"
    label = "Claude (Anthropic API, data leaves this computer)"
    sends_data_off_device = True

    def __init__(self, model: str):
        self.model = model

    def extract_requirements(self, text, *, today, known_countries, known_cities):
        import anthropic  # optional dependency, imported only when this provider is switched on

        client = anthropic.Anthropic()  # credentials from the environment (ANTHROPIC_API_KEY or an `ant auth login` profile)
        places = ", ".join(sorted(set(known_countries + known_cities))[:400]) or "(none)"
        try:
            response = client.messages.parse(
                model=self.model,
                max_tokens=16000,
                system=SYSTEM_PROMPT.format(today=today.isoformat(), places=places),
                messages=[{"role": "user", "content": f"<email>\n{text}\n</email>"}],
                output_format=ExtractedRequirements,
            )
        except anthropic.AuthenticationError as exc:
            raise AIUnavailable("The Claude API key is missing or invalid.") from exc
        except anthropic.RateLimitError as exc:
            raise AIUnavailable("The Claude API is busy (rate limit). Try again shortly.") from exc
        except anthropic.APIStatusError as exc:
            raise AIUnavailable(f"The Claude API returned an error ({exc.status_code}).") from exc
        except anthropic.APIConnectionError as exc:
            raise AIUnavailable("Cannot reach the Claude API from this computer.") from exc
        if response.stop_reason == "refusal" or response.parsed_output is None:
            raise AIUnavailable("Claude did not return requirements for this text.")
        return response.parsed_output


def anthropic_installed() -> bool:
    return importlib.util.find_spec("anthropic") is not None


def get_provider() -> AIProvider:
    s = get_settings()
    if s.ai_provider == "claude":
        if anthropic_installed():
            return ClaudeProvider(s.ai_model)
        log.warning("YANA_AI_PROVIDER=claude but the 'anthropic' package is not installed; using the offline reader.")
    return OfflineProvider()


def status() -> dict:
    s = get_settings()
    p = get_provider()
    return {
        "provider": p.name, "label": p.label, "sends_data_off_device": p.sends_data_off_device,
        "configured_provider": s.ai_provider, "model": s.ai_model if p.name == "claude" else None,
        "claude_sdk_installed": anthropic_installed(),
    }
