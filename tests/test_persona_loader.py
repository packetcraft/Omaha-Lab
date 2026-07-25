"""Tests for personas/loader.py and personas/schema.py."""
import pytest
from personas.loader import PersonaLoader
from personas.schema import Persona

KNOWN_SLUGS = {
    "customer_service", "hr_assistant", "security_analyst", "code_assistant",
    "devops_assistant",
}
VALID_RISK_LEVELS = {"low", "medium", "high"}


# ---------------------------------------------------------------------------
# PersonaLoader.list_personas
# ---------------------------------------------------------------------------

class TestListPersonas:
    def test_returns_all_four_slugs(self):
        slugs = PersonaLoader.list_personas()
        assert KNOWN_SLUGS == set(slugs)

    def test_returns_sorted_list(self):
        slugs = PersonaLoader.list_personas()
        assert slugs == sorted(slugs)


# ---------------------------------------------------------------------------
# PersonaLoader.load — happy path
# ---------------------------------------------------------------------------

class TestLoadPersona:
    @pytest.mark.parametrize("slug", sorted(KNOWN_SLUGS))
    def test_all_personas_load(self, slug):
        persona = PersonaLoader.load(slug)
        assert isinstance(persona, Persona)

    @pytest.mark.parametrize("slug", sorted(KNOWN_SLUGS))
    def test_name_is_nonempty(self, slug):
        persona = PersonaLoader.load(slug)
        assert persona.name.strip()

    @pytest.mark.parametrize("slug", sorted(KNOWN_SLUGS))
    def test_system_prompt_is_nonempty(self, slug):
        persona = PersonaLoader.load(slug)
        assert persona.system_prompt.strip()

    @pytest.mark.parametrize("slug", sorted(KNOWN_SLUGS))
    def test_allowed_tools_are_strings(self, slug):
        persona = PersonaLoader.load(slug)
        assert all(isinstance(t, str) for t in persona.allowed_tools)

    @pytest.mark.parametrize("slug", sorted(KNOWN_SLUGS))
    def test_risk_level_is_valid(self, slug):
        persona = PersonaLoader.load(slug)
        assert persona.risk_level in VALID_RISK_LEVELS

    def test_customer_service_tool_subset(self):
        persona = PersonaLoader.load("customer_service")
        assert "get_weather" in persona.allowed_tools
        # customer_service should NOT have write_file (high-blast-radius tool)
        assert "write_file" not in persona.allowed_tools


# ---------------------------------------------------------------------------
# PersonaLoader.load — error cases
# ---------------------------------------------------------------------------

class TestLoadPersonaErrors:
    def test_missing_slug_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            PersonaLoader.load("nonexistent_persona")

    def test_error_lists_available_personas(self):
        with pytest.raises(FileNotFoundError) as exc_info:
            PersonaLoader.load("does_not_exist")
        # The error message should mention available slugs
        msg = str(exc_info.value)
        assert any(slug in msg for slug in KNOWN_SLUGS)
