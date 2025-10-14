"""MCP server for Pappers.fr API - Minimal implementation."""

import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Load environment variables
load_dotenv()

# Configuration
PAPPERS_API_KEY = os.getenv("PAPPERS_API_KEY")
PAPPERS_BASE_URL = "https://api.pappers.fr/v2"

if not PAPPERS_API_KEY:
    raise ValueError("PAPPERS_API_KEY environment variable is required")

# Create MCP server
server = Server("pappers-mcp-server")


async def _call_pappers_api(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    """
    Call Pappers API with authentication.

    Args:
        endpoint: API endpoint (e.g., "entreprise", "recherche")
        params: Query parameters

    Returns:
        API response as JSON dict

    Raises:
        httpx.HTTPError: If API call fails
    """
    url = f"{PAPPERS_BASE_URL}/{endpoint}"
    headers = {"api-key": PAPPERS_API_KEY}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params, timeout=30.0)
        response.raise_for_status()
        return response.json()


async def _search_companies_handler(query: str, page: int = 1, per_page: int = 10) -> str:
    """Internal handler for search_companies tool."""
    params = {
        "q": query,
        "page": page,
        "par_page": min(per_page, 100),  # Max 100 per page
    }

    try:
        result = await _call_pappers_api("recherche", params)

        # Format results for readability
        total = result.get("total", 0)
        companies = result.get("resultats", [])

        formatted = {
            "total": total,
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
                for c in companies
            ],
        }

        return json.dumps(formatted, ensure_ascii=False, indent=2)

    except httpx.HTTPError as e:
        return f"Error calling Pappers API: {str(e)}"


async def _get_company_details_handler(siren: str) -> str:
    """Internal handler for get_company_details tool."""
    # Validate SIREN format (9 digits)
    if not siren.isdigit() or len(siren) != 9:
        return f"Invalid SIREN format. Must be 9 digits, got: {siren}"

    params = {"siren": siren}

    try:
        result = await _call_pappers_api("entreprise", params)

        # Extract key information for readability
        formatted = {
            "siren": result.get("siren"),
            "denomination": result.get("nom_entreprise"),
            "forme_juridique": result.get("forme_juridique"),
            "date_creation": result.get("date_creation"),
            "statut_rcs": result.get("statut_rcs"),
            "entreprise_cessee": result.get("entreprise_cessee"),
            "capital": result.get("capital"),
            "chiffre_affaires": result.get("derniers_chiffres_affaires"),
            "resultat": result.get("derniers_resultats"),
            "siege": {
                "adresse": result.get("siege", {}).get("adresse_ligne_1"),
                "complement": result.get("siege", {}).get("adresse_ligne_2"),
                "code_postal": result.get("siege", {}).get("code_postal"),
                "ville": result.get("siege", {}).get("ville"),
                "pays": result.get("siege", {}).get("pays"),
            },
            "code_naf": result.get("code_naf"),
            "libelle_code_naf": result.get("libelle_code_naf"),
            "dirigeants": [
                {
                    "nom": d.get("nom"),
                    "prenom": d.get("prenom"),
                    "qualite": d.get("qualite"),
                    "date_prise_de_poste": d.get("date_prise_de_poste"),
                }
                for d in result.get("representants", [])[:5]  # Limit to 5 for readability
            ],
            "nombre_etablissements": result.get("nombre_etablissements"),
        }

        return json.dumps(formatted, ensure_ascii=False, indent=2)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Company not found with SIREN: {siren}"
        return f"API error ({e.response.status_code}): {e.response.text}"
    except httpx.HTTPError as e:
        return f"Error calling Pappers API: {str(e)}"


# Register tools
@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_companies",
            description=(
                "Search for French companies using Pappers.fr API. "
                "Returns a JSON string with search results containing total count, "
                "page information, and an array of companies with basic info "
                "(siren, denomination, siege address, date_creation, statut)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Company name or search text (e.g., 'Google France')",
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination (default: 1)",
                        "default": 1,
                    },
                    "per_page": {
                        "type": "integer",
                        "description": "Number of results per page, max 100 (default: 10)",
                        "default": 10,
                        "maximum": 100,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_company_details",
            description=(
                "Get detailed information about a French company by SIREN. "
                "Returns a JSON string with complete company information including "
                "basic info (denomination, date_creation, forme_juridique), "
                "financial data (capital, chiffre_affaires, resultat), "
                "contact info (siege address), legal status, representatives, and establishments."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "siren": {
                        "type": "string",
                        "description": "9-digit SIREN number (e.g., '443061841' for Google France)",
                        "pattern": "^[0-9]{9}$",
                    },
                },
                "required": ["siren"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    if name == "search_companies":
        result = await _search_companies_handler(
            query=arguments["query"],
            page=arguments.get("page", 1),
            per_page=arguments.get("per_page", 10),
        )
        return [TextContent(type="text", text=result)]
    elif name == "get_company_details":
        result = await _get_company_details_handler(siren=arguments["siren"])
        return [TextContent(type="text", text=result)]
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server with stdio transport."""
    import sys
    import logging

    # Configure logging to stderr (stdio is used for MCP protocol)
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stderr,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    logger.info("Starting Pappers MCP Server")
    logger.info(f"API Key configured: {'✓' if PAPPERS_API_KEY else '✗'}")
    logger.info("Available tools:")
    logger.info("  - search_companies: Search for companies by name")
    logger.info("  - get_company_details: Get full company info by SIREN")

    # Run with stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
