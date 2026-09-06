"""Real lfx evaluator/output dispatcher and SDK; only HTTP is substituted."""

import hashlib
import json
import re
import shutil
import socket
from pathlib import Path

import httpx
import pytest
from lfx.custom.custom_component.component import Component
from lfx.custom.eval import eval_custom_component_code
from lfx.schema import Data

import asqav_langflow.sign_action as integration
from asqav_langflow._compat import LANGFLOW_AVAILABLE

RESPONSE = {
    "signature": "synthetic-response",
    "signature_id": "sig_fixture",
    "action_id": "act_fixture",
    "verification_url": "https://example.invalid/receipt",
    "timestamp": "2026-09-06T00:00:00Z",
    "algorithm": "ml-dsa-65",
}


@pytest.fixture
def api(monkeypatch):
    import asqav.client as sdk

    calls = []
    settings = {"status": 200, "stage": "sign", "decision": "permit"}
    monkeypatch.delenv("ASQAV_MODE", raising=False)
    monkeypatch.setattr(sdk, "_api_base", "https://api.asqav.com/api/v1")

    def blocked(*args, **kwargs):
        raise AssertionError("Network forbidden in Langflow integration tests")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)

    def send(client, request, **kwargs):
        path = request.url.path
        assert request.url.host == "api.asqav.com"
        assert path in ("/api/v1/agents/create", "/api/v1/agents/agent_fixture/sign")
        assert request.headers["X-API-Key"] == "test-only-key"
        body = json.loads(request.content)
        calls.append((path, body))
        stage = "create" if path.endswith("/create") else "sign"
        if settings["stage"] == stage and settings["status"] != 200:
            return httpx.Response(
                settings["status"], json={"detail": "test refusal"}, request=request
            )
        if stage == "create":
            response = {
                "agent_id": "agent_fixture",
                "name": body["name"],
                "public_key": "public_fixture",
                "key_id": "key_fixture",
                "algorithm": "ml-dsa-65",
                "capabilities": [],
                "created_at": 1700000000.0,
            }
        else:
            response = {**RESPONSE, "policy_decision": settings["decision"]}
            if settings.get("malformed"):
                response.pop("signature_id")
        return httpx.Response(200, json=response, request=request)

    monkeypatch.setattr(httpx.Client, "send", send)
    yield calls, settings
    if sdk._client is not None:
        sdk._client.close()


@pytest.fixture
def component_class(tmp_path):
    source = Path(integration.__file__)
    copied = tmp_path / "sign_action.py"
    shutil.copyfile(source, copied)
    code = copied.read_text()
    assert copied.read_bytes() == source.read_bytes()
    cls = eval_custom_component_code(code)
    assert LANGFLOW_AVAILABLE and issubclass(cls, Component)
    return cls, code


def component(component_class, **inputs):
    cls, code = component_class
    instance = cls(_code=code)
    instance.set(api_key="test-only-key", action_type="api:call", **inputs)
    assert instance._outputs_map["receipt"].types == ["JSON"]
    return instance


def test_readme_copy_instructions_use_the_installed_file(tmp_path, monkeypatch):
    readme = Path(__file__).resolve().parents[1] / "README.md"
    blocks = re.findall(r"```python\n(.*?)```", readme.read_text(), re.DOTALL)
    assert len(blocks) == 1
    monkeypatch.chdir(tmp_path)
    exec(compile(blocks[0], "README.md", "exec"), {})
    copied = tmp_path / "custom_components/asqav/sign_action.py"
    assert copied.read_bytes() == Path(integration.__file__).read_bytes()
    assert (copied.parent / "__init__.py").is_file()
    assert issubclass(eval_custom_component_code(copied.read_text()), Component)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["hash-only", "full-payload"])
async def test_actual_dispatch_serializes_configured_context(
    component_class, api, monkeypatch, mode
):
    calls, _ = api
    if mode == "full-payload":
        monkeypatch.setenv("ASQAV_MODE", mode)
    context = {"customer": "private value", "_model_name": "fixture-model"}
    instance = component(component_class, agent_name="test-agent", context=json.dumps(context))
    assert calls == []
    results, _ = await instance.run()
    result = results["receipt"]
    assert isinstance(result, Data)
    assert result.data == {key: value for key, value in RESPONSE.items() if key != "signature"}
    assert len(calls) == 2
    assert calls[0][1] == {"name": "test-agent", "algorithm": "ml-dsa-65", "capabilities": []}
    body = calls[1][1]
    assert body["action_type"] == "api:call" and body["compliance_mode"] is True
    if mode == "hash-only":
        canonical = json.dumps(
            {"action_type": "api:call", "context": context}, sort_keys=True, separators=(",", ":")
        ).encode()
        assert body["hash"] == "sha256:" + hashlib.sha256(canonical).hexdigest()
        assert body["payload_size"] == len(canonical) and body["hash_algo"] == "sha256"
        assert body["metadata"] == {
            "agent_id": "agent_fixture",
            "action_type": "api:call",
            "model_name": "fixture-model",
        }
        assert "context" not in body and "private value" not in json.dumps(body)
    else:
        assert body["context"] == context and "hash" not in body


@pytest.mark.asyncio
async def test_output_cache_and_fresh_method_execution(component_class, api):
    calls, _ = api
    instance = component(component_class)
    await instance.run()
    await instance.run()
    assert len(calls) == 2
    instance.reset_all_output_values()
    await instance.run()
    assert len(calls) == 4
    assert calls[0][1]["name"] == calls[2][1]["name"] == "langflow"


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["create", "sign"])
async def test_http_refusal_is_error_data(component_class, api, stage):
    calls, settings = api
    settings.update(stage=stage, status=403)
    results, _ = await component(component_class).run()
    result = results["receipt"]
    assert isinstance(result, Data) and "Asqav Sign Action failed:" in result.data["error"]
    assert "signature_id" not in result.data
    assert len(calls) == (1 if stage == "create" else 2)


@pytest.mark.asyncio
async def test_successful_policy_deny_is_not_a_local_gate(component_class, api):
    _, settings = api
    settings["decision"] = "deny"
    results, _ = await component(component_class).run()
    assert results["receipt"].data["signature_id"] == "sig_fixture"
    assert "error" not in results["receipt"].data


@pytest.mark.asyncio
async def test_malformed_success_response_is_error_data(component_class, api):
    _, settings = api
    settings["malformed"] = True
    results, _ = await component(component_class).run()
    assert "Asqav Sign Action failed:" in results["receipt"].data["error"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "inputs,diagnostic",
    [
        ({"api_key": ""}, "API key is required"),
        ({"action_type": ""}, "Action Type"),
        ({"context": "{"}, "valid JSON"),
        ({"context": "[]"}, "JSON object"),
    ],
)
async def test_input_failures_do_not_request_signing(component_class, api, inputs, diagnostic):
    calls, _ = api
    instance = component(component_class)
    instance.set(**inputs)
    results, _ = await instance.run()
    assert diagnostic in results["receipt"].data["error"]
    assert calls == []
