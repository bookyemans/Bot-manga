from pathlib import Path

import pytest

from systems.translation_pipeline.base_persona import BasePersona
from systems.translation_pipeline.registry import PersonaRegistry


def test_registry_discovers_personas_deterministically_and_has_default_fallback():
    registry = PersonaRegistry()
    names = registry.get_available_personas()

    assert names == sorted(names, key=str.casefold)
    assert "Default Translator" in names
    assert registry.get_handler("nAbIl").name == "NABIL"
    assert registry.get_handler("unknown persona").name == "Default Translator"
    assert registry.get_handler(None).name == "Default Translator"


def test_persona_prompt_is_cached_per_instance():
    persona = PersonaRegistry().get_handler("Default Translator")
    assert persona is not None

    first = persona.prompt
    prompt_path = Path(persona.module_dir) / "prompt.txt"
    original = prompt_path.read_text(encoding="utf-8")
    try:
        prompt_path.write_text("changed prompt", encoding="utf-8")
        assert persona.prompt == first
    finally:
        prompt_path.write_text(original, encoding="utf-8")


def test_persona_prompt_missing_file_has_clear_error(tmp_path, monkeypatch):
    class PromptlessPersona(BasePersona):
        name = "Promptless"

        async def validate_and_update_job(self, job, raw_json):
            return job

        async def paginate(self, job, mode="scene_split"):
            return []

        def generate_txt(self, pages, session_note=None):
            raise NotImplementedError

        def generate_docx(self, pages, session_note=None):
            raise NotImplementedError

    persona = PromptlessPersona()
    # Point the module directory at a controlled, empty directory.
    monkeypatch_module = type("Module", (), {"__file__": str(tmp_path / "persona.py")})
    import sys
    monkeypatch.setitem(sys.modules, PromptlessPersona.__module__, monkeypatch_module)
    with pytest.raises(RuntimeError, match="Prompt file.*unavailable"):
        _ = persona.prompt
