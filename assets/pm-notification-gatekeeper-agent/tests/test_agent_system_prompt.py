"""Tests for agent system prompt and configuration decorators."""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "app"))


def test_system_prompt_contains_human_in_the_loop():
    """System prompt includes the human-in-the-loop instruction."""
    from agent import get_system_prompt
    prompt = get_system_prompt()
    assert "Accept agent recommendation" in prompt
    assert "Override agent recommendation" in prompt
    assert "Request more information" in prompt


def test_system_prompt_contains_plant_session_instruction():
    """System prompt instructs agent to ask for plant if not provided."""
    from agent import get_system_prompt
    prompt = get_system_prompt()
    assert "plant" in prompt.lower()
    assert "session" in prompt.lower()


def test_system_prompt_contains_guardrails():
    """System prompt includes key guardrails."""
    from agent import get_system_prompt
    prompt = get_system_prompt()
    assert "fabricate" in prompt.lower() or "invent" in prompt.lower()
    assert "NOCO" in prompt or "duplicate" in prompt.lower()


def test_system_prompt_contains_pagination_limit():
    """System prompt instructs agent to set page size to max 100."""
    from agent import get_system_prompt
    prompt = get_system_prompt()
    assert "100" in prompt


def test_get_model_name_returns_string():
    """Model name function returns a non-empty string."""
    from agent import get_model_name
    model = get_model_name()
    assert isinstance(model, str)
    assert len(model) > 0


def test_get_temperature_returns_float():
    """Temperature function returns a float."""
    from agent import get_temperature
    temp = get_temperature()
    assert isinstance(temp, float)
    assert 0.0 <= temp <= 1.0


def test_system_prompt_no_hardcoded_plant():
    """System prompt does not hardcode any specific plant number."""
    from agent import get_system_prompt
    prompt = get_system_prompt()
    # Should not contain '1710' as a hardcoded value
    assert "1710" not in prompt
