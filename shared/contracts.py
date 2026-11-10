"""Structural contracts shared between application layers.

Protocols keep the modular monolith loosely coupled without introducing a
runtime DI framework or additional dependencies.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class AsyncClosable(Protocol):
    async def close(self) -> None: ...


@runtime_checkable
class DatabaseContract(AsyncClosable, Protocol):
    async def connect(self) -> None: ...


@runtime_checkable
class EventBusContract(Protocol):
    def subscribe(self, event: str, handler: Any) -> None: ...
    async def publish(self, event: str, payload: Any = None) -> None: ...


@runtime_checkable
class AIProviderContract(AsyncClosable, Protocol):
    async def extract_raw_json(self, image_bytes: bytes, job_id: Any,
                               prompt_text: str, api_keys: list[str]) -> dict[str, Any]: ...


@runtime_checkable
class JobLifecycleContract(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...


@runtime_checkable
class DeliveryContract(Protocol):
    async def process(self, job: Any) -> Any: ...
    async def render(self, job: Any) -> Any: ...
    async def send(self, job: Any) -> Any: ...


@runtime_checkable
class ErrorNotifierContract(Protocol):
    async def notify(self, job: Any, error: Exception) -> None: ...
