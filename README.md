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

## ⚠️ Important

Ce serveur est conçu pour être **déployé sur alpic.ai** avec le transport `streamable-http`. Il n'est pas configuré pour une utilisation locale avec Claude Desktop (qui nécessiterait `transport="stdio"`).

Pour déployer votre propre serveur, suivez les instructions ci-dessous.

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
- FastMCP (inclus dans le package `mcp`, supporté par alpic.ai)
- Transport `streamable-http` (recommandé pour le déploiement cloud)
- Configuration via `alpic.yaml`

### 2. Pousser sur GitHub

```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

### 3. Déployer depuis l'interface alpic.ai

1. Connectez-vous sur https://alpic.ai
2. Cliquez sur "New Server" ou "Deploy"
3. Autorisez alpic.ai à accéder à votre repository GitHub
4. Sélectionnez votre repository `mcp-pappers`
5. Sélectionnez la branche `main`
6. alpic.ai détecte automatiquement `alpic.yaml` et lance le déploiement

Documentation complète: https://docs.alpic.ai/quickstart

### 4. Configurer les variables d'environnement

**Option A: Via le dashboard alpic.ai**

Dans l'interface de votre serveur déployé, ajoutez:
- `PAPPERS_API_KEY`: Votre clé API Pappers (requis)
- `MCP_API_KEY`: Clé secrète pour protéger l'accès (optionnel)

**Option B: Uploader un fichier .env**

Créez un `.env` local et uploadez-le via le dashboard alpic.ai:
```bash
PAPPERS_API_KEY=your_pappers_api_key
MCP_API_KEY=your_secret_key  # Optionnel
```

**Modes d'authentification:**
- **Mode public** (par défaut): Si `MCP_API_KEY` n'est pas défini, le serveur est accessible sans authentification.
- **Mode protégé**: Si `MCP_API_KEY` est défini, les clients doivent envoyer le header `x-api-key` avec chaque requête.

### 5. Utiliser votre serveur déployé

Une fois déployé, votre serveur sera accessible via une URL fournie par alpic.ai:
```
https://your-server-name-xxxxx.alpic.live
```

Pour tester, modifiez l'URL dans `test_client.py` (ligne 28) et exécutez:
```bash
python test_client.py
```

## Architecture

```
Client MCP (Test client, applications)
    ↓ HTTPS + SSE/Streamable-HTTP
alpic.ai (Cloud Platform)
    ↓
MCP Server (FastMCP avec streamable-http)
    ↓ REST API + Authentication
Pappers.fr API
```

**Transport:** `streamable-http` (déployé sur alpic.ai)
**Framework:** FastMCP (inclus dans le package `mcp`)
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
- **Python MCP SDK** (contient FastMCP): https://github.com/modelcontextprotocol/python-sdk
- **MCP Protocol**: https://modelcontextprotocol.io
- **alpic.ai Documentation**: https://docs.alpic.ai/
- **alpic.ai Quickstart**: https://docs.alpic.ai/quickstart
- **Tutorial complet**: Voir [TUTORIAL.md](./TUTORIAL.md)

## Licence

MIT
