# asqav-langflow

Stop a rogue agent before it acts, and prove what it tried. This Langflow custom component sends an agent action to [Asqav](https://asqav.com) for a policy decision. A permitted action returns a verifiable cryptographic receipt. A denied action is refused server-side and leaves a forensic record of the attempt, never a permissive receipt.

This package is built and maintained by the Asqav team. Asqav is the company behind the signed-receipt service the component calls. Using the component requires an Asqav API key.

## What it does

The package exposes one component, **Asqav Sign Action**. When it runs it:

1. Reads your Asqav API key from the component input.
2. Calls the Asqav Python SDK: `asqav.init(api_key=...)`, `asqav.Agent.create(name)`, `agent.sign(action_type=..., context=...)`.
3. Returns the receipt as a Langflow `Data` object so downstream components can record or display it.

The SDK is thin and HTTP-only. All ML-DSA cryptography happens server-side at asqav.com. Only the values you pass in `context` are hashed into the receipt; nothing else from the flow travels.

## Inputs

- **Asqav API Key** (secret, required): your Asqav API key (`sk_...`).
- **Agent Name** (string, optional): name for the signing agent. Defaults to `langflow`.
- **Action Type** (string, required): the action being signed, for example `api:call` or `tool:invoke`.
- **Context (JSON)** (multiline, optional): a JSON object describing the action. Accepts a JSON string or an object.

## Output

A `Data` object whose `data` dict carries the key receipt fields:

- `signature_id`
- `action_id`
- `verification_url`
- `timestamp`
- `algorithm`

If signing fails, the component does not abort the flow. It returns a `Data` object with an `error` key and sets the component status text, so the failure is visible without crashing the run.

## Install

```bash
pip install asqav-langflow
```

This installs the component and its only hard runtime dependency, the Asqav SDK (`asqav`).

Langflow itself is a heavy dependency (it pulls in a large web stack), so it is not installed automatically. The component is meant to run inside an existing Langflow install, which already provides the base class. If you want Langflow pulled in alongside the component, install the extra:

```bash
pip install "asqav-langflow[langflow]"
```

## Add the component to Langflow

Langflow discovers custom components from a directory you point it at with the `LANGFLOW_COMPONENTS_PATH` environment variable.

1. Install this package into the same environment as Langflow (see above).
2. Copy or symlink `src/asqav_langflow/sign_action.py` into your components directory, for example:

   ```bash
   mkdir -p ~/.langflow/components/asqav
   cp src/asqav_langflow/sign_action.py ~/.langflow/components/asqav/
   ```

3. Start Langflow pointing at that directory:

   ```bash
   LANGFLOW_COMPONENTS_PATH=~/.langflow/components langflow run
   ```

4. In the editor, the **Asqav Sign Action** component appears under your custom-components group. Drag it onto the canvas, paste your Asqav API key, set the action type, and connect the receipt output downstream.

You can also paste the contents of `sign_action.py` directly into Langflow's built-in custom-component code editor.

## SDK reference

The component uses the public Asqav SDK surface:

- `asqav.init(api_key=...)` to configure the client.
- `asqav.Agent.create(name)` to create the signing agent.
- `agent.sign(action_type=..., context=...)` which returns a `SignatureResponse` carrying `signature_id`, `action_id`, `verification_url`, `timestamp`, and `algorithm`.

Get your API key at asqav.com.

## Development

```bash
pip install -e ".[dev]"
python -m pytest -q   # mocks the SDK, no live calls
```

The component resolves the Langflow base class at import time and falls back to a local stub when Langflow is not installed, so the package imports and the test suite runs without a full Langflow install.

## License

MIT
