# Weave — Data Fabric AI Assistant

AI-powered chatbot for HSBC's Data Fabric platform. Supports multiple LLM
providers with provider-optimized prompt formats, and a **persona switch**
(FAB-2101) that adds a SQL-backed Analytics specialist alongside the existing
Knowledge + Registry agents.

## Architecture

```mermaid
graph TB
    User([User / Client])

    subgraph Server["Server Layer"]
        FastAPI["FastAPI /ask endpoint<br/>persona: weave-base · weave-analytics"]
        A2A["A2A Protocol"]
        Health["GET /health"]
    end

    subgraph Core["Core Infrastructure"]
        Config["Config<br/>(Dynaconf)"]
        ModelFactory["Model Factory<br/>(Gemini / Anthropic / OpenAI / Kimi)"]
        Cache["Response Cache<br/>session-scoped · LRU + TTL"]
        Sessions["Session Service<br/>(In-Memory / PostgreSQL)"]
        DB["DB Layer<br/>(SQLAlchemy + pg8000)"]
    end

    subgraph Agents["Agent Layer"]
        RootBase["Root · weave-base"]
        RootAnalytics["Root · weave-analytics"]
        Knowledge["Knowledge Agent<br/>(Documentation)"]
        Registry["Registry Agent<br/>(Asset Metadata)"]
        subgraph Analytics["Analytics persona (FAB-2101)"]
            AnalyticsWrapper["Analytics Wrapper"]
            Schema["schema_agent"]
            Stats["stats_agent"]
            Segment["segment_agent"]
            Fraud["fraud_agent"]
        end
    end

    subgraph Prompts["Prompt Templates"]
        Default["default/ (Markdown)"]
        Anthropic["anthropic/ (XML)"]
        OpenAI["openai/ (Markdown #)"]
        Kimi["kimi/ (→ openai)"]
    end

    subgraph External["External Services"]
        DocsMCP["Docusaurus MCP<br/>(Documentation Search)"]
        RegistryMCP["Asset Registry MCP<br/>(PostgreSQL)"]
        TxnDB["Postgres<br/>transactions table"]
        LLM["LLM Provider<br/>(Gemini / Claude / GPT / Kimi)"]
    end

    User -->|POST /ask| FastAPI
    User -->|A2A protocol| A2A
    User -->|GET /health| Health

    FastAPI --> Cache
    Cache -->|miss| RootBase
    Cache -->|miss| RootAnalytics
    FastAPI --> Sessions

    RootBase -->|delegates| Knowledge
    RootBase -->|delegates| Registry
    RootAnalytics -->|delegates| Knowledge
    RootAnalytics -->|delegates| Registry
    RootAnalytics -->|delegates| AnalyticsWrapper

    AnalyticsWrapper -->|AgentTool| Schema
    AnalyticsWrapper -->|AgentTool| Stats
    AnalyticsWrapper -->|AgentTool| Segment
    AnalyticsWrapper -->|AgentTool| Fraud

    Knowledge -->|MCP| DocsMCP
    Registry -->|MCP| RegistryMCP
    Schema -->|FunctionTool| DB
    Stats -->|FunctionTool| DB
    Segment -->|FunctionTool| DB
    Fraud -->|FunctionTool| DB
    DB -->|SELECT only| TxnDB

    RootBase -->|LLM call| LLM
    RootAnalytics -->|LLM call| LLM
    Knowledge -->|LLM call| LLM
    Registry -->|LLM call| LLM
    AnalyticsWrapper -->|LLM call| LLM

    ModelFactory -->|configures| RootBase
    ModelFactory -->|configures| RootAnalytics
    ModelFactory -->|configures| Knowledge
    ModelFactory -->|configures| Registry
    ModelFactory -->|configures| Analytics

    Config --> ModelFactory
    Prompts --> RootBase
    Prompts --> RootAnalytics
    Prompts --> Knowledge
    Prompts --> Registry
    Prompts --> Analytics
```

### Persona Switch

- `weave-base` (default) — Knowledge + Registry only. Same behaviour as FAB-1417.
- `weave-analytics` — adds an Analytics wrapper that routes SQL EDA over a
  `transactions` Postgres table to four specialists: schema discovery,
  descriptive statistics, segmentation, fraud/anomaly detection.

Same `/ask` endpoint serves both (D8 — no new ports or processes). The
persona-analytics Runner is built **lazily** on first request, so
`weave-base`-only startups pay zero analytics cost.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (FastAPI mode, default: Gemini)
cd src
APP_ENV=local python main.py

# Run locally (A2A mode)
APP_ENV=local python main.py --a2a
```

### Using the analytics persona

```bash
# weave-base (default) — Knowledge + Registry
curl -X POST http://127.0.0.1:8080/datafabric-weave-agent/ask \
  -H 'Content-Type: application/json' \
  -d '{"message": "What datasets are available?"}'

# weave-analytics — adds SQL EDA over the transactions table
curl -X POST http://127.0.0.1:8080/datafabric-weave-agent/ask \
  -H 'Content-Type: application/json' \
  -d '{"message": "Show transaction count by region", "persona": "weave-analytics", "session_id": "s1"}'
```

Analytics requires the DB password at runtime (never committed — D14):

```bash
export APP_VECTOR_STORES__DB_IAM_PASS="<password>"
```

**Full end-to-end validation walkthrough**, including the 6-test smoke suite
and expected log output, lives in
[`docs/FAB-2101_VALIDATION.md`](docs/FAB-2101_VALIDATION.md).

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

Cache key is `(session_id, sha256(normalised_message))` — same question in
different sessions never collides (D9). `detects_format_override` in the
user message marks the turn as `format=freeform` instead of the default
`structured` (D10). `tool_calls` and `total_ms` appear in a single log line
per request for latency tracking.

```mermaid
sequenceDiagram
    participant U as User
    participant S as server/app.py
    participant C as core/cache.py
    participant Sess as Session Service
    participant R as Root Agent (persona-aware)
    participant Sub as Sub-Agent<br/>Knowledge · Registry · Analytics
    participant Ext as MCP / SQL tools
    participant LLM as LLM Provider

    U->>S: POST /ask {message, session_id, persona}
    S->>S: detects_format_override(message)
    S->>C: get_exact(message, session_id)
    alt Cache HIT
        C-->>S: cached reply
        S-->>U: 200 {cache="hit", format, reply}
    else Cache MISS
        C-->>S: None
        S->>S: _get_runner(persona)  // lazy-build per persona
        S->>Sess: get/create session
        S->>R: run_async(message)
        R->>LLM: route by persona
        LLM-->>R: pick sub-agent
        R->>Sub: AgentTool call  (tool_calls += 1)
        Sub->>Ext: MCP call or SQL function call
        Ext-->>Sub: results
        Sub->>LLM: results + prompt
        LLM-->>Sub: formatted answer
        Sub-->>R: response
        R-->>S: final response
        S->>C: put(message, reply, session_id)
        S->>S: log req=... persona=... cache=miss tool_calls=N total_ms=M format=...
        S-->>U: 200 {cache="miss", format, reply}
    end
```

## Project Structure

```
src/
├── prompts/                     # System prompts (per-provider subdirectories)
│   ├── default/                 #   Gemini / universal fallback (Markdown)
│   ├── anthropic/               #   Claude-optimized (XML)
│   ├── openai/                  #   GPT-optimized (Markdown with # headers)
│   └── kimi/                    #   Kimi (symlinks to openai/)
├── agents/
│   ├── knowledge.py             # Knowledge sub-agent factory
│   ├── registry.py              # Registry sub-agent factory
│   ├── root.py                  # build_root_agent(persona) — persona-aware
│   ├── descriptions.py          # short agent descriptions
│   └── analytics/               # FAB-2101 — weave-analytics persona only
│       ├── factory.py           #   create_analytics_agent()
│       ├── schema.py            #   schema_agent
│       ├── stats.py             #   stats_agent
│       ├── segment.py           #   segment_agent
│       └── fraud.py             #   fraud_agent
├── core/
│   ├── config.py                # Dynaconf wrapper + configure_environment()
│   ├── model.py                 # get_model(), get_provider(), LiteLLM bridge
│   ├── mcp.py                   # MCP connection factory (streamable-http / SSE)
│   ├── cache.py                 # session-scoped ResponseCache (D9)
│   ├── session.py               # InMemory / DatabaseSessionService factory
│   ├── db.py                    # FAB-2101 — SQLAlchemy engine + SQL guards
│   ├── tools.py                 # FAB-2101 — 12 SQL tool functions
│   ├── schemas.py               # FAB-2101 — Pydantic output schemas per agent
│   └── format_override.py       # FAB-2101 — "as a table" detector
├── server/                      # FastAPI + A2A + agent card
├── utils/                       # logging + prompt loader
├── conf/config.yaml             # Dynaconf (local, dev profiles)
└── main.py                      # Entry point
```

## Endpoints

- `GET /datafabric-weave-agent/health` — status, active persona, cache stats
- `POST /datafabric-weave-agent/ask` — query the agent. Body:
  `{message, session_id?, user_id?, persona?}`. Response:
  `{session_id, user_id, reply, cache: hit|miss, format: structured|freeform}`.
- `GET /.well-known/agent.json` — A2A Agent Card (advertises both personas)
