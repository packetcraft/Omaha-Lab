from typing import Literal
from pydantic import BaseModel, field_validator


class Persona(BaseModel):
    name: str
    description: str
    system_prompt: str
    allowed_tools: list[str]
    risk_level: Literal["low", "medium", "high"]

    @field_validator("allowed_tools")
    @classmethod
    def tools_must_be_strings(cls, v: list[str]) -> list[str]:
        for item in v:
            if not isinstance(item, str):
                raise ValueError(f"allowed_tools entries must be strings, got: {item!r}")
        return v
