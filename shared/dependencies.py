"""Typed access to application-scoped dependencies stored by the Telegram app."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from shared.container import ServiceContainer


CONTAINER_KEY = "container"


def get_container(bot_data: Mapping[str, Any]) -> "ServiceContainer":
    """Return the initialized service container or fail with a useful error."""
    from shared.container import ServiceContainer

    container = bot_data.get(CONTAINER_KEY)
    if not isinstance(container, ServiceContainer):
        raise RuntimeError(
            "Application services are not initialized; expected a ServiceContainer "
            f"in bot_data[{CONTAINER_KEY!r}]."
        )
    return container
