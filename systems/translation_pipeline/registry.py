from __future__ import annotations

import importlib
import inspect
import logging
from pathlib import Path
from typing import Dict, List

from systems.translation_pipeline.base_persona import BasePersona

logger = logging.getLogger(__name__)


class PersonaRegistry:
    """Discovers and owns persona instances for the translation pipeline."""

    DEFAULT_NAME = "default translator"

    def __init__(self, plugins_dir: str = "systems/translation_pipeline/plugins") -> None:
        self._handlers: Dict[str, BasePersona] = {}
        self._plugins_dir = Path(plugins_dir).resolve()
        self._discover_personas()

    def _discover_personas(self) -> None:
        if not self._plugins_dir.is_dir():
            logger.error("Plugins directory not found: %s", self._plugins_dir)
            return

        for plugin_dir in sorted(self._plugins_dir.iterdir(), key=lambda path: path.name.casefold()):
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("_"):
                continue
            module_name = f"systems.translation_pipeline.plugins.{plugin_dir.name}.persona"
            try:
                module = importlib.import_module(module_name)
                for _, candidate in inspect.getmembers(module, inspect.isclass):
                    if candidate is BasePersona or not issubclass(candidate, BasePersona):
                        continue
                    # Ignore imported BasePersona subclasses; only register classes
                    # declared by this plugin module.
                    if candidate.__module__ != module.__name__:
                        continue
                    instance = candidate()
                    name = instance.name.strip()
                    if not name:
                        logger.warning("Ignoring persona with empty name in %s", module_name)
                        continue
                    key = name.casefold()
                    if key in self._handlers:
                        logger.warning("Duplicate persona name %r in %s; keeping first", name, module_name)
                        continue
                    self._handlers[key] = instance
                    logger.info("Loaded persona plugin: %s", name)
            except Exception:
                logger.exception("Failed to load persona from %s", module_name)

        if self.DEFAULT_NAME not in self._handlers:
            logger.critical("Default Translator persona failed to load; no default fallback available")

    def get_handler(self, persona_name: str | None) -> BasePersona | None:
        if persona_name:
            handler = self._handlers.get(persona_name.strip().casefold())
            if handler is not None:
                return handler
        return self._handlers.get(self.DEFAULT_NAME)

    def get_available_personas(self) -> List[str]:
        return [persona.name for persona in self._handlers.values()]
