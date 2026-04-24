# Weave Agent — Architecture Overview

Conversational AI assistant for HSBC's Data Fabric platform. A root agent
delegates to two specialist sub-agents (Knowledge, Registry) via Google ADK
and serves over either a FastAPI HTTP endpoint or the A2A protocol.

## Tech stack

| Layer            | Choice                                                 |
|------------------|--------------------------------------------------------|
| Agent framework  | `google-adk[a2a]` + `google-genai`                     |
| LLM providers    | Gemini (default), Anthropic, OpenAI, Kimi via LiteLLM  |
| Server           | FastAPI / Uvicorn (dev) **or** A2A protocol (prod)     |
| Config           | Dynaconf with `APP_ENV` switcher, YAML in `conf/`      |
| Tools            | MCP via `streamable-http` to Asset Registry + Docusaurus|
| Container        | `python:3.13` base, deployed to GCP Cloud Run          |

## Directory layout (current `main` branch — pre-`src/` move)

```
main.py                     Entry point; flips between FastAPI and A2A
agents/
  root.py                   Root LlmAgent; wraps Knowledge + Registry as AgentTools
  knowledge.py              Knowledge sub-agent (Docusaurus MCP)
  registry.py               Registry sub-agent (Asset Registry MCP / PostgreSQL)
  descriptions.py           Agent description constants
core/
  config.py                 Dynaconf settings + configure_environment()
  model.py                  Provider/model factory (Gemini | Anthropic | OpenAI | Kimi)
  mcp.py                    get_mcp_connection() — MCP toolset wiring
  session.py                In-memory or Postgres session service
  cache.py                  LRU + TTL response cache
server/
  app.py                    create_app() (FastAPI) + _create_a2a_app() (A2A)
  agent_card.py             A2A AgentCard
prompts/
  default/  *.md            Markdown prompts (Gemini)
  anthropic/ *.xml          XML prompts (Claude)
  openai/   *.md            Markdown-with-#-headers prompts (GPT)
  kimi/                     (delegates to openai/)
utils/
  prompts.py                load_prompt(name, provider) — prompt resolver
  logging_config.py         setup_logging()
conf/config.yaml            Dynaconf config (local + dev profiles)
Dockerfile                  Build for Cloud Run
Jenkinsfile                 HSBC shared-pipeline build/deploy
```

> Note: branch `FAB-1417` reorganises everything under `src/` with the same
> internal layout. This overview documents the `main` layout currently in use.

## Entry points

```bash
# Dev (FastAPI /ask endpoint)
APP_ENV=local python main.py

# Production (A2A protocol)
APP_ENV=dev python main.py --a2a
```

`APP_ENV` selects the `local:` or `dev:` block in `conf/config.yaml`.

## Request flow (FastAPI mode)

1. `POST /ask` → `server/app.py:create_app()` → ADK `Runner`
2. `Runner` invokes `agents.root.root_agent` (LlmAgent)
3. Root selects `AgentTool(knowledge_agent)` or `AgentTool(registry_agent)`
4. Sub-agent calls its MCP toolset (`core/mcp.py`) over `streamable-http`
5. LLM provider returns; `ResponseCache` (LRU 500, TTL 24 h) memoises identical prompts

## Configuration model

`conf/config.yaml` — two profiles (`local`, `dev`) selected by `APP_ENV`.

Key keys: `app.{host,port,path}`, `llm.{provider,model,temperature}`,
`vertexai.{project,location,google_application_credentials}`,
`proxy.{cloud_proxy,no_proxy}`,
`asset_registry_mcp.url`, `knowledge_registry_mcp.url`,
optional `session_db_url` (commented out — defaults to in-memory).

## External dependencies (runtime)

- Vertex AI / Gemini API (or Anthropic/OpenAI/Kimi via LiteLLM)
- Asset Registry MCP (HTTP, on-prem)
- Docusaurus MCP (HTTP, on-prem)
- (Optional) PostgreSQL for `DatabaseSessionService`
- HSBC corporate proxy + truststore (`hsbc-truststore.pem`, `fabric_dev_crt.pem`)

## Refactor candidates (for the upcoming pass)

- `agents/__init__.py` re-exports `root_agent` at import time → eager
  initialisation of MCP connections; `server/app.py:17` then imports
  `from agents import root_agent`. Splitting init from import would help tests.
- Provider switching (`core/model.py`) uses string keys; promoting to an Enum
  would surface typos at config-load.
- `prompts/` resolution in `utils/prompts.py` falls back across providers —
  worth documenting the precedence order in code, not just README.
- A2A vs FastAPI mode is decided by `--a2a` arg parsing in `main.py`. Could be
  driven by `settings.app.mode` for parity with `APP_ENV` switching.
