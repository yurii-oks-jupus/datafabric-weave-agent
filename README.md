# Weave — Data Fabric AI Assistant

AI-powered chatbot for HSBC's Data Fabric platform. Supports multiple LLM providers with provider-optimized prompt formats.

## Architecture

```mermaid
graph TB
    User([User / Client])

    subgraph Server["Server Layer"]
        FastAPI["FastAPI /ask endpoint"]
        A2A["A2A Protocol"]
        Health["GET /health"]
    end

    subgraph Core["Core Infrastructure"]
        Config["Config\n(Dynaconf)"]
        ModelFactory["Model Factory\n(Gemini / Anthropic / OpenAI / Kimi)"]
        Cache["Response Cache\n(LRU + TTL)"]
        Sessions["Session Service\n(In-Memory / PostgreSQL)"]
    end

    subgraph Agents["Agent Layer"]
        Root["Root Agent\n(Orchestrator)"]
        Knowledge["Knowledge Agent\n(Documentation)"]
        Registry["Registry Agent\n(Asset Metadata)"]
    end

    subgraph Prompts["Prompt Templates"]
        Default["default/ (Markdown)"]
        Anthropic["anthropic/ (XML)"]
        OpenAI["openai/ (Markdown #)"]
        Kimi["kimi/ (→ openai)"]
    end

    subgraph External["External Services"]
        DocsMCP["Docusaurus MCP\n(Documentation Search)"]
        RegistryMCP["Asset Registry MCP\n(PostgreSQL)"]
        LLM["LLM Provider\n(Gemini / Claude / GPT / Kimi)"]
    end

    User -->|POST /ask| FastAPI
    User -->|A2A protocol| A2A
    User -->|GET /health| Health

    FastAPI --> Cache
    Cache -->|miss| Root
    FastAPI --> Sessions

    Root -->|delegates| Knowledge
    Root -->|delegates| Registry

    Knowledge -->|MCP| DocsMCP
    Registry -->|MCP| RegistryMCP

    Root -->|LLM call| LLM
    Knowledge -->|LLM call| LLM
    Registry -->|LLM call| LLM

    ModelFactory -->|configures| Root
    ModelFactory -->|configures| Knowledge
    ModelFactory -->|configures| Registry

    Config --> ModelFactory
    Prompts --> Root
    Prompts --> Knowledge
    Prompts --> Registry
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (FastAPI mode, default: Gemini)
APP_ENV=local python main.py

# Run locally (A2A mode)
APP_ENV=local python main.py --a2a
```

## Multi-Model Support

Switch LLM providers via `conf/config.yaml`:

```yaml
llm:
  provider: gemini    # gemini | anthropic | openai | kimi
  model: gemini-2.5-flash
```

### Provider Setup

| Provider | Config `provider` | API Key Env Var | Example Model |
|----------|-------------------|-----------------|---------------|
| Google Gemini | `gemini` | (Vertex AI service account) | `gemini-2.5-flash` |
| Anthropic Claude | `anthropic` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` |
| OpenAI GPT | `openai` | `OPENAI_API_KEY` | `gpt-4o` |
| Kimi (Moonshot) | `kimi` | `MOONSHOT_API_KEY` | `moonshot-v1-128k` |

### Prompt Formats

Each provider uses an optimized prompt format:

| Provider | Format | Location |
|----------|--------|----------|
| Gemini | Markdown | `prompts/default/` |
| Anthropic | XML tags | `prompts/anthropic/` |
| OpenAI | Markdown (# headers) | `prompts/openai/` |
| Kimi | Markdown (# headers) | `prompts/kimi/` (symlinks to openai/) |

## Request Flow

```mermaid
sequenceDiagram
    participant U as User
    participant S as FastAPI Server
    participant C as Response Cache
    participant Sess as Session Service
    participant R as Root Agent
    participant Sub as Sub-Agent (Knowledge / Registry)
    participant MCP as MCP Server
    participant LLM as LLM Provider

    U->>S: POST /ask {message}
    S->>C: get_exact(message)
    alt Cache HIT
        C-->>S: cached response
        S-->>U: 200 {reply}
    else Cache MISS
        C-->>S: None
        S->>Sess: get/create session
        S->>R: run_async(message)
        R->>LLM: route query
        LLM-->>R: delegate to sub-agent
        R->>Sub: forward query
        Sub->>MCP: tool call (search/query)
        MCP-->>Sub: results
        Sub->>LLM: results + prompt
        LLM-->>Sub: formatted answer
        Sub-->>R: response
        R-->>S: final response
        S->>C: put(message, reply)
        S-->>U: 200 {reply}
    end
```

## Project Structure

```
├── prompts/             # System prompts (per-provider subdirectories)
│   ├── default/         #   Gemini / universal fallback (Markdown)
│   ├── anthropic/       #   Claude-optimized (XML)
│   ├── openai/          #   GPT-optimized (Markdown with # headers)
│   └── kimi/            #   Kimi (symlinks to openai/)
├── agents/              # Agent definitions (one per agent)
├── core/                # Shared infrastructure (config, model, MCP, sessions, cache)
├── server/              # Server setup (FastAPI + A2A)
├── utils/               # Utilities (prompt loader, logging)
├── conf/                # Configuration (Dynaconf YAML)
├── main.py              # Entry point
└── Dockerfile           # Container build
```

## Endpoints

- `GET /datafabric-weave-agent/health` — Health check (includes provider/model info)
- `POST /datafabric-weave-agent/ask` — Query the agent (FastAPI mode)
- `GET /.well-known/agent.json` — Agent Card (A2A mode)
