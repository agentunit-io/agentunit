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
  components:
    skills:
      - name: string     # Required
        path: string     # Required. Relative path
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

### Runtime HTTP Interface

All Agent Units expose a standard HTTP interface:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/run` | POST | Execute the agent. Body = contract.inputs schema |
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
