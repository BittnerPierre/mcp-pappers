"""MCP server for Pappers.fr API - Minimal implementation."""

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
MCP_API_KEY = os.getenv("MCP_API_KEY")  # Optional: API key to protect this MCP server

if not PAPPERS_API_KEY:
    raise ValueError("PAPPERS_API_KEY environment variable is required")

# Create FastMCP server (alpic.ai compatible)
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


@mcp.tool(
    title="Search Companies",
    description="Search for French companies using Pappers.fr API"
)
async def search_companies(
    query: str = Field(description="Company name or search text (e.g., 'Google France')"),
    page: int = Field(default=1, description="Page number for pagination"),
    per_page: int = Field(default=10, description="Number of results per page, max 100"),
    ctx=None
) -> str:
    """Search for French companies."""
    # Validate API key if configured
    if ctx:
        error = _validate_api_key(ctx)
        if error:
            return json.dumps({"error": error}, ensure_ascii=False, indent=2)

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


@mcp.tool(
    title="Get Company Details",
    description="Get detailed information about a French company by SIREN"
)
async def get_company_details(
    siren: str = Field(description="9-digit SIREN number (e.g., '443061841' for Google France)"),
    ctx=None
) -> str:
    """Get detailed company information."""
    # Validate API key if configured
    if ctx:
        error = _validate_api_key(ctx)
        if error:
            return json.dumps({"error": error}, ensure_ascii=False, indent=2)

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


if __name__ == "__main__":
    # Run with streamable HTTP transport (alpic.ai compatible)
    mcp.run(transport="streamable-http")
