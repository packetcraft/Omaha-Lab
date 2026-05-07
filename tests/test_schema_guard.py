"""Tests for guardrails/schema_guard.py — validate_tool_result rules."""
import pytest
from guardrails.schema_guard import validate_tool_result


class TestTypeCheck:
    def test_none_is_invalid(self):
        ok, msg = validate_tool_result("any_tool", None)
        assert not ok
        assert "NoneType" in msg

    def test_int_is_invalid(self):
        ok, msg = validate_tool_result("any_tool", 42)
        assert not ok
        assert "int" in msg

    def test_list_is_invalid(self):
        ok, msg = validate_tool_result("any_tool", ["a", "b"])
        assert not ok
        assert "list" in msg


class TestEmptyCheck:
    def test_empty_string_is_invalid(self):
        ok, msg = validate_tool_result("any_tool", "")
        assert not ok
        assert "empty" in msg

    def test_whitespace_only_is_invalid(self):
        ok, msg = validate_tool_result("any_tool", "   \n\t  ")
        assert not ok
        assert "empty" in msg

    def test_nonempty_string_passes(self):
        ok, msg = validate_tool_result("any_tool", "some result")
        assert ok
        assert msg is None


class TestHttpGetJsonCheck:
    def test_valid_json_object_passes(self):
        ok, msg = validate_tool_result("http_get", '{"key": "value"}')
        assert ok

    def test_malformed_json_is_invalid(self):
        ok, msg = validate_tool_result("http_get", '{"key": ')
        assert not ok
        assert "json" in msg.lower()

    def test_non_json_response_skips_check(self):
        ok, msg = validate_tool_result("http_get", "plain text response")
        assert ok

    def test_json_array_skips_check(self):
        # Arrays don't start with '{' — JSON check is skipped
        ok, msg = validate_tool_result("http_get", '[1, 2, 3]')
        assert ok

    def test_json_check_only_applies_to_http_get(self):
        ok, msg = validate_tool_result("web_search", '{"broken": ')
        assert ok  # web_search is not subject to the JSON rule


class TestPassingCases:
    @pytest.mark.parametrize("tool_name,result", [
        ("get_weather", "Location: Denver, US\nTemperature: 72°F"),
        ("web_search",  "1. Some Result\n   https://example.com"),
        ("read_file",   "file contents here"),
        ("write_file",  "Wrote 42 characters to workspace/out.txt"),
        ("http_get",    "200 OK — response body here"),
    ])
    def test_normal_results_pass(self, tool_name, result):
        ok, msg = validate_tool_result(tool_name, result)
        assert ok
        assert msg is None
