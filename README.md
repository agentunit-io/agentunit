# AgentUnit

> The Docker for AI Agent Packaging

AgentUnit is a CLI tool + Spec that packages any AI Agent (LangChain / Dify / custom) into a standardized, versioned, governable Agent Unit.

**Status: Alpha (Phase 1 in progress)**

## Quick Start

```bash
# Install
pip install agentunit

# Initialize an Agent Unit project
au init my-agent --framework generic-python

# Validate configuration
au validate

# Pack into Docker image
au pack -t my-agent:1.0.0

# Run
au run my-agent:1.0.0 --input input.json
```

## What is an Agent Unit?

An Agent Unit is a self-contained AI capability unit with:

- **Business contract**: Clear input/output schema (not prompts)
- **Responsible human**: Who is accountable for its outputs
- **Versioned**: Reproducible across environments
- **Governable**: Audit trail, approval policies, performance metrics
- **Packaged**: Runtime + Skills + Tools + Knowledge — all in one Docker image

## Framework Support

| Framework | Status |
|-----------|--------|
| generic-python | Available |
| pm-agent | Available |
| langchain | Experimental |
| custom | Bring your own Dockerfile |

## License

Apache 2.0
