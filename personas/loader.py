from pathlib import Path

import yaml
from pydantic import ValidationError

from personas.schema import Persona

_PERSONAS_DIR = Path(__file__).parent


class PersonaLoader:
    @staticmethod
    def load(name: str) -> Persona:
        """Load and validate a persona YAML by slug (e.g., 'customer_service')."""
        path = _PERSONAS_DIR / f"{name}.yaml"
        if not path.exists():
            available = PersonaLoader.list_personas()
            raise FileNotFoundError(
                f"Persona '{name}' not found.\n"
                f"Available: {', '.join(available) or '(none)'}"
            )
        with open(path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh)
        try:
            return Persona.model_validate(raw)
        except ValidationError as exc:
            raise ValueError(f"Invalid persona config '{path.name}':\n{exc}") from exc

    @staticmethod
    def list_personas() -> list[str]:
        """Return sorted slug names for all *.yaml files in the personas directory."""
        return sorted(p.stem for p in _PERSONAS_DIR.glob("*.yaml"))
