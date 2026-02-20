# Claude Code Router → Azure OpenAI Foundry Proxy

Un proxy FastAPI qui convertit les requêtes au format **Anthropic Messages API** (utilisé par Claude Code Router) vers le format **Azure OpenAI Foundry API** (2025-04-01-preview).

## Architecture

```
Claude Code Router (Anthropic Format)
    ↓
Proxy FastAPI
    ├── Convertisseur Anthropic → OpenAI
    ├── Conversion des tools (input_schema → parameters)
    ├── Conversion du streaming (SSE events → OpenAI chunks)
    └── Mapping tool_use ↔ tool_calls
    ↓
Azure OpenAI Foundry API (OpenAI Format)
```

## Installation

### 1. Cloner le dépôt

```bash
cd /Users/bilalkhaldi/gitrepos/proxy
```

### 2. Créer un environnement virtuel

```bash
python -m venv venv
source venv/bin/activate  # Sur macOS/Linux
# ou
venv\Scripts\activate  # Sur Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

Copier le fichier `.env.example` vers `.env`:

```bash
cp .env.example .env
```

Éditer `.env` avec vos credentials Azure:

```env
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_API_VERSION=2025-04-01-preview

# Mapping Claude models → Azure deployments
MODEL_MAPPING={"claude-opus-4-5-20251101":"gpt-4o","claude-sonnet-4-5-20250929":"gpt-4o-mini"}
```

**Important**: Ajustez le `MODEL_MAPPING` selon vos deployments Azure. Les clés sont les noms de modèles Claude, les valeurs sont vos noms de déploiements Azure.

## Lancer le proxy

### Mode développement (avec reload)

```bash
python main.py
```

### Mode production

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Le proxy sera accessible sur `http://localhost:8000`.

## Configuration de Claude Code Router

Pour utiliser ce proxy avec Claude Code Router, modifiez votre configuration:

### Option 1: Via la variable d'environnement

```bash
export ANTHROPIC_API_BASE_URL=http://localhost:8000
```

### Option 2: Via config.json

Si Claude Code Router utilise un fichier de configuration:

```json
{
  "providers": [
    {
      "name": "azure-proxy",
      "api_base_url": "http://localhost:8000",
      "api_key": "dummy",
      "models": ["claude-opus-4-5", "claude-sonnet-4-5"]
    }
  ]
}
```

## Tests

### Test 1: Requête simple sans streaming

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Hello! What is 2+2?"}
    ]
  }'
```

### Test 2: Avec streaming

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 1024,
    "stream": true,
    "messages": [
      {"role": "user", "content": "Count from 1 to 5"}
    ]
  }'
```

### Test 3: Avec tools (function calling)

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 1024,
    "tools": [
      {
        "name": "get_weather",
        "description": "Get the current weather for a location",
        "input_schema": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "The city name"
            }
          },
          "required": ["location"]
        }
      }
    ],
    "messages": [
      {"role": "user", "content": "What is the weather in Paris?"}
    ]
  }'
```

### Test 4: Tool result submission

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "What is the weather in Paris?"},
      {
        "role": "assistant",
        "content": [
          {
            "type": "tool_use",
            "id": "toolu_01ABC",
            "name": "get_weather",
            "input": {"location": "Paris"}
          }
        ]
      },
      {
        "role": "user",
        "content": [
          {
            "type": "tool_result",
            "tool_use_id": "toolu_01ABC",
            "content": "The weather in Paris is 22°C and sunny"
          }
        ]
      }
    ]
  }'
```

### Test 5: Health check

```bash
curl http://localhost:8000/health
```

## Structure du projet

```
/Users/bilalkhaldi/gitrepos/proxy/
├── main.py                      # FastAPI app avec endpoint /v1/messages
├── config.py                    # Configuration et variables d'environnement
├── requirements.txt             # Dépendances Python
├── .env.example                 # Exemple de configuration
├── README.md                    # Cette documentation
├── models/
│   ├── __init__.py
│   ├── anthropic.py            # Modèles Pydantic format Anthropic
│   └── openai.py               # Modèles Pydantic format OpenAI
├── converters/
│   ├── __init__.py
│   ├── request_converter.py    # Anthropic request → OpenAI request
│   ├── response_converter.py   # OpenAI response → Anthropic response
│   ├── tools_converter.py      # input_schema ↔ parameters
│   ├── messages_converter.py   # Conversion des messages + tool_use/tool_result
│   └── streaming_converter.py  # SSE OpenAI → SSE Anthropic
├── services/
│   ├── __init__.py
│   └── azure_client.py         # Client HTTP vers Azure Foundry
└── utils/
    ├── __init__.py
    └── logging.py              # Configuration du logging
```

## Différences entre les formats

### Format des tools

| Aspect | Anthropic | Azure OpenAI |
|--------|-----------|--------------|
| Structure | `{name, description, input_schema}` | `{type: "function", function: {name, description, parameters}}` |
| Schéma params | `input_schema` | `parameters` |
| Type wrapper | Non | `type: "function"` requis |

### Format des réponses avec tool calling

**Anthropic:**
```json
{
  "content": [
    {
      "type": "tool_use",
      "id": "toolu_01ABC",
      "name": "get_weather",
      "input": {"location": "Paris"}
    }
  ],
  "stop_reason": "tool_use"
}
```

**Azure OpenAI:**
```json
{
  "choices": [{
    "message": {
      "tool_calls": [
        {
          "id": "call_ABC",
          "type": "function",
          "function": {
            "name": "get_weather",
            "arguments": "{\"location\":\"Paris\"}"
          }
        }
      ]
    },
    "finish_reason": "tool_calls"
  }]
}
```

### Mapping des stop_reason

| OpenAI finish_reason | Anthropic stop_reason |
|---------------------|----------------------|
| `stop` | `end_turn` |
| `tool_calls` | `tool_use` |
| `length` | `max_tokens` |
| `content_filter` | `stop_sequence` |

## Gestion des erreurs

Le proxy convertit les erreurs Azure en format Anthropic:

```json
{
  "type": "error",
  "error": {
    "type": "invalid_request_error",
    "message": "Azure API error: ..."
  }
}
```

Types d'erreurs:
- `invalid_request_error`: Erreurs 4xx (requête invalide)
- `api_error`: Erreurs 5xx (erreur serveur)

## Debug

Pour activer le mode debug, ajoutez à votre `.env`:

```env
DEBUG=true
```

Cela affichera les requêtes et réponses complètes dans les logs.

## Limitations connues

1. **Tool descriptions**: Azure limite les descriptions à 1024 caractères
2. **Streaming tool calls**: Implémentation simplifiée pour le streaming des tool calls
3. **Content blocks multiples**: Anthropic supporte text + tool_use mixés dans un même message, Azure non
4. **ID mapping**: Les IDs sont convertis `toolu_*` ↔ `call_*`, peut causer des collisions dans de rares cas

## Références

- [Claude Code Router - GitHub](https://github.com/musistudio/claude-code-router)
- [Azure OpenAI Foundry API Reference](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/reference-preview)
- [Anthropic Messages API](https://platform.claude.com/docs/en/api/messages)
- [Anthropic Tool Use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)

## License

MIT
# proxy-anth
