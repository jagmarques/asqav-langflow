"""Request Asqav signing for configured action data and return selected response fields.

The SDK controls context serialization. Signing failures become Data(error);
this component does not execute or gate another tool or verify the response.
"""

from __future__ import annotations

import json
from typing import Any

from asqav_langflow._compat import (
    Component,
    Data,
    MessageTextInput,
    MultilineInput,
    Output,
    SecretStrInput,
)


class AsqavSignActionComponent(Component):
    """Submit action data to Asqav and return response fields or an error."""

    display_name: str = "Asqav Sign Action"
    description: str = (
        "Request Asqav signing for the configured action and context. "
        "Returns selected response fields or error data; does not gate another tool."
    )
    documentation: str = "https://asqav.com/docs"
    icon: str = "shield-check"
    name: str = "AsqavSignAction"

    inputs = [
        SecretStrInput(
            name="api_key",
            display_name="Asqav API Key",
            info="Your Asqav API key (sk_...). Create one at asqav.com.",
            required=True,
        ),
        MessageTextInput(
            name="agent_name",
            display_name="Agent Name",
            info="Human-readable name for the signing agent.",
            value="langflow",
            required=False,
        ),
        MessageTextInput(
            name="action_type",
            display_name="Action Type",
            info='The action being signed, for example "api:call" or "tool:invoke".',
            required=True,
        ),
        MultilineInput(
            name="context",
            display_name="Context (JSON)",
            info=(
                "Optional JSON object describing the action. The SDK's mode controls "
                "whether the request carries a context hash or the full context."
            ),
            required=False,
        ),
    ]

    outputs = [
        Output(
            display_name="Receipt",
            name="receipt",
            method="build_receipt",
        ),
    ]

    def _parse_context(self) -> dict[str, Any]:
        raw = getattr(self, "context", None)
        if raw is None:
            return {}
        if isinstance(raw, dict):
            return raw
        text = str(raw).strip()
        if not text:
            return {}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                'Asqav Sign Action: "Context" must be valid JSON.'
            ) from exc
        if not isinstance(parsed, dict):
            raise ValueError(
                'Asqav Sign Action: "Context" must be a JSON object.'
            )
        return parsed

    def build_receipt(self) -> Data:
        """Initialise the SDK, create an agent, sign, return the receipt.

        Errors are surfaced as a Data payload with an ``error`` key and the
        component ``status`` text rather than propagating as an unhandled
        exception, so a failed signing does not abort the whole flow.
        """
        import asqav

        api_key = getattr(self, "api_key", None)
        if not api_key:
            return self._error("Asqav Sign Action: an API key is required.")

        action_type = getattr(self, "action_type", None)
        if not action_type:
            return self._error('Asqav Sign Action: "Action Type" is required.')

        agent_name = getattr(self, "agent_name", None) or "langflow"

        try:
            context = self._parse_context()
        except ValueError as exc:
            return self._error(str(exc))

        try:
            asqav.init(api_key=api_key)
            agent = asqav.Agent.create(agent_name)
            receipt = agent.sign(action_type=action_type, context=context)
        except Exception as exc:  # noqa: BLE001 - report, do not abort the flow
            return self._error(f"Asqav Sign Action failed: {exc}")

        payload = {
            "signature_id": getattr(receipt, "signature_id", None),
            "action_id": getattr(receipt, "action_id", None),
            "verification_url": getattr(receipt, "verification_url", None),
            "timestamp": getattr(receipt, "timestamp", None),
            "algorithm": getattr(receipt, "algorithm", None),
        }
        self.status = f"Signed: {payload['signature_id']}"
        return Data(data=payload)

    def _error(self, message: str) -> Data:
        self.status = message
        return Data(data={"error": message})
