# Phase 07 — Translation engines, personas, and prompts

## Scope
This phase hardens persona discovery and prompt lifecycle without changing translation output schemas, provider request formats, database schema, or Telegram delivery behavior.

## Changes
- `systems/translation_pipeline/base_persona.py`
  - Persona prompts are now loaded lazily and cached per persona instance using `cached_property`, avoiding repeated disk reads for every processed page.
  - Missing or empty prompt files raise a clear `RuntimeError` identifying the persona and prompt path.
- `systems/translation_pipeline/registry.py`
  - Plugin directories are discovered in stable, case-insensitive sorted order.
  - Only persona classes declared by the plugin module are registered; imported subclasses are ignored.
  - Persona keys are normalized with `casefold()` and whitespace trimming.
  - Empty and duplicate names are handled safely; the first discovered duplicate is retained and logged.
  - Unknown or empty persona selections fall back to `Default Translator` when it is registered.
- `tests/test_translation_personas.py`
  - Added coverage for deterministic discovery, case-insensitive lookup, default fallback, prompt caching, and missing prompt diagnostics.

## Verification
- Baseline before edits: `48 passed in 3.46s`.
- Full test suite after edits: `51 passed in 3.47s`.
- `python -m compileall -q systems tests/test_translation_personas.py`: passed.

## Compatibility and boundaries
- No database or migration changes.
- No new runtime dependencies.
- Gemini provider request/retry/key-rotation behavior and JSON response contract were not modified.
- Persona prompt text, persona-specific validation, pagination, TXT/DOCX generation, and delivery strategies were not intentionally changed.
- Prompt caching means edits to a prompt file during a running process are not picked up by existing persona instances; restart/reload the process to apply prompt-file changes.
- This phase does not establish translation quality against live Gemini calls and does not perform Telegram integration or low-memory host tests.
