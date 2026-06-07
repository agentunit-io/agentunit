# Why AgentUnit Exists

**AgentUnit is a specification and a CLI tool to package AI capabilities into versioned, governable business units.**

Not a framework. Not a runtime. Think of it as defining the `rpm` or `deb` for AI Agents.

---

## 1. The Problem: Agents Work, But They Don't Ship

We've gotten very good at building Agents that can write PRDs, review code, or summarize meetings.

But in the enterprise, "it works" is not the finish line. It's the starting line.

Right now, an AI Agent is usually:
- **A Script** — Hard to reuse, impossible to audit.
- **A Black Box** — You can talk to it, but you can't hold anyone responsible for its output.
- **A Pet** — When it breaks, you ssh in and nurse it back to health.

Enterprises don't need smarter pets. They need **reliable business assets**.

---

## 2. The Solution: Packaging Intelligence

AgentUnit solves this by turning an Agent into a **Unit** — a self-contained Docker image with a declarative spec.

### Get Started in 4 Steps

```bash
# 1. Install
pip install git+https://github.com/agentunit-io/agentunit.git

# 2. Scaffold a new unit
au init prd-writer

# 3. Validate and pack
cd prd-writer
au validate
au pack -t prd-writer:1.0.0

# 4. Run it
au run prd-writer:1.0.0 --serve --port 8091
```

That's it. No magic. No hidden state. Just a standard way to build, ship, and run AI capabilities.

One-shot mode is also available:

```bash
echo '{"prompt": "Build a todo app"}' > input.json
au run prd-writer:1.0.0 --input input.json
```

---

## 3. The Design: Contracts, Not Chats

The core idea is simple: **Structure over Hype.**

### The Contract

Every Unit declares its interface. Not prompts, but typed inputs and outputs.

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
```

This forces clarity. The contract is validated at `au validate` and enforced at `au run`.

### The Adapter Pattern

Whether you use LangChain, AutoGen, or raw Python scripts, AgentUnit wraps it with an adapter. The framework is an implementation detail; the Unit is the product.

Built-in adapters:
- `generic-python` — Complete. Works with any Python code.
- `langchain` — Skeleton. Community contributions welcome.

### Model Agnostic

A Unit declares *which* model it uses, but never hardcodes credentials. API keys are injected at runtime via environment variables:

```bash
export MODEL_API_KEY=your-key
export MODEL_BASE_URL=https://api.openai.com/v1
au run prd-writer:1.0.0 --serve
```

This means the same Unit works with OpenAI, DeepSeek, or any OpenAI-compatible provider — no code changes needed.

---

## 4. The Spec: One File, Full Picture

An `agentunit.yaml` captures everything about a Unit:

| Section | What it declares |
|---------|-----------------|
| `metadata` | Name, version, author, license, tags |
| `contract` | Typed inputs and outputs |
| `governance` | Human approval required? Audit enabled? |
| `protocol` | Request-response or streaming? |
| `runtime` | Framework, entry point, model config, skills/tools/knowledge |
| `resources` | CPU, memory, GPU, timeout, concurrency |
| `observability` | Quality metrics, latency baselines |
| `build` | Base image, port, environment variables |

See the [full specification](../spec/agentunit-spec-v0.1.md) for details.

---

## 5. The Vision

Packaging is just Phase 0.

Once we have standardized Units, the real work begins:

- **Phase 1** — Spec stabilization, community adapters, discovery. Make it easy for anyone to create and share Units.
- **Phase 2** — Governance and audit. Accountability layers for enterprise adoption.
- **Phase 3** — Assembly lines. Compose Units into pipelines with human approval gates.

The end state isn't one Agent. It's a production line where **humans own the "why", and machines own the "how"**.

---

## 6. The End State: AI-Native Companies

For decades, we perfected *shipping software*. We defined packages, versions, dependencies, and audit logs. We turned code into reliable business assets.

Yet with AI, we went backward. Prompts, manual clicks, and black boxes.

**AgentUnit brings software engineering discipline back to AI.** An AI capability should be shipped exactly like a software package — versioned, tested, and governed.

The future belongs to companies that don't just *use* AI — but are *run on* AI. Not companies with a chatbot on their website, but companies whose core business processes run on AI Units — versioned, auditable, and replaceable. Where:

- **AI Units own the "how"** — They execute tasks, follow contracts, and produce measurable outputs.
- **Humans own the "why"** — They set direction, own risk, and operate the decision gates.

The goal isn't smarter pets. It's reliable factories.

---

## 7. Non-Goals

To stay focused, we explicitly **do not**:
- Replace LangChain, AutoGen, CrewAI, or any Agent framework
- Provide a chat UI
- Lock you into a specific cloud or model provider
- Manage Agent runtime orchestration

---

## 8. Join Us

AgentUnit is open source. The spec is ready, the CLI works, and the first Units are running.

We're looking for people who are tired of "prompt engineering" and ready for **AI engineering**.

**Star us**: https://github.com/agentunit-io/agentunit
