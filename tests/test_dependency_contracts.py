from __future__ import annotations

import pytest

from shared.dependencies import get_container
from shared.container import ServiceContainer


def test_get_container_returns_initialized_container():
    # ServiceContainer is intentionally assembled by the composition root.
    marker = object()
    container = ServiceContainer(
        db=marker, bot=marker, event_bus=marker,
        access=marker, api_keys=marker, settings=marker,
        ai=marker, personas=marker, queue=marker, jobs=marker,
        batch=marker, renderer=marker, delivery=marker, notifier=marker,
        glossary=marker,
    )
    assert get_container({"container": container}) is container


def test_get_container_fails_clearly_before_initialization():
    with pytest.raises(RuntimeError, match="not initialized"):
        get_container({})


def test_get_container_rejects_wrong_object():
    with pytest.raises(RuntimeError, match="ServiceContainer"):
        get_container({"container": object()})
