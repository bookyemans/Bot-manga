# systems/translation_pipeline/base_persona.py
from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path
from typing import Any, Dict, List, Optional
import io
import os
import sys

from systems.translation_pipeline.models.page_job import PageJob
from systems.translation_pipeline.models.page_data import PageData


class BasePersona(ABC):
    name: str = "Base Persona"

    @property
    def module_dir(self) -> str:
        module = sys.modules[self.__class__.__module__]
        return os.path.dirname(os.path.abspath(module.__file__))

    @cached_property
    def prompt(self) -> str:
        """Load the persona prompt once per instance, not once per page/job."""
        prompt_path = Path(self.module_dir) / "prompt.txt"
        try:
            prompt = prompt_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(
                f"Prompt file for persona {self.name!r} is unavailable: {prompt_path}"
            ) from exc
        if not prompt:
            raise RuntimeError(f"Prompt file for persona {self.name!r} is empty: {prompt_path}")
        return prompt

    @abstractmethod
    async def validate_and_update_job(self, job: PageJob, raw_json: Dict[str, Any]) -> PageJob: pass

    @abstractmethod
    async def paginate(self, job: PageJob, mode: str = "scene_split") -> List[str]: pass

    @abstractmethod
    def generate_txt(self, pages: List[PageData], session_note: Optional[str] = None) -> io.BytesIO: pass

    @abstractmethod
    def generate_docx(self, pages: List[PageData], session_note: Optional[str] = None) -> io.BytesIO: pass