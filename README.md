# Estonian Presidio API

A privacy-focused Flask API server that combines Microsoft Presidio with the Estonian EstBERT NER model to detect and anonymize personally identifiable information (PII) in Estonian text.

## Features

- **Estonian NER Support**: Integrates `tartuNLP/EstBERT_NER` for Estonian named entity recognition
- **Multilingual**: Supports Estonian and other languages via spaCy
- **Custom Estonian Patterns**: Recognizes Estonian-specific entities like personal codes (isikukood), car numbers, and phone numbers
- **REST API**: Easy-to-use HTTP endpoints for text analysis and anonymization
- **Docker Support**: Ready-to-deploy containerized application
- **Configurable**: YAML-based configuration for entities, patterns, and anonymization rules

## Supported Entities

### Estonian-Specific
- **EE_PERSONAL_CODE**: Estonian personal identification codes (isikukood)
- **CAR_NUMBER**: Estonian car registration numbers
- **PHONE_NUMBER**: Estonian and international phone numbers

### General Entities (via EstBERT + Presidio)
- **PERSON**: Personal names
- **ORGANIZATION**: Company and organization names
- **LOCATION**: Addresses and locations
- **EMAIL_ADDRESS**: Email addresses
- **URL**: Website URLs
- **IP_ADDRESS**: IP addresses
- **IBAN_CODE**: Bank account numbers
- **DATE_TIME**: Dates and times
- **CRYPTO**: Cryptocurrency addresses

## Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/ckittask/et_presidio.git
cd et_presidio
```

2. Start the service:
```bash
docker-compose up --build -d
```

3. Test the API:
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Minu nimi on Jaan Tamm ja ma elan Tallinnas.",
    "language": "xx"
}'
```

### Manual Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
python -m spacy download xx_ent_wiki_sm
```

2. Run the application:
```bash
python app.py
```

## API Endpoints

### Health Check
```http
GET /
```
Returns API status and configuration information.

### Analyze Text
```http
POST /analyze
```

Detects PII entities in text without modifying the original content.

**Request Body:**
```json
{
  "text": "Minu nimi on Jaan Tamm ja ma elan Tallinnas.",
  "language": "xx",
  "entities": ["PERSON", "LOCATION"],
  "return_decision_process": false,
  "correlation_id": "optional-uuid"
}
```

**Response:**
```json
{
    "results": [
        {
            "end": 43,
            "entity_type": "LOCATION",
            "recognition_metadata": {
                "recognizer_identifier": "EstBERT_NER_Recognizer_136620996207040",
                "recognizer_name": "EstBERT_NER_Recognizer"
            },
            "score": "0.9976997",
            "start": 34
        },
        {
            "end": 22,
            "entity_type": "PERSON",
            "recognition_metadata": {
                "recognizer_identifier": "EstBERT_NER_Recognizer_136620996207040",
                "recognizer_name": "EstBERT_NER_Recognizer"
            },
            "score": "0.99680436",
            "start": 13
        },
        {
            "end": 43,
            "entity_type": "PERSON",
            "recognition_metadata": {
                "recognizer_identifier": "SpacyRecognizer_136620873524752",
                "recognizer_name": "SpacyRecognizer"
            },
            "score": "0.85",
            "start": 34
        }
    ],
    "text": "Minu nimi on Jaan Tamm ja ma elan Tallinnas."
}
```

### Anonymize Text
```http
POST /anonymize
```

Analyzes and replaces PII entities with anonymized placeholders.

**Request Body:**
```json
{
  "text": "Minu nimi on Jaan Tamm ja ma elan Tallinnas.",
  "language": "xx",
  "anonymizers": {
    "PERSON": {"type": "replace", "new_value": "[ISIK]"},
    "LOCATION": {"type": "replace", "new_value": "[ASUKOHT]"}
  },
  "entities": ["PERSON", "LOCATION"]
}
```

**Response:**
```json
{
    "items": [
        {
            "end": 40,
            "entity_type": "LOCATION",
            "operator": "replace",
            "start": 31,
            "text": "[ASUKOHT]"
        },
        {
            "end": 19,
            "entity_type": "PERSON",
            "operator": "replace",
            "start": 13,
            "text": "[ISIK]"
        }
    ],
    "text": "Minu nimi on [ISIK] ja ma elan [ASUKOHT]."
}
```

### Get Supported Entities
```http
GET /supportedentities?language=xx
```

### Get Available Recognizers
```http
GET /recognizers?language=xx
```

### Get Configuration
```http
GET /config
```

## Configuration

The API is configured via `config/presidio-stanza-estbert.yml`. Key sections include:

- **NLP Engine**: spaCy configuration with multilingual model
- **EstBERT Model**: Estonian NER model settings
- **Custom Recognizers**: Pattern-based recognizers for Estonian-specific entities
- **Anonymization Rules**: Default replacement values for different entity types

Example configuration snippet:
```yaml
estbert_configuration:
  model_name: "tartuNLP/EstBERT_NER"
  supported_language: xx

anonymization_config:
  default_operators:
    PERSON: "[ISIK]"
    LOCATION: "[ASUKOHT]"
    EE_PERSONAL_CODE: "[ISIKUKOOD]"
```

## Docker Deployment

### Environment Variables

- `FLASK_ENV`: Environment mode (production/development)
- `PORT`: Port to bind to (default: 8000)
- `HOST`: Host to bind to (default: 0.0.0.0)
- `LOG_LEVEL`: Logging level (info/debug/warning/error)

### Resource Requirements

- **Memory**: 2-4GB RAM (EstBERT model loading)
- **CPU**: 1-2 cores recommended
- **Storage**: ~2GB for models and dependencies

### Health Checks

The container includes built-in health checks that verify API availability:
- Endpoint: `GET /`
- Interval: 30 seconds
- Timeout: 10 seconds
- Retries: 5

## Examples

### Estonian Personal Code Detection
```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "Minu isikukood on 38001085718 ja auto number on 123 ABC."}'
```

### Anonymizing Estonian Text
```bash
curl -X POST http://localhost:8000/anonymize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Jaan Tamm (isikukood: 38001085718) töötab AS Eesti Firma juures Tallinnas.",
    "language": "xx"
  }'
```



### Adding Custom Recognizers

1. Edit `config/presidio-stanza-estbert.yml`
2. Add new recognizer configuration under `recognizers` section
3. Restart the application


## Dependencies

- **presidio-analyzer**: Core PII detection engine
- **presidio-anonymizer**: Text anonymization engine
- **transformers**: Hugging Face transformers for EstBERT
- **spacy**: NLP processing engine
- **flask**: Web framework
- **pyyaml**: Configuration file parsing
