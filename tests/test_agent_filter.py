"""Tests for the _filter_tools helper in agent.py."""
import pytest
from unittest.mock import MagicMock

from agent import _filter_tools
from tools import TOOLS


def _mock_persona(allowed: list[str], risk: str = "low"):
    p = MagicMock()
    p.allowed_tools = allowed
    p.risk_level = risk
    return p


class TestFilterTools:
    def test_none_persona_returns_all_tools(self):
        result = _filter_tools(TOOLS, None)
        assert result == list(TOOLS)

    def test_persona_with_single_tool(self):
        persona = _mock_persona(["get_weather"])
        result = _filter_tools(TOOLS, persona)
        assert len(result) == 1
        assert result[0].name == "get_weather"

    def test_persona_with_subset(self):
        persona = _mock_persona(["get_weather", "web_search"])
        result = _filter_tools(TOOLS, persona)
        names = {t.name for t in result}
        assert names == {"get_weather", "web_search"}

    def test_persona_with_all_tools(self):
        all_names = [t.name for t in TOOLS]
        persona = _mock_persona(all_names)
        result = _filter_tools(TOOLS, persona)
        assert len(result) == len(TOOLS)

    def test_persona_with_no_tools(self):
        persona = _mock_persona([])
        result = _filter_tools(TOOLS, persona)
        assert result == []

    def test_unknown_tool_name_is_excluded(self, capsys):
        persona = _mock_persona(["get_weather", "nonexistent_tool"])
        result = _filter_tools(TOOLS, persona)
        names = {t.name for t in result}
        assert "nonexistent_tool" not in names
        assert "get_weather" in names

    def test_unknown_tool_prints_warning(self, capsys):
        persona = _mock_persona(["nonexistent_tool"])
        _filter_tools(TOOLS, persona)
        captured = capsys.readouterr()
        assert "nonexistent_tool" in captured.out
        assert "warning" in captured.out.lower()

    def test_preserves_tool_order(self):
        all_names = [t.name for t in TOOLS]
        persona = _mock_persona(all_names)
        result = _filter_tools(TOOLS, persona)
        assert [t.name for t in result] == all_names
