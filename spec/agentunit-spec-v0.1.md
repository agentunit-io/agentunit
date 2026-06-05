# Agent Unit Spec v0.1

## Overview

Agent Unit Spec defines a framework-agnostic standard for packaging AI Agents into self-contained, versioned, governable business capability units.

An Agent Unit is to AI Agents what a Docker Image is to applications.

## File: `agentunit.yaml`

Every Agent Unit project contains a single `agentunit.yaml` at its root.

### Structure

```yaml
apiVersion: agentunit.io/v1alpha1
kind: AgentUnit

metadata:
  name: string           # Required. kebab-case identifier
  version: string        # Required. SemVer (e.g. "1.0.0")
  description: string    # Required. One-line business description
  author: string         # Optional. Author or org name
  license: string        # Optional. Default "Apache-2.0"
  tags: [string]         # Optional. Searchable tags
  domain: [string]       # Optional. Business domain (e.g. "product-management")

contract:
  inputs:                # Required. JSON Schema for input
    type: object
    properties: {...}
    required: [...]
  outputs:               # Required. JSON Schema for output
    type: object
    properties: {...}

governance:
  require_human_approval: boolean  # Default true
  max_token_per_task: int          # Optional. Token budget (omit = no limit)
  audit_enabled: boolean           # Default true

protocol:
  mode: string            # "request-response" | "streaming" | "both". Default "request-response"
  streaming_type: string  # "sse" | "none" | "websocket". Default "none"
  compatible_with: [string]   # Optional. Known protocol names (e.g. "openai-chat-completions")
  supports_function_calling: boolean  # Default false

runtime:
  framework: string      # Required. Adapter name: generic-python | langchain | pm-agent | custom. Default "generic-python"
  language: string       # Required. python | nodejs | go. Default "python"
  entry: string          # Required. Agent entry point (file path or module path, framework-dependent). Default "app.py"
  model:
    provider: string     # Optional. Design-time model provider. Default "openai"
    name: string         # Optional. Design-time model name. Default "gpt-4o"
  routing:
    default: string      # Optional. "auto" | "explicit" | "hybrid". Default "hybrid"
  components:
    skills:
      - name: string         # Required. Human-readable skill name
        id: string           # Optional. Identifier for explicit routing, defaults to name
        path: string         # Required. Relative path to skill definition
        description: string  # Optional. One-line description for routing/registry
        contract:            # Optional. Per-skill contract override (inherits Unit-level if omitted)
          inputs: { ... }
          outputs: { ... }
    tools:
      - name: string     # Required
        path: string     # Required. Relative path
        description: string  # Optional. One-line description
        type: string     # Optional. "embedded" | "external". Default "embedded"
    knowledge:
      - name: string     # Required
        path: string     # Required. Relative path
        description: string  # Optional. One-line description
  framework_config: {}   # Optional. Framework-specific free-form config
  dependencies:
    file: string         # Optional. Default "requirements.txt". Relative path to dependency file

resources:
  cpu: string            # Default "1". K8s-style (e.g. "1", "500m")
  memory: string         # Default "512Mi". K8s-style (e.g. "512Mi", "1Gi")
  gpu: boolean           # Default false
  timeout_seconds: int   # Default 300. Max execution time per request
  concurrency: int       # Default 10. Max concurrent requests

services:
  outbound_network: boolean   # Default true. Whether the Unit needs outbound internet access
  domains: [string]           # Optional. Domains that need to be accessible

observability:
  metrics_endpoint: string    # Optional. Prometheus-compatible endpoint path. Empty = not exposed
  evaluation_indicators:      # Optional. Output fields that are quality signals
    - field: string           # Required. Property name in contract.outputs
      description: string     # Optional
      range: [number, number] # Optional. Expected [min, max]
      higher_is_better: boolean  # Default true
  baselines:                  # Optional. Design-time performance expectations
    latency_p95_ms: int       # Optional. Expected P95 latency in ms
    success_rate: number      # Optional. Expected success rate (0-1)

build:
  base_image: string     # Default "python:3.11-slim"
  port: int              # Default 8091
  health_check: string   # Default "/health"
  env:                   # Optional. Env vars injected at runtime
    KEY: ""              # Empty string = must be provided at runtime
```

### Key Principles

1. **Framework-agnostic**: `contract`, `governance`, `protocol`, `resources`, `services`, and `build` are identical across all frameworks
2. **Adapter-driven**: `runtime.framework` selects the adapter; `runtime.framework_config` holds framework-specific settings as free-form JSON
3. **Self-contained**: The packed Docker image includes Runtime + Skills + Tools + Knowledge + all dependencies
4. **Governable**: Docker Labels embed the full spec, enabling zero-intrusion registration by HA-OOS
5. **Declarative**: All sections declare facts about the Unit as-is — what it supports, what it needs — not prescriptions for what it should do

### Docker Labels

When packed, the following labels are written to the Docker image:

| Label | Value |
|-------|-------|
| `agentunit.name` | metadata.name |
| `agentunit.version` | metadata.version |
| `agentunit.description` | metadata.description |
| `agentunit.framework` | runtime.framework |
| `agentunit.spec` | Full agentunit.yaml content as JSON string |

### Model Declaration

`runtime.model` declares the **design-time model** — the model the Unit creator used during development and testing. Its semantics:

- `provider` + `name` describe the model this Unit was **validated against**, not a runtime hard constraint
- At runtime, the actual model endpoint is controlled by `build.env` (`MODEL_BASE_URL`, `MODEL_API_KEY`), which can point to any compatible service — cloud API, enterprise private deployment (vLLM, TGI, Ollama), or local model
- Deployers should choose a model with **equivalent or superior capability** to the declared design-time model to ensure expected behavior
- The declaration serves as a **capability baseline** for cost estimation, compliance review, and model selection guidance

Example — a Unit designed with GPT-4o can be deployed with any OpenAI-compatible endpoint:

```yaml
runtime:
  model:
    provider: "openai"
    name: "gpt-4o"          # Design-time: "tested with GPT-4o"

build:
  env:
    MODEL_BASE_URL: ""      # Runtime: can be http://internal-vllm:8000/v1
    MODEL_API_KEY: ""       # Runtime: can be empty for local models
```

### Protocol

The `protocol` section declares the Unit's calling interface — how external callers interact with it over HTTP. This is determined by the Agent code inside the Unit; the spec merely exposes this fact.

- `mode`: Whether the Unit returns a single response, streams output, or supports both
- `streaming_type`: Transport protocol for streaming (`sse`, `websocket`)
- `compatible_with`: Known protocol names this Unit is compatible with (e.g. `openai-chat-completions`). Enables zero-config integration when callers use compatible SDKs
- `supports_function_calling`: Whether the Unit can act as a tool provider (accepting function/tool call requests in the protocol sense)

### Resources

The `resources` section declares compute requirements for deployment. Orchestrators and K8s schedulers use this for capacity planning and pod placement.

- `cpu` / `memory`: K8s-style resource strings
- `gpu`: Whether GPU acceleration is required
- `timeout_seconds`: Expected maximum execution time per request — callers and orchestrators use this to set timeouts
- `concurrency`: Maximum concurrent requests the Unit can handle

### Services

The `services` section declares external service dependencies. Enterprise deployment requires this for firewall configuration and network policy.

- `outbound_network`: Whether the Unit makes outbound HTTP calls (most LLM-based Units need this)
- `domains`: Specific domains that need to be accessible. Enables fine-grained network policy (whitelist)

### Skill Routing

An Agent Unit is a **capability collection** — not a single skill. It packages multiple Skills that represent different sub-capabilities of a business role. The routing system controls how callers invoke specific skills.

#### Routing Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `auto` | Framework automatically selects the best skill based on input | Conversational UX, chatbots |
| `explicit` | Caller must specify `skill_id` for every request | API/system integration, governance-critical flows |
| `hybrid` | `skill_id` is optional — explicit when provided, auto when omitted | General purpose (recommended) |

#### Skill-Level Contract

Each skill may optionally declare its own `contract` (inputs/outputs). When omitted, the skill inherits the Unit-level `contract`. This enables multi-skill Units where different skills accept different input shapes:

```yaml
skills:
  - name: prd_writer
    contract:
      inputs:
        type: object
        properties:
          requirement_notes: { type: string }
      outputs:
        type: object
        properties:
          prd_document: { type: string }
  - name: prd_reviewer
    contract:
      inputs:
        type: object
        properties:
          prd_document: { type: string }
      outputs:
        type: object
        properties:
          quality_score: { type: number }
```

#### Skill Identification

Each skill in `runtime.components.skills` may declare:
- `id`: An identifier (kebab-case or snake_case) used for explicit routing (defaults to `name` if omitted)
- `description`: A one-line description used by the routing engine and HA-OOS registry

#### `/run` Endpoint with Routing

The `/run` endpoint accepts an optional `skill_id` field:

```json
POST /run
{
  "skill_id": "prd_writer",     // Optional. Explicit skill selection
  "requirement_notes": "..."    // Per contract.inputs
}
```

When `skill_id` is provided, the Unit MUST route to the specified skill. When omitted, the routing mode determines behavior:
- `auto` / `hybrid`: Framework selects the best-matching skill
- `explicit`: Returns an error if `skill_id` is missing

#### Governance Implications

Skill-level routing enables:
- **Audit granularity**: Track which skill handled each request
- **Performance evaluation**: Measure per-skill quality scores and latency
- **Access control**: Restrict certain skills to authorized callers (future)

### Runtime HTTP Interface

All Agent Units expose a standard HTTP interface:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/run` | POST | Execute the agent. Body may include `skill_id` + contract.inputs |
| `/health` | GET | Health check |
| `/spec` | GET | Return agentunit.yaml as JSON |

Response from `/run` uses a two-part envelope:

```json
{
  "output": { ... },
  "telemetry": {
    "skill_id": "prd_writer",
    "token_usage": { "input": 500, "output": 2000 },
    "model_used": "gpt-4o-2024-08-06",
    "latency_ms": 3200
  }
}
```

- `output`: conforms to `contract.outputs` schema — the business result
- `telemetry`: standard observability data for HA-OOS to collect (all fields optional)

### Telemetry

The `telemetry` part of the `/run` response carries system-level observability data that only the Unit can know internally:

| Field | Type | Description |
|-------|------|-------------|
| `skill_id` | string | The skill that handled this request |
| `token_usage.input` | int | Input tokens consumed |
| `token_usage.output` | int | Output tokens generated |
| `model_used` | string | Actual model identifier (may differ from design-time declaration) |
| `latency_ms` | int | Internal processing time (excluding network transfer) |

All telemetry fields are optional. Simple Agents may omit `telemetry` entirely — HA-OOS will still collect Layer 1 metrics (latency, success rate) from the HTTP layer.

### Observability

The `observability` section declares what HA-OOS should measure and what baselines to expect. It addresses two needs:

**Evaluation indicators** — mark which `contract.outputs` fields are quality signals. HA-OOS extracts these from the `output` part of the response for quality tracking:

```yaml
observability:
  evaluation_indicators:
    - field: "quality_score"
      description: "Self-evaluated output quality"
      range: [0, 1]
      higher_is_better: true
```

**Performance baselines** — declare design-time expectations that HA-OOS compares against actual measurements:

```yaml
observability:
  baselines:
    latency_p95_ms: 5000       # 95% of requests should complete in <5s
    success_rate: 0.95          # 95% of requests should succeed
```

Note the difference from `resources.timeout_seconds` (deployment hard limit) — baselines are quality expectations, not kill thresholds.

### Environment Variables

The `build.env` section declares environment variables needed at runtime. The convention is:

- **Empty string (`""`)**: Must be provided at runtime (e.g. API keys, secrets)
- **Non-empty string**: Default value that can be overridden

Example:
```yaml
build:
  env:
    MODEL_API_KEY: ""                 # Required — must inject at runtime
    MODEL_BASE_URL: "https://api.openai.com/v1"  # Has default, optional override
```

## Validation Rules

1. `metadata.name` must be kebab-case (lowercase, hyphens, no spaces)
2. `metadata.version` must be valid SemVer
3. `contract.inputs` and `contract.outputs` must be valid JSON Schema
4. All `components.*.path` must reference existing files (relative to agentunit.yaml)
5. `runtime.entry` must reference an existing file
6. `runtime.dependencies.file` must reference an existing file
7. `runtime.framework` must match a registered adapter name
8. `runtime.routing.default` must be one of: `auto`, `explicit`, `hybrid`
9. Each `components.skills[].id` must be unique within the Unit
10. When `routing.default` is `explicit`, `/run` requests without `skill_id` must be rejected
11. `protocol.mode` must be one of: `request-response`, `streaming`, `both`
12. `protocol.streaming_type` must be one of: `sse`, `none`, `websocket`
13. When `protocol.mode` is `request-response`, `streaming_type` should be `none`
