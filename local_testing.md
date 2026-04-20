# Weave Agent — Local Testing Setup

## Prerequisites

- Virtual environment already set up (`.venv`)
- Dependencies installed from `requirements.txt`
- Service account key file placed in project root
- `APP_ENV` set to `local`

---

## Step 1: Verify MCP Inspector Connection

Open PowerShell and run:

```powershell
set NODE_TLS_REJECT_UNAUTHORIZED=0
npx --registry=https://gbmt-nexus.prd.fx.gbm.cloud.uk.hsbc/repository/npmjs-group @modelcontextprotocol/inspector
```

MCP Inspector will open in the browser at `localhost:6274`.

Configure the connection:
- **Transport Type:** `Streamable HTTP`
- **URL:** `<DEPLOYED_ASSET_REGISTRY_MCP_URL>`
- **Connection Type:** `Via Proxy`

Click **Connect**. Verify status shows `● Connected` and the following tools are listed:
- `query_database`
- `get_asset_with_attributes`
- `search_assets`

Copy the exact URL from the URL field — it will be needed in the next step.

---

## Step 2: Update Config File

Open `src/conf/config.yaml`.

Locate **line 32** under the `asset_registry_mcp` section:

```yaml
asset_registry_mcp:
  transport: streamable-http
  url: http://127.0.0.1:8083/datafabric-asset-registry-mcp    # ← line 32
  headers:
    Authorization: ""
```

Replace the `url` value with the deployed MCP URL copied from MCP Inspector.

Save the file.

---

## Step 3: Restart Agent

If the agent is currently running, stop it with `Ctrl+C` in the server terminal.

Restart:

```powershell
cd src
python main.py
```

Wait for the startup logs to complete. Expected output should end with:

```
INFO:     Uvicorn running on http://127.0.0.1:8080 (Press CTRL+C to quit)
```

---

## Step 4: Verify Health Check

In a second PowerShell tab:

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8080/datafabric-weave-agent/health"
```

Expected response:

```json
{
  "status": "ok",
  "llm_provider": "gemini",
  "llm_model": "gemini-2.5-flash",
  "cache_stats": { ... }
}
```

---

## Step 5: Test Registry Queries

Send a test query:

```powershell
$body = '{"message": "Show me assets in the ESG domain"}'
Invoke-RestMethod -Uri "http://127.0.0.1:8080/datafabric-weave-agent/ask" -Method Post -Body $body -ContentType "application/json"
```

Additional test queries:

```powershell
$body = '{"message": "How many strategic data assets are there?"}'
Invoke-RestMethod -Uri "http://127.0.0.1:8080/datafabric-weave-agent/ask" -Method Post -Body $body -ContentType "application/json"
```

```powershell
$body = '{"message": "List GDA type assets"}'
Invoke-RestMethod -Uri "http://127.0.0.1:8080/datafabric-weave-agent/ask" -Method Post -Body $body -ContentType "application/json"
```

---

## Troubleshooting

### Agent fails to start

Check the server terminal output for the specific error.

**If error mentions credentials file not found:**
- Verify the service account key file is present in the project root
- Update the `google_application_credentials` path in `config.yaml` to match the local file location
- Use double backslashes on Windows: `C:\\Users\\<user>\\path\\to\\key.json`

**If error mentions MCP connection failure:**
- Re-verify the URL in MCP Inspector
- Confirm the URL in `config.yaml` matches exactly
- Check for typos, missing `https://`, or incorrect path

### Query returns 500 Internal Server Error

Check the server terminal for the traceback.

**If error mentions `no healthy upstream`:**
- The MCP server deployment is down
- Verify via MCP Inspector
- Wait for infrastructure team to restore service

**If error mentions `Failed to create MCP session`:**
- Network connectivity issue to the MCP endpoint
- Try setting proxy variables:
  ```powershell
  $env:HTTP_PROXY = "<CORPORATE_PROXY>"
  $env:HTTPS_PROXY = "<CORPORATE_PROXY>"
  $env:NO_PROXY = ".hsbc,127.0.0.1,localhost"
  ```

### Knowledge agent errors on startup

If Docusaurus MCP is down, the knowledge agent will fail to initialize.

**Temporary workaround** — edit `src/agents/root.py` and remove the knowledge agent from the tools list:

```python
tools=[
    AgentTool(registry_agent),
    # AgentTool(knowledge_agent),  # disabled — MCP down
],
```

Revert this change once the Docusaurus MCP is restored.

---

## Notes

- The `APP_ENV` environment variable must be set to `local` for the agent to load local configuration
- AMToken-based authentication is not used in this configuration — the agent uses a service account key for Vertex AI access
- Restart the server after any config changes
- Knowledge queries will fail until Docusaurus MCP is restored — only registry queries will work end-to-end
