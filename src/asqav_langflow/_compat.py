"""Langflow base-class and IO resolution with a lightweight fallback.

Langflow is a heavy dependency (it pulls in a large web stack). The
component only needs the ``Component`` base class plus a handful of input
classes and the ``Data`` schema type at runtime. To keep this package
importable and unit-testable without a full Langflow install, we resolve
the real Langflow symbols when Langflow is present and fall back to small
local stubs when it is not.

Import resolution order, matching the Langflow docs:

1. Modern path (Langflow >= 1.7): ``lfx.custom.custom_component.component``
   and ``lfx.io`` / ``lfx.schema``.
2. Classic path (still compatible): ``langflow.custom``, ``langflow.io``,
   ``langflow.schema``.
3. Local stubs, so the module imports and tests run with no Langflow.

``LANGFLOW_AVAILABLE`` records whether a real Langflow was found.
"""

from __future__ import annotations

from typing import Any

LANGFLOW_AVAILABLE = False

Component: Any = None
SecretStrInput: Any = None
MessageTextInput: Any = None
MultilineInput: Any = None
Output: Any = None
Data: Any = None


def _load_real() -> bool:
    """Try the modern then classic Langflow import paths."""
    global Component, SecretStrInput, MessageTextInput, MultilineInput
    global Output, Data

    # Modern path (Langflow 1.7+).
    try:
        from lfx.custom.custom_component.component import (  # type: ignore
            Component as _Component,
        )
        from lfx.io import (  # type: ignore
            MessageTextInput as _MessageTextInput,
        )
        from lfx.io import (
            MultilineInput as _MultilineInput,
        )
        from lfx.io import (
            Output as _Output,
        )
        from lfx.io import (
            SecretStrInput as _SecretStrInput,
        )
        from lfx.schema import Data as _Data  # type: ignore

        Component = _Component
        SecretStrInput = _SecretStrInput
        MessageTextInput = _MessageTextInput
        MultilineInput = _MultilineInput
        Output = _Output
        Data = _Data
        return True
    except Exception:  # noqa: BLE001 - any failure means fall through
        pass

    # Classic path (kept compatible by Langflow).
    try:
        from langflow.custom import Component as _Component  # type: ignore
        from langflow.io import (  # type: ignore
            MessageTextInput as _MessageTextInput,
        )
        from langflow.io import (
            MultilineInput as _MultilineInput,
        )
        from langflow.io import (
            Output as _Output,
        )
        from langflow.io import (
            SecretStrInput as _SecretStrInput,
        )
        from langflow.schema import Data as _Data  # type: ignore

        Component = _Component
        SecretStrInput = _SecretStrInput
        MessageTextInput = _MessageTextInput
        MultilineInput = _MultilineInput
        Output = _Output
        Data = _Data
        return True
    except Exception:  # noqa: BLE001
        return False


class _StubInput:
    """Minimal stand-in for a Langflow input descriptor.

    Records its keyword arguments so tests can inspect ``name`` and
    ``display_name``. Real Langflow inputs carry far more behaviour; this
    only needs to be enough to declare the ``inputs`` list and let the
    class import.
    """

    def __init__(self, **kwargs: Any) -> None:
        self.name = kwargs.get("name")
        self.display_name = kwargs.get("display_name")
        self.info = kwargs.get("info")
        self.required = kwargs.get("required", False)
        self.value = kwargs.get("value")
        self._kwargs = kwargs


class _StubOutput:
    def __init__(self, **kwargs: Any) -> None:
        self.name = kwargs.get("name")
        self.display_name = kwargs.get("display_name")
        self.method = kwargs.get("method")
        self._kwargs = kwargs


class _StubData:
    """Minimal stand-in for ``langflow.schema.Data``."""

    def __init__(self, data: dict[str, Any] | None = None, **kwargs: Any) -> None:
        self.data = data or {}
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"Data(data={self.data!r})"


class _StubComponent:
    """Minimal stand-in for the Langflow ``Component`` base class.

    Real Langflow injects input values as instance attributes by ``name``
    and exposes a ``status`` attribute the editor displays. The stub keeps
    those two behaviours so the component runs identically under test.
    """

    inputs: list[Any] = []
    outputs: list[Any] = []

    def __init__(self, **kwargs: Any) -> None:
        self.status: Any = None
        for key, value in kwargs.items():
            setattr(self, key, value)


if not _load_real():
    Component = _StubComponent
    SecretStrInput = _StubInput
    MessageTextInput = _StubInput
    MultilineInput = _StubInput
    Output = _StubOutput
    Data = _StubData
else:
    LANGFLOW_AVAILABLE = True
