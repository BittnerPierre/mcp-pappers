# MCP Pappers Server

Serveur MCP minimaliste pour l'API Pappers.fr (données d'entreprises françaises).

## Installation

```bash
# Installer uv si nécessaire
curl -LsSf https://astral.sh/uv/install.sh | sh

# Créer l'environnement et installer les dépendances
uv venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
uv pip install -e .
```

## Configuration

Créer un fichier `.env` avec votre clé API Pappers:

```bash
PAPPERS_API_KEY=your_api_key_here
```

Obtenir une clé API gratuite sur: https://www.pappers.fr/api

## Utilisation Locale

### Démarrer le serveur MCP (SSE)

```bash
python -m mcp_pappers.server
```

Le serveur démarre sur `http://localhost:8001` par défaut.

### Tester avec un client MCP

```python
from agents.mcp import MCPServerStreamableHttp

mcp_server = MCPServerStreamableHttp(
    name="Pappers MCP Server",
    params={
        "url": "http://localhost:8001",
    },
)

async with mcp_server as server:
    # Utiliser les outils MCP
    tools = await server.list_tools()
    print(tools)
```

## Outils MCP Disponibles

### 1. `search_company`
Rechercher une entreprise par nom ou SIREN/SIRET.

**Paramètres:**
- `query` (str): Nom de l'entreprise ou numéro SIREN/SIRET

**Exemple:**
```json
{
  "query": "Google France"
}
```

### 2. `get_company_details`
Obtenir les détails complets d'une entreprise.

**Paramètres:**
- `siren` (str): Numéro SIREN de l'entreprise (9 chiffres)

**Exemple:**
```json
{
  "siren": "443061841"
}
```

## Déploiement sur alpic.ai

### 1. Préparer le déploiement

Le serveur est déjà configuré pour alpic.ai avec:
- Port configurable via variable d'environnement `PORT`
- Host `0.0.0.0` pour accepter les connexions externes
- Transport **Streamable HTTP** (standard MCP recommandé, SSE est deprecated)

### 2. Déployer sur alpic.ai

```bash
# Se connecter à alpic.ai
alpic login

# Déployer le serveur
alpic deploy
```

### 3. Configuration des variables d'environnement

Dans le dashboard alpic.ai, configurer:
- `PAPPERS_API_KEY`: Votre clé API Pappers

### 4. Utiliser le serveur déployé

```python
from agents.mcp import MCPServerStreamableHttp

mcp_server = MCPServerStreamableHttp(
    name="Pappers MCP Server",
    params={
        "url": "https://your-app.alpic.ai",  # URL fournie par alpic
    },
)
```

## Architecture

```
Client (Agents SDK)
    ↓ Streamable HTTP
MCP Server (FastMCP)
    ↓ REST API
Pappers.fr API
```

**Transport:** Streamable HTTP (standard MCP, SSE deprecated)
**Framework:** FastMCP (simple comme FastAPI)
**API:** Pappers.fr v2

## Développement

### Lancer les tests

```bash
uv pip install -e ".[dev]"
pytest
```

### Linter

```bash
ruff check .
ruff format .
```

## Limitations

- Clé API gratuite Pappers: 500 requêtes/mois
- Serveur lecture seule (pas de modification de données)
- Données limitées aux entreprises françaises

## Ressources

- **API Pappers.fr**: https://www.pappers.fr/api/documentation
- **FastMCP**: https://github.com/jlowin/fastmcp
- **MCP Protocol**: https://modelcontextprotocol.io
- **alpic.ai**: https://docs.alpic.ai/

## Licence

MIT
