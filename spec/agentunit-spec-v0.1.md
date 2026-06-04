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
  responsible_human: string        # Optional. Run-time injected
  require_human_approval: boolean  # Default true
  max_token_per_task: int          # Optional. Token budget
  audit_enabled: boolean           # Default true

runtime:
  framework: string      # Required. Adapter name: generic-python | langchain | pm-agent | custom
  language: string       # Required. python | nodejs | go
  entry: string          # Required. Agent entry point file
  model:
    provider: string     # Required. openai | anthropic | custom
    name: string         # Required. Model identifier
  routing:
    default: string      # Optional. "auto" | "explicit" | "hybrid". Default "auto"
  components:
    skills:
      - name: string         # Required. Human-readable skill name
        id: string           # Optional. Identifier for explicit routing, defaults to name
        path: string         # Required. Relative path to skill definition
        description: string  # Optional. One-line description for routing/registry
    tools:
      - name: string     # Required
        path: string     # Required. Relative path
        type: string     # Optional. "embedded" | "external". Default "embedded"
    knowledge:
      - name: string     # Required
        path: string     # Required. Relative path
  framework_config: {}   # Optional. Framework-specific free-form config
  dependencies:
    file: string         # Required. Relative path to requirements.txt / package.json

build:
  base_image: string     # Default "python:3.11-slim"
  port: int              # Default 8091
  health_check: string   # Default "/health"
  env:                   # Optional. Env vars (injected at run time)
    KEY: ""              # Empty = must be provided at run time
```

### Key Principles

1. **Framework-agnostic**: `contract`, `governance`, and `build` are identical across all frameworks
2. **Adapter-driven**: `runtime.framework` selects the adapter; `runtime.framework_config` holds framework-specific settings as free-form JSON
3. **Self-contained**: The packed Docker image includes Runtime + Skills + Tools + Knowledge + all dependencies
4. **Governable**: Docker Labels embed the full spec, enabling zero-intrusion registration by HA-OOS

### Docker Labels

When packed, the following labels are written to the Docker image:

| Label | Value |
|-------|-------|
| `agentunit.name` | metadata.name |
| `agentunit.version` | metadata.version |
| `agentunit.description` | metadata.description |
| `agentunit.framework` | runtime.framework |
| `agentunit.spec` | Full agentunit.yaml content as JSON string |

### Skill Routing

An Agent Unit is a **capability collection** — not a single skill. It packages multiple Skills that represent different sub-capabilities of a business role. The routing system controls how callers invoke specific skills.

#### Routing Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `auto` | Framework automatically selects the best skill based on input | Conversational UX, chatbots |
| `explicit` | Caller must specify `skill_id` for every request | API/system integration, governance-critical flows |
| `hybrid` | `skill_id` is optional — explicit when provided, auto when omitted | General purpose (recommended) |

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

Response from `/run` conforms to `contract.outputs` schema.

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
