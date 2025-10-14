# MCP Pappers Server

Serveur MCP pour l'API Pappers.fr (données d'entreprises françaises), construit avec le Python MCP SDK officiel.

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

### Démarrer le serveur MCP

Le serveur utilise le transport stdio standard du Python MCP SDK:

```bash
python -m mcp_pappers.server
```

### Configuration Claude Desktop

Ajouter dans votre configuration Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "pappers": {
      "command": "python",
      "args": ["-m", "mcp_pappers.server"],
      "env": {
        "PAPPERS_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

## Outils MCP Disponibles

### 1. `search_companies`
Rechercher des entreprises françaises par nom.

**Paramètres:**
- `query` (str): Nom de l'entreprise (ex: "Google France")
- `page` (int, optionnel): Numéro de page pour la pagination (défaut: 1)
- `per_page` (int, optionnel): Nombre de résultats par page, max 100 (défaut: 10)

**Exemple:**
```json
{
  "query": "Google France",
  "page": 1,
  "per_page": 10
}
```

### 2. `get_company_details`
Obtenir les détails complets d'une entreprise par SIREN.

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

Le serveur est configuré pour alpic.ai avec:
- Python MCP SDK officiel (supporté par alpic.ai)
- Transport stdio (alpic.ai gère automatiquement la conversion vers HTTP/SSE)
- Configuration via `alpic.yaml`

### 2. Déployer sur alpic.ai

```bash
# Se connecter à alpic.ai
alpic login

# Déployer le serveur
alpic deploy
```

Ou utilisez l'interface web d'alpic.ai pour un déploiement en un clic depuis votre dépôt GitHub.

### 3. Configuration des variables d'environnement

Dans le dashboard alpic.ai, configurer:
- `PAPPERS_API_KEY`: Votre clé API Pappers (requis)
- `MCP_API_KEY`: Clé API pour protéger votre serveur MCP (optionnel)

**Mode public** (par défaut): Si `MCP_API_KEY` n'est pas défini, le serveur est accessible sans authentification.

**Mode protégé**: Définir `MCP_API_KEY` avec une valeur secrète (ex: `my-secret-key-123`). Les clients devront alors envoyer le header `x-api-key` avec chaque requête.

### 4. Utiliser le serveur déployé

Le serveur déployé sera accessible via l'URL fournie par alpic.ai et pourra être utilisé par n'importe quel client MCP compatible.

## Architecture

```
Client MCP (Claude Desktop, etc.)
    ↓ stdio / HTTP (géré par alpic.ai)
MCP Server (Python MCP SDK)
    ↓ REST API
Pappers.fr API
```

**Transport:** stdio (local) / HTTP (déployé sur alpic.ai)
**Framework:** Python MCP SDK officiel
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
- **Python MCP SDK**: https://github.com/modelcontextprotocol/python-sdk
- **MCP Protocol**: https://modelcontextprotocol.io
- **alpic.ai**: https://docs.alpic.ai/

## Licence

MIT
