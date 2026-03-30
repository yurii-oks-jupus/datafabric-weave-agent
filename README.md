# Weave — Data Fabric AI Assistant

AI-powered chatbot for HSBC's Data Fabric platform.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (FastAPI mode)
APP_ENV=local python main.py

# Run locally (A2A mode)
APP_ENV=local python main.py --a2a
```

## Project Structure

```
├── prompts/           # System prompts (Markdown files, one per agent)
├── agents/            # Agent definitions (one per agent)
├── core/              # Shared infrastructure (config, MCP, sessions, cache)
├── server/            # Server setup (FastAPI + A2A)
├── utils/             # Utilities (prompt loader, logging)
├── conf/              # Configuration (Dynaconf YAML)
├── main.py            # Entry point
└── Dockerfile         # Container build
```

## Endpoints

- `GET /datafabric-weave-agent/health` — Health check
- `POST /datafabric-weave-agent/ask` — Query the agent (FastAPI mode)
- `GET /.well-known/agent.json` — Agent Card (A2A mode)
