"""MCP server for Pappers.fr API - Minimal implementation."""

import os
from typing import Any

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

# Load environment variables
load_dotenv()

# Configuration
PAPPERS_API_KEY = os.getenv("PAPPERS_API_KEY")
PAPPERS_BASE_URL = "https://api.pappers.fr/v2"

if not PAPPERS_API_KEY:
    raise ValueError("PAPPERS_API_KEY environment variable is required")

# Create FastMCP server
mcp = FastMCP(
    name="Pappers MCP Server",
    version="0.1.0",
)


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


@mcp.tool()
async def search_companies(
    query: str,
    page: int = 1,
    per_page: int = 10,
) -> str:
    """
    Search for French companies using Pappers.fr API.

    Args:
        query: Company name or search text (e.g., "Google France")
        page: Page number for pagination (default: 1)
        per_page: Number of results per page, max 100 (default: 10)

    Returns:
        JSON string with search results containing:
        - total: Total number of results
        - resultats: Array of companies with basic info (siren, denomination, siege)

    Example:
        search_companies("Google France")
        search_companies("SNCF", page=2, per_page=20)
    """
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

        import json
        return json.dumps(formatted, ensure_ascii=False, indent=2)

    except httpx.HTTPError as e:
        return f"Error calling Pappers API: {str(e)}"


@mcp.tool()
async def get_company_details(siren: str) -> str:
    """
    Get detailed information about a French company by SIREN.

    Args:
        siren: 9-digit SIREN number (e.g., "443061841" for Google France)

    Returns:
        JSON string with complete company information including:
        - Basic info: denomination, date_creation, forme_juridique
        - Financial: capital, chiffre_affaires, resultat
        - Contact: siege (address), telephone, email
        - Legal: statut_rcs, entreprise_cessee
        - Representatives: dirigeants
        - Establishments: etablissements

    Example:
        get_company_details("443061841")  # Google France
    """
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

        import json
        return json.dumps(formatted, ensure_ascii=False, indent=2)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Company not found with SIREN: {siren}"
        return f"API error ({e.response.status_code}): {e.response.text}"
    except httpx.HTTPError as e:
        return f"Error calling Pappers API: {str(e)}"


def main():
    """Run the MCP server with streamable HTTP transport."""
    # Get port from environment or use default
    port = int(os.getenv("PORT", "8001"))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"Starting Pappers MCP Server on {host}:{port}")
    print(f"API Key configured: {'✓' if PAPPERS_API_KEY else '✗'}")
    print("\nAvailable tools:")
    print("  - search_companies: Search for companies by name")
    print("  - get_company_details: Get full company info by SIREN")
    print("\nPress Ctrl+C to stop")

    # Run with streamable HTTP transport (recommended, SSE is deprecated)
    mcp.run(transport="streamable-http", host=host, port=port)


if __name__ == "__main__":
    main()
