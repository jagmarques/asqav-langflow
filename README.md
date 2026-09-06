# asqav-langflow

A Langflow component that requests Asqav signing for configured action data and returns selected response fields as `Data`. It runs when Langflow evaluates its **Receipt** output. It does not execute or gate another tool, or establish that the described action happened.

The component is maintained by Asqav and requires an Asqav API key. Signing takes place on the Asqav server. The component does not independently verify a returned receipt.

## Request and error behavior

After local input checks pass, the signing method initializes the SDK and requests a new agent with the configured name. It uses that agent to request a signature for the action type and context. Each signing-method call requests its own agent. Langflow can reuse a cached output, so reading the output again does not always make another request.

A successful request returns a `Data` object with `signature_id`, `action_id`, `verification_url`, `timestamp`, and `algorithm`. These are fields from the SDK response, not the complete signing envelope. A successful response's policy decision is not an admission check in this component.

Missing required inputs, invalid context, and SDK errors return `Data` with an `error` key and set the component status. Those errors do not raise from the signing method. Downstream components must inspect the result and decide how to proceed. A failed request does not guarantee a receipt or forensic record.

## Inputs and data handling

- **Asqav API Key:** required secret input for SDK authentication.
- **Agent Name:** optional signing-agent name, defaulting to `langflow`.
- **Action Type:** required action name, such as `api:call` or `tool:invoke`.
- **Context (JSON):** optional JSON text containing an object that describes the action.

With the SDK's default cloud configuration, signing uses hash-only mode: the request carries a digest, its algorithm and size, action/agent identifiers, and SDK metadata. Context entries such as `_model_name` and `_tool_name` opt into metadata forwarding. This is not a claim that only a hash leaves the process.

The component reinitializes the SDK with automatic mode selection. A valid `ASQAV_MODE` takes precedence; without it, hostnames under `*.asqav.com` select hash-only mode and other API hostnames select full-payload mode. This can replace a mode chosen by another `asqav.init()` call. An existing SDK base URL is preserved.

Set `ASQAV_MODE=hash-only` in the Langflow environment to require hashing before the signing request. `ASQAV_MODE=full-payload` sends the configured context in the request body. Other flow components and model providers handle their own traffic separately.

## Install from source

Use Python 3.10 through 3.14 in the environment running Langflow 1.12 or later within the 1.x series:

```bash
python -m pip install "git+https://github.com/jagmarques/asqav-langflow.git"
```

This installs the component and the Asqav SDK. It does not install the Langflow application. To install the application as well, request the extra from the same source:

```bash
python -m pip install "asqav-langflow[langflow] @ git+https://github.com/jagmarques/asqav-langflow.git"
```

## Add the component

Run this in a directory where you want to keep your custom components. It copies the installed component, so no repository-relative source path is needed:

```python
from importlib.util import find_spec
from pathlib import Path
from shutil import copyfile

source = Path(find_spec("asqav_langflow.sign_action").origin)
category = Path("custom_components/asqav")
category.mkdir(parents=True, exist_ok=True)
(category / "__init__.py").touch()
copyfile(source, category / "sign_action.py")
```

Start Langflow with that components directory:

```bash
LANGFLOW_COMPONENTS_PATH="$PWD/custom_components" langflow run
```

Find **Asqav Sign Action** in the custom component group, configure its inputs, and connect its **Receipt** output downstream. Keep the integration package installed: the copied file imports its helper through the `asqav_langflow` package name.

You can also paste the installed `sign_action.py` contents into Langflow's custom-component editor in that same environment. Both routes use the same signing implementation.

## Development and verification

From a checkout:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

The development extra installs `lfx` 1.12.0, the framework used for the component evaluator and output dispatcher, without the full Langflow application. Tests require real framework types and exercise SDK 0.10.10 request serialization with HTTP intercepted. No Asqav or model-provider request is made. This does not establish a complete browser/server flow or cryptographic verification.

When neither host import path loads, `_compat.py` provides small fallback classes so ordinary package imports can work without Langflow. Those classes do not reproduce host validation or dispatch and are not evidence of Langflow compatibility.

## License

[Elastic License 2.0](LICENSE).
