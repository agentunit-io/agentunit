# AgentUnit

**Dockerize your AI capabilities.**

AgentUnit provides a standard (`agentunit.yaml`) and a CLI tool (`au`) to package any AI Agent into a self-contained, versioned, and governable business unit.

> Think of it as defining the **RPM/DEB** for AI Agents.
> Not a framework, not a runtime, but a **packaging standard**.

---

## Why AgentUnit?

Today, AI Agents are like "scripts" — hard to reuse, harder to trust.
Enterprise needs **business assets**, not experiments.

AgentUnit solves this by turning an Agent into a **Unit** that has:

- **Identity** — Who made it? What version?
- **Contract** — What does it receive? What does it return?
- **Governance** — Who is responsible? Is audit enabled?
- **Reproducibility** — Packaged as a Docker image with all dependencies

---

## Quick Start

Get a PRD Writer running in 4 steps:

```bash
# 1. Install
pip install git+https://github.com/angdem-c/agentunit.git

# 2. Scaffold a new unit
au init prd-writer

# 3. Validate and pack
cd prd-writer
au validate
au pack -t prd-writer:1.0.0

# 4. Run it
au run prd-writer:1.0.0 --serve --port 8091
```

Now you have a Docker container running a structured AI business unit.

One-shot mode is also available:

```bash
echo '{"requirement_notes": "Build a todo app"}' > input.json
au run prd-writer:1.0.0 --input input.json
```

---

## The `agentunit.yaml`

Every Unit declares what it is. No magic, just a clear contract.

```yaml
apiVersion: agentunit.io/v1alpha1
kind: AgentUnit

metadata:
  name: prd-writer
  version: "1.0.0"
  description: "Turns requirement notes into structured PRDs"

contract:
  inputs:
    type: object
    properties:
      requirement_notes:
        type: string
    required: [requirement_notes]
  outputs:
    type: object
    properties:
      prd_document:
        type: string
      quality_score:
        type: number

governance:
  require_human_approval: true
  audit_enabled: true

runtime:
  framework: "generic-python"
  entry: "app.py"
  model:
    provider: "openai"
    name: "gpt-4o"

build:
  base_image: "python:3.11-slim"
  port: 8091
  env:
    MODEL_API_KEY: ""
```

See [spec/agentunit-spec-v0.1.md](spec/agentunit-spec-v0.1.md) for the full specification.

---

## How It Works

```
agentunit.yaml  →  au validate  →  au pack  →  Docker Image
                                                       │
                                           ┌───────────┴───────────┐
                                           │  au run --serve        │
                                           │  au run --input        │
                                           └───────────────────────┘
```

1. **Define** — Write `agentunit.yaml` to declare your Unit's identity, contract, and runtime
2. **Validate** — Check the spec against JSON Schema and file references
3. **Pack** — Generate a Dockerfile and build a Docker image
4. **Run** — Execute as a one-shot task or an HTTP server

---

## Framework Adapters

AgentUnit is framework-agnostic. Built-in adapters:

| Adapter | Status |
|---------|--------|
| `generic-python` | Complete |
| `langchain` | Skeleton |

Use `au init --framework generic-python` to scaffold with a specific adapter.

Community adapters can be registered via Python entry points.

---

## Roadmap

We are building towards a world where AI capabilities are as manageable as code.

- **Phase 0** ✅ — Standard + CLI (`init`, `validate`, `pack`, `run`)
- **Phase 1** 🔄 — Spec stabilization, community adapters, discovery
- **Phase 2** — Governance & audit (accountability layer)

---

## Non-Goals

To keep this project focused, we explicitly **do not**:

- Replace LangChain, AutoGen, CrewAI, or any Agent framework
- Provide a chat UI
- Lock you into a specific cloud or model provider
- Manage Agent runtime orchestration

---

## Contributing

We are just getting started. If you believe AI should be packaged and governed like software, join us.

Issues and pull requests are welcome. Please read the [Spec](spec/agentunit-spec-v0.1.md) first.

## License

Apache 2.0
