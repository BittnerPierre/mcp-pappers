# Building and Deploying an MCP Server on alpic.ai: A Complete Guide

## The Story: From Concept to Production

This tutorial documents our journey building **mcp-pappers**, a Model Context Protocol (MCP) server that provides access to French company data via the Pappers.fr API. We'll walk through every decision, mistake, and solution we encountered while deploying to alpic.ai.

---

## 🎯 Project Overview

**What we built:**
- An MCP server that queries French company information
- Two tools: `search_companies` and `get_company_details`
- Deployed on alpic.ai with optional API key authentication
- Accessible at: https://mcp-pappers-08aa3f2c.alpic.live/

**Tech stack:**
- Python 3.10+
- FastMCP (included in the `mcp` package - **NOT** a separate `fastmcp` package)
- Pappers.fr API
- alpic.ai cloud platform

**⚠️ CRITICAL:** Use `mcp>=1.0.0` package which includes FastMCP. Do NOT install a separate `fastmcp` package.

---

## 📋 Prerequisites

Before starting, you'll need:
- Python 3.10 or higher
- `uv` package manager (faster than pip - install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- A Pappers.fr API key (free tier available at https://www.pappers.fr/api)
- A GitHub account
- An alpic.ai account (https://alpic.ai)
- Basic understanding of Python and APIs

---

## 🚀 Step-by-Step Implementation Guide

### Phase 1: Initial Setup (The FastMCP Attempt)

**Step 1: Create Project Structure**

```bash
mkdir mcp-pappers
cd mcp-pappers
git init

# Initialize Python environment with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

**Step 2: Install Dependencies**

Create `pyproject.toml` and install packages:
```toml
[project]
name = "mcp-pappers"
version = "0.1.0"
description = "MCP server for Pappers.fr French company data API"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.27.0",
    "python-dotenv>=1.0.0",
]

[project.scripts]
mcp-pappers = "mcp_pappers.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Then install:
```bash
uv pip install -e .
```

**Step 3: Initial Server Implementation**

Create `mcp_pappers/server.py`:

```python
"""MCP server for Pappers.fr API."""

import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import Field

# Load environment variables
load_dotenv()

# Configuration
PAPPERS_API_KEY = os.getenv("PAPPERS_API_KEY")
PAPPERS_BASE_URL = "https://api.pappers.fr/v2"

if not PAPPERS_API_KEY:
    raise ValueError("PAPPERS_API_KEY environment variable is required")

# Create FastMCP server
mcp = FastMCP("Pappers MCP Server", stateless_http=True)


async def _call_pappers_api(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    """Call Pappers API with authentication."""
    url = f"{PAPPERS_BASE_URL}/{endpoint}"
    headers = {"api-key": PAPPERS_API_KEY}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params, timeout=30.0)
        response.raise_for_status()
        return response.json()


@mcp.tool(
    title="Search Companies",
    description="Search for French companies using Pappers.fr API"
)
async def search_companies(
    query: str = Field(description="Company name or search text"),
    page: int = Field(default=1, description="Page number for pagination"),
    per_page: int = Field(default=10, description="Number of results per page, max 100")
) -> str:
    """Search for French companies."""
    params = {
        "q": query,
        "page": page,
        "par_page": min(per_page, 100),
    }

    try:
        result = await _call_pappers_api("recherche", params)

        formatted = {
            "total": result.get("total", 0),
            "page": page,
            "per_page": per_page,
            "companies": [
                {
                    "siren": c.get("siren"),
                    "denomination": c.get("nom_entreprise"),
                    "siege": {
                        "adresse": c.get("siege", {}).get("adresse_ligne_1"),
                        "code_postal": c.get("siege", {}).get("code_postal"),
                        "ville": c.get("siege", {}).get("ville"),
                    },
                    "date_creation": c.get("date_creation"),
                    "statut": "actif" if not c.get("entreprise_cessee") else "cessée",
                }
                for c in result.get("resultats", [])
            ],
        }

        return json.dumps(formatted, ensure_ascii=False, indent=2)

    except httpx.HTTPError as e:
        return f"Error calling Pappers API: {str(e)}"


@mcp.tool(
    title="Get Company Details",
    description="Get detailed information about a French company by SIREN"
)
async def get_company_details(
    siren: str = Field(description="9-digit SIREN number")
) -> str:
    """Get detailed company information."""
    if not siren.isdigit() or len(siren) != 9:
        return f"Invalid SIREN format. Must be 9 digits, got: {siren}"

    params = {"siren": siren}

    try:
        result = await _call_pappers_api("entreprise", params)

        formatted = {
            "siren": result.get("siren"),
            "denomination": result.get("nom_entreprise"),
            "forme_juridique": result.get("forme_juridique"),
            "date_creation": result.get("date_creation"),
            "capital": result.get("capital"),
            "siege": {
                "adresse": result.get("siege", {}).get("adresse_ligne_1"),
                "code_postal": result.get("siege", {}).get("code_postal"),
                "ville": result.get("siege", {}).get("ville"),
            },
            "dirigeants": [
                {
                    "nom": d.get("nom"),
                    "prenom": d.get("prenom"),
                    "qualite": d.get("qualite"),
                }
                for d in result.get("representants", [])[:5]
            ],
        }

        return json.dumps(formatted, ensure_ascii=False, indent=2)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Company not found with SIREN: {siren}"
        return f"API error ({e.response.status_code}): {e.response.text}"
    except httpx.HTTPError as e:
        return f"Error calling Pappers API: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

---

### Phase 2: First Deployment Attempt - The Transport Detection Error

**⚠️ TRAP #1: Transport Detection Failure**

When we first deployed to alpic.ai, we got this error:

```
Error: No MCP transport found
```

**Root Cause:** alpic.ai's build system uses regex to detect the transport type:
```bash
grep -r "mcp.run(.*transport=['\"]\(stdio\|sse\|streamable-http\|http\)['\"]"
```

**The Problem:** We initially used the official Python MCP SDK's approach which didn't match this pattern.

**Solution:** Use FastMCP's `mcp.run(transport="streamable-http")` pattern which alpic.ai explicitly looks for.

**✅ Key Learning:** Always check alpic.ai's official Python template at:
https://github.com/alpic-ai/mcp-server-template-python

---

### Phase 3: Understanding FastMCP Transports

**⚠️ TRAP #2: Transport Confusion**

We went back and forth between different transport names:
- `"streamable-http"` ✅ Correct
- `"sse"` ✅ Also works (legacy)
- `"stdio"` ❌ Wrong for cloud deployment

**FastMCP supports exactly 3 transports:**
```python
def run(self, transport: Literal["stdio", "sse", "streamable-http"] = "stdio"):
```

**Decision Tree:**
- **Local development with Claude Desktop?** → Use `"stdio"`
- **Cloud deployment (alpic.ai)?** → Use `"streamable-http"` (recommended) or `"sse"`
- **Testing locally with HTTP?** → Use `"streamable-http"`

**✅ Final Choice:** `transport="streamable-http"` for alpic.ai deployment

---

### Phase 4: Adding Authentication

**Step 4: Implement Optional API Key Protection**

alpic.ai servers are **public by default**. To add protection, we implemented custom API key validation.

Add to `server.py` before the `mcp` initialization:

```python
# Configuration
PAPPERS_API_KEY = os.getenv("PAPPERS_API_KEY")
PAPPERS_BASE_URL = "https://api.pappers.fr/v2"
MCP_API_KEY = os.getenv("MCP_API_KEY")  # Optional: API key to protect this MCP server

if not PAPPERS_API_KEY:
    raise ValueError("PAPPERS_API_KEY environment variable is required")

# Create FastMCP server
mcp = FastMCP("Pappers MCP Server", stateless_http=True)


def _validate_api_key(ctx) -> str | None:
    """
    Validate API key from request headers.

    Returns:
        Error message if validation fails, None if valid or no key configured.
    """
    # If no MCP_API_KEY is set, allow all requests (public mode)
    if not MCP_API_KEY:
        return None

    # Check for x-api-key header
    request_headers = ctx.request_context.headers if hasattr(ctx, 'request_context') else {}
    api_key = request_headers.get("x-api-key")

    if not api_key:
        return "Authentication required: Missing x-api-key header"

    if api_key != MCP_API_KEY:
        return "Authentication failed: Invalid API key"

    return None
```

Then add validation to each tool (add `ctx=None` parameter):

```python
@mcp.tool(...)
async def search_companies(
    query: str = Field(...),
    page: int = Field(default=1, ...),
    per_page: int = Field(default=10, ...),
    ctx=None  # Add this
) -> str:
    # Validate API key if configured
    if ctx:
        error = _validate_api_key(ctx)
        if error:
            return json.dumps({"error": error}, ensure_ascii=False, indent=2)

    # ... rest of the function
```

**✅ Key Learning:**
- API key validation must be implemented in **your code**, not configured in alpic.ai
- Use the `x-api-key` header (alpic.ai's convention)
- Make it **optional** by checking if `MCP_API_KEY` is set

---

### Phase 5: Deployment Configuration

**Step 5: Create alpic.yaml**

Create `alpic.yaml` in your project root:

```yaml
# alpic.ai deployment configuration
name: mcp-pappers
version: 0.1.0

runtime:
  python: "3.13"

# Entry point
start: python -m mcp_pappers.server

# Environment variables (configure in alpic.ai dashboard)
env:
  - PAPPERS_API_KEY
  - MCP_API_KEY  # Optional: Set to enable API key authentication
  - PORT=8000

# Resources
resources:
  memory: 256Mi
  cpu: 0.5
```

**⚠️ TRAP #3: Environment Variables**

**The Problem:** We initially didn't configure `PORT` in alpic.yaml, causing issues.

**Solution:** Always include:
```yaml
env:
  - YOUR_API_KEYS
  - PORT=8000  # FastMCP uses this
```

---

### Phase 6: Deploying to alpic.ai

**Step 6: Push to GitHub**

```bash
git add .
git commit -m "Initial MCP server implementation"
git push origin main
```

**Step 7: Deploy on alpic.ai**

1. Go to https://alpic.ai dashboard
2. Click "New Server" or "Deploy"
3. Connect your GitHub repository
4. Select branch: `main`
5. Configure environment variables:
   - `PAPPERS_API_KEY`: Your Pappers.fr API key
   - `MCP_API_KEY`: (Optional) Set a secret key to enable authentication
6. Click "Deploy"

**Step 8: Monitor Deployment**

Watch the build logs. Look for:
```
✓ MCP transport: streamable-http
✓ Building Docker image
✓ Deployment successful
```

If you see `Error: No MCP transport found`, check that your `server.py` has:
```python
mcp.run(transport="streamable-http")
```

---

### Phase 7: Testing Your Deployment

**Step 9: Create Test Client**

Create `test_client.py`:

```python
"""Test client for MCP Pappers server."""

import argparse
import asyncio
import os
from contextlib import AsyncExitStack

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client

load_dotenv()


async def test_get_company_details(transport: str = "sse"):
    """Test the get_company_details tool with SIREN 443061841 (Google France)."""

    api_key = os.getenv("MCP_API_KEY")

    print("🔍 Testing MCP Pappers Server")
    print("📍 URL: https://your-server.alpic.live")
    print(f"🔌 Transport: {transport}")
    print(f"🔑 Authentication: {'Enabled' if api_key else 'Disabled'}")
    print("\n" + "="*60 + "\n")

    server_url = "https://your-server.alpic.live"
    headers = {"x-api-key": api_key} if api_key else {}

    async with AsyncExitStack() as stack:
        # Create SSE client connection
        sse_read, sse_write = await stack.enter_async_context(
            sse_client(server_url, headers=headers)
        )

        session = await stack.enter_async_context(
            ClientSession(sse_read, sse_write)
        )

        await session.initialize()
        print("✅ Connected to MCP server\n")

        # List available tools
        tools_result = await session.list_tools()
        print("📋 Available tools:")
        for tool in tools_result.tools:
            print(f"  - {tool.name}: {tool.description}")
        print()

        # Call the tool
        print("🔧 Calling get_company_details(siren='443061841')...")
        result = await session.call_tool(
            "get_company_details",
            arguments={"siren": "443061841"}
        )

        print("\n✅ Success!")
        print("\n" + "="*60)
        print("Response:")
        print("="*60 + "\n")
        for content in result.content:
            if hasattr(content, 'text'):
                print(content.text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test MCP Pappers Server")
    parser.add_argument(
        "--transport", "-t",
        choices=["sse", "streamable-http"],
        default="sse",
        help="Transport type to use (default: sse)",
    )
    args = parser.parse_args()

    asyncio.run(test_get_company_details(transport=args.transport))
```

**Step 10: Run Tests**

```bash
# Install test dependencies
uv pip install python-dotenv

# Without authentication
python test_client.py

# With authentication (set MCP_API_KEY in .env first)
echo "MCP_API_KEY=your-secret-key" >> .env
python test_client.py
```

---

## 🎬 Video Tutorial Script

### Introduction (30 seconds)
"Hi! Today we're building an MCP server that provides access to French company data and deploying it to alpic.ai. We'll cover FastMCP, authentication, and common deployment pitfalls. Let's get started!"

### Part 1: Project Setup (2 minutes)
1. Show creating the directory structure
2. Display pyproject.toml and explain dependencies
3. Highlight the FastMCP import and server initialization

### Part 2: Implementing Tools (3 minutes)
1. Show the `@mcp.tool()` decorator pattern
2. Explain Pydantic Field for parameter descriptions
3. Demonstrate calling external API (Pappers.fr)
4. Show error handling

### Part 3: The Transport Trap (2 minutes)
1. Show the initial deployment error
2. Explain alpic.ai's detection script
3. **Key Point:** Show the correct `mcp.run(transport="streamable-http")`
4. Reference alpic.ai's template repository

### Part 4: Adding Authentication (2 minutes)
1. Explain why servers are public by default
2. Show the `_validate_api_key()` function
3. Demonstrate adding `ctx` parameter to tools
4. Show setting `MCP_API_KEY` in alpic.ai dashboard

### Part 5: Deployment (3 minutes)
1. Show alpic.yaml configuration
2. Push to GitHub
3. Connect repository in alpic.ai dashboard
4. Set environment variables
5. Watch build logs
6. Celebrate success! 🎉

### Part 6: Testing (2 minutes)
1. Show test_client.py
2. Run without authentication
3. Add API key to .env
4. Run with authentication
5. Show successful company data retrieval

### Conclusion (1 minute)
"And that's it! You now have a production MCP server deployed on alpic.ai. Remember the key points:
- Use FastMCP with `stateless_http=True`
- Always use `transport="streamable-http"` for alpic.ai
- Implement custom authentication with `x-api-key` header
- Test both with and without authentication
Happy building!"

---

## 🤖 Instructions for Claude Code (or Any Coding Agent)

If you're a coding agent helping someone recreate this project, follow these instructions:

### Critical Decision Points

1. **When asked about MCP SDK:**
   - ✅ **ALWAYS** use: `mcp>=1.0.0` (this package includes FastMCP)
   - ❌ **NEVER** use: `fastmcp` as a separate package (it will conflict and fail)
   - ✅ Import: `from mcp.server.fastmcp import FastMCP`
   - ❌ Don't import: `from fastmcp import FastMCP` (wrong package)

2. **When implementing the server:**
   - ✅ Use: `from mcp.server.fastmcp import FastMCP`
   - ✅ Initialize: `mcp = FastMCP("Server Name", stateless_http=True)`
   - ✅ Tools: Use `@mcp.tool()` decorator with Pydantic Fields
   - ✅ Run: `mcp.run(transport="streamable-http")`

3. **When configuring for alpic.ai:**
   - ✅ Create alpic.yaml with `runtime.python`, `start`, `env`, and `resources`
   - ✅ Include `PORT=8000` in env variables
   - ✅ Use `python -m your_module.server` as the start command

4. **When implementing authentication:**
   - ✅ Make it optional (check if `MCP_API_KEY` is set)
   - ✅ Use `x-api-key` header (not `Authorization: Bearer`)
   - ✅ Add `ctx=None` parameter to all tools
   - ✅ Validate at the start of each tool function

5. **When creating tests:**
   - ✅ Use `mcp.client.sse import sse_client` (works with alpic.ai)
   - ✅ Load API key from `.env` with python-dotenv
   - ✅ Include headers: `{"x-api-key": api_key}` if key exists

### Common Mistakes to Avoid

1. **❌ DON'T** use `from mcp.server import Server` and manual registration
   - **✅ DO** use FastMCP with decorators

2. **❌ DON'T** use `transport="stdio"` for cloud deployment
   - **✅ DO** use `transport="streamable-http"`

3. **❌ DON'T** forget `stateless_http=True` in FastMCP initialization
   - **✅ DO** include it for cloud deployment

4. **❌ DON'T** use `Authorization: Bearer` for API keys
   - **✅ DO** use `x-api-key` header

5. **❌ DON'T** implement authentication in alpic.yaml
   - **✅ DO** implement it in your Python code

### Verification Checklist

Before telling the user deployment is ready:

- [ ] `server.py` contains `mcp.run(transport="streamable-http")`
- [ ] `alpic.yaml` exists with all required fields
- [ ] `pyproject.toml` has `mcp>=1.0.0` dependency
- [ ] Authentication validation is optional (checks if key is set)
- [ ] All tools have `ctx=None` parameter
- [ ] Test client uses `sse_client` from `mcp.client.sse`
- [ ] `.env` file is in `.gitignore`

### When User Encounters Errors

**"Error: No MCP transport found"**
→ Check: `mcp.run(transport="streamable-http")` is present

**"401 Unauthorized" or "403 Forbidden"**
→ Check: MCP_API_KEY is set in alpic.ai dashboard AND in local .env for testing

**"ModuleNotFoundError: No module named 'fastmcp'"** or **"ImportError: cannot import name 'FastMCP' from 'fastmcp'"**
→ Fix: **DO NOT install `fastmcp` package.** Uninstall it if present: `uv pip uninstall fastmcp`
→ Use only: `mcp>=1.0.0` which includes FastMCP
→ Reinstall: `uv pip install -e .`
→ Import: `from mcp.server.fastmcp import FastMCP` (note: `mcp.server.fastmcp`, not just `fastmcp`)

**Test client hangs with streamable-http transport**
→ Solution: Use SSE transport for the client (it works with both server transports)

---

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         User/Client                          │
│                  (Claude Desktop, Custom Client)             │
└────────────────────────────┬────────────────────────────────┘
                             │
                             │ HTTPS + SSE/Streamable-HTTP
                             │
┌────────────────────────────▼────────────────────────────────┐
│                        alpic.ai                              │
│                   (Cloud Platform)                           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           MCP Pappers Server                         │  │
│  │                                                      │  │
│  │  • FastMCP (stateless_http=True)                   │  │
│  │  • Transport: streamable-http                       │  │
│  │  • Optional x-api-key authentication                │  │
│  │                                                      │  │
│  │  Tools:                                             │  │
│  │  - search_companies                                 │  │
│  │  - get_company_details                              │  │
│  └──────────────────┬───────────────────────────────────┘  │
└─────────────────────┼──────────────────────────────────────┘
                      │
                      │ HTTPS + API Key
                      │
┌─────────────────────▼────────────────────────────────────────┐
│                    Pappers.fr API                             │
│              (French Company Data Provider)                   │
└───────────────────────────────────────────────────────────────┘
```

---

## 🎓 Key Learnings Summary

1. **FastMCP is the easiest way** to build MCP servers for alpic.ai
2. **Transport matters**: Use `"streamable-http"` for cloud, `"stdio"` for local
3. **Authentication is DIY**: Implement it in your code, not in config
4. **alpic.ai uses regex** to detect your transport - match their pattern
5. **SSE client works everywhere**: Use it for testing, it's compatible with both transports
6. **Environment variables are crucial**: Both `PAPPERS_API_KEY` and optional `MCP_API_KEY`
7. **stateless_http=True**: Required for cloud deployment with FastMCP

---

## 📚 Resources

- **MCP Official Docs**: https://modelcontextprotocol.io
- **FastMCP Docs**: https://gofastmcp.com
- **alpic.ai Docs**: https://docs.alpic.ai
- **alpic.ai Python Template**: https://github.com/alpic-ai/mcp-server-template-python
- **Pappers.fr API Docs**: https://www.pappers.fr/api/documentation
- **Our Repository**: https://github.com/BittnerPierre/mcp-pappers

---

## 🐛 Troubleshooting

### Build fails with "No MCP transport found"
**Solution:** Ensure `server.py` has exactly: `mcp.run(transport="streamable-http")`

### Server starts but tools don't work
**Solution:** Check that tools are decorated with `@mcp.tool()` and have proper type hints

### Authentication not working
**Solution:**
1. Verify `MCP_API_KEY` is set in alpic.ai dashboard
2. Check client sends `x-api-key` header (not `Authorization`)
3. Ensure `ctx` parameter is added to tool functions

### Test client can't connect
**Solution:** Use SSE transport: `sse_client(server_url, headers=headers)`

---

## 🎉 Conclusion

Congratulations! You've built and deployed a production-ready MCP server. You now understand:
- How FastMCP works and why it's perfect for alpic.ai
- The differences between transport types
- How to implement custom authentication
- How to avoid common deployment pitfalls

The pattern you've learned here applies to ANY MCP server you want to build - just swap out the API calls and tool logic!

---

**Built with ❤️ using Claude Code and deployed on alpic.ai**

*Last updated: 2025-01-04*
