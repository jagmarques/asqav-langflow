"""Unit tests for the Asqav Sign Action Langflow component.

The asqav SDK is mocked so no real API calls are made, mirroring the
mocking style of the asqav-activepieces and asqav-flowise node tests:
stub init / Agent.create / agent.sign, then assert the component wires
them together and returns the receipt fields.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

from asqav_langflow.sign_action import AsqavSignActionComponent


@pytest.fixture
def mock_asqav(monkeypatch: pytest.MonkeyPatch):
    """Install a fake `asqav` module with init / Agent.create / sign."""
    sign_mock = MagicMock(
        return_value=MagicMock(
            signature_id="sig_test_12345",
            action_id="act_test_67890",
            verification_url="https://asqav.com/verify/sig_test_12345",
            timestamp=1748476800.0,
            algorithm="ml-dsa-65",
        )
    )
    agent = MagicMock()
    agent.sign = sign_mock

    create_mock = MagicMock(return_value=agent)
    init_mock = MagicMock()

    fake = types.ModuleType("asqav")
    fake.init = init_mock
    fake.Agent = MagicMock()
    fake.Agent.create = create_mock
    monkeypatch.setitem(sys.modules, "asqav", fake)

    return types.SimpleNamespace(
        init=init_mock,
        create=create_mock,
        sign=sign_mock,
        agent=agent,
    )


def _make(**attrs) -> AsqavSignActionComponent:
    comp = AsqavSignActionComponent()
    for key, value in attrs.items():
        setattr(comp, key, value)
    return comp


def test_signs_and_returns_receipt_fields(mock_asqav):
    comp = _make(
        api_key="sk_live_xxx",
        agent_name="langflow",
        action_type="api:call",
        context='{"model":"gpt-4"}',
    )

    result = comp.build_receipt()

    # SDK was wired correctly: init -> Agent.create -> sign.
    mock_asqav.init.assert_called_once_with(api_key="sk_live_xxx")
    mock_asqav.create.assert_called_once_with("langflow")
    mock_asqav.sign.assert_called_once_with(
        action_type="api:call",
        context={"model": "gpt-4"},
    )

    # Receipt fields are surfaced on the returned Data.
    assert result.data["signature_id"] == "sig_test_12345"
    assert result.data["action_id"] == "act_test_67890"
    assert result.data["verification_url"] == "https://asqav.com/verify/sig_test_12345"
    assert result.data["timestamp"] == 1748476800.0
    assert result.data["algorithm"] == "ml-dsa-65"
    assert comp.status == "Signed: sig_test_12345"


def test_accepts_context_dict(mock_asqav):
    comp = _make(
        api_key="sk_live_xxx",
        action_type="tool:invoke",
        context={"foo": "bar"},
    )

    result = comp.build_receipt()

    mock_asqav.sign.assert_called_once_with(
        action_type="tool:invoke",
        context={"foo": "bar"},
    )
    assert result.data["signature_id"] == "sig_test_12345"


def test_empty_context_defaults_to_empty_dict(mock_asqav):
    comp = _make(api_key="sk_live_xxx", action_type="api:call", context="")
    comp.build_receipt()
    mock_asqav.sign.assert_called_once_with(action_type="api:call", context={})


def test_default_agent_name(mock_asqav):
    comp = _make(api_key="sk_live_xxx", action_type="api:call")
    comp.build_receipt()
    mock_asqav.create.assert_called_once_with("langflow")


def test_missing_api_key_returns_error_not_raise(mock_asqav):
    comp = _make(action_type="api:call")
    result = comp.build_receipt()
    assert "API key is required" in result.data["error"]
    mock_asqav.init.assert_not_called()


def test_missing_action_type_returns_error(mock_asqav):
    comp = _make(api_key="sk_live_xxx")
    result = comp.build_receipt()
    assert "Action Type" in result.data["error"]


def test_invalid_json_context_returns_error(mock_asqav):
    comp = _make(api_key="sk_live_xxx", action_type="api:call", context="{not json")
    result = comp.build_receipt()
    assert "valid JSON" in result.data["error"]
    mock_asqav.sign.assert_not_called()


def test_sdk_failure_is_reported_not_raised(mock_asqav):
    mock_asqav.sign.side_effect = RuntimeError("network down")
    comp = _make(api_key="sk_live_xxx", action_type="api:call")
    result = comp.build_receipt()
    assert "Asqav Sign Action failed" in result.data["error"]
    assert "network down" in result.data["error"]


def test_component_metadata():
    comp = AsqavSignActionComponent()
    assert comp.display_name == "Asqav Sign Action"
    input_names = [getattr(i, "name", None) for i in comp.inputs]
    assert input_names == ["api_key", "agent_name", "action_type", "context"]
    output_methods = [getattr(o, "method", None) for o in comp.outputs]
    assert output_methods == ["build_receipt"]
