import os
import yaml
import logging
from typing import Tuple

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

# Import your custom configuration loader
from presidio_flask_estbert import (
    load_presidio_from_config,
    validate_config
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("presidio-flask-api")

DEFAULT_PORT = "8000"

WELCOME_MESSAGE = r"""
    _______  _______  _______  _______ _________ ______  _________ _______ 
    (  ____ )(  ____ )(  ____ \(  ____ \\__   __/(  __  \ \__   __/(  ___  )
    | (    )|| (    )|| (    \/| (    \/   ) (   | (  \  )   ) (   | (   ) |
    | (____)|| (____)|| (__    | (_____    | |   | |   ) |   | |   | |   | |
    |  _____)|     __)|  __)   (_____  )   | |   | |   | |   | |   | |   | |
    | (      | (\ (   | (            ) |   | |   | |   ) |   | |   | |   | |
    | )      | ) \ \__| (____/\/\____) |___) (___| (__/  )___) (___| (___) |
    |/       |/   \__/(_______/\_______)\_______/(______/ \_______/(_______)

    Estonian Presidio API Server
                                                              
"""

class EstonianPresidioFlaskServer:
    """Flask server for Presidio with Estonian EstBERT support"""
    
    def __init__(self, config_path: str = "/app/config/presidio-stanza-estbert.yml"):
        self.config_path = config_path
        self.app = Flask(__name__)
        
        # Enable CORS
        CORS(self.app)
        
        # Configure Flask
        self.app.config['JSON_AS_ASCII'] = False  # Support for Estonian characters
        self.app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
        
        # Initialize engines
        self._initialize_engines()
        
        # Setup routes
        self._setup_routes()
        
        # Setup error handlers
        self._setup_error_handlers()
        
        logger.info(WELCOME_MESSAGE)
    
    def _initialize_engines(self):
        """Initialize Presidio analyzer and anonymizer engines"""
        try:
            # Validate configuration
            is_valid, message = validate_config(self.config_path)
            if not is_valid:
                raise ValueError(f"Invalid configuration: {message}")
            
            # Load configuration
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            # Initialize analyzer with EstBERT + Stanza
            logger.info("Initializing Presidio Analyzer with EstBERT + Stanza...")
            self.analyzer = load_presidio_from_config(self.config_path)
            
            # Initialize anonymizer
            logger.info("Initializing Presidio Anonymizer...")
            self.anonymizer = AnonymizerEngine()
            
            logger.info("Presidio engines initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Presidio engines: {e}")
            raise
    
    def _setup_error_handlers(self):
        """Setup Flask error handlers"""
        
        @self.app.errorhandler(HTTPException)
        def handle_http_exception(error):
            logger.error(f"HTTP error: {error}")
            return jsonify(error=str(error)), error.code
        
        @self.app.errorhandler(Exception)
        def handle_generic_exception(error):
            logger.error(f"Unexpected error: {error}")
            return jsonify(error="Internal server error"), 500
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route("/", methods=["GET"])
        def health_check() -> Tuple[Response, int]:
            """Health check endpoint"""
            return jsonify({
                "status": "healthy",
                "service": "Estonian Presidio API",
                "version": "1.0.0",
                "supported_languages": self.config.get("supported_languages", ["xx"]),
                "model": "tartuNLP/EstBERT_NER + Spacy"
            }), 200
        
        @self.app.route("/analyze", methods=["POST"])
        def analyze() -> Tuple[Response, int]:
            """
            Analyze text for PII entities using EstBERT + Stanza
            
            Expected JSON payload:
            {
                "text": "Minu nimi on Jaan Tamm ja ma elan Tallinnas.",
                "language": "xx",
                "entities": ["PERSON", "LOCATION"], // optional
                "return_decision_process": false, // optional
                "correlation_id": "uuid" // optional
            }
            """
            try:
                # Parse request JSON
                if not request.is_json:
                    return jsonify(error="Request must be JSON"), 400
                
                data = request.get_json()
                
                # Validate required fields
                if "text" not in data:
                    return jsonify(error="Missing required field: text"), 400
                
                text = data["text"]
                language = data.get("language", "xx")
                entities = data.get("entities")
                return_decision_process = data.get("return_decision_process", False)
                correlation_id = data.get("correlation_id")
                
                # Use entities from request or default from config
                entities_to_detect = entities or self.config.get('entities_to_detect', ["PERSON", "LOCATION", "ORGANIZATION", "PHONE_NUMBER", "EMAIL_ADDRESS", "URL", "IP_ADDRESS", "IBAN_CODE", "DATE_TIME", "CRYPTO", "CREDIT_CARD"])
                
                # Analyze text
                analyzer_results = self.analyzer.analyze(
                    text=text,
                    entities=entities_to_detect,
                    language=language,
                    return_decision_process=return_decision_process,
                    correlation_id=correlation_id
                )
                
                # Convert results to JSON format
                results_json = []
                for result in analyzer_results:
                    result_dict = {
                        "entity_type": result.entity_type,
                        "start": result.start,
                        "end": result.end,
                        "score": str(result.score)
                    }
                    
                    # Add analysis explanation if available
                    if hasattr(result, 'analysis_explanation') and result.analysis_explanation:
                        result_dict["analysis_explanation"] = result.analysis_explanation
                    
                    # Add recognition metadata if available
                    if hasattr(result, 'recognition_metadata') and result.recognition_metadata:
                        result_dict["recognition_metadata"] = result.recognition_metadata
                    
                    results_json.append(result_dict)
                # make the results_json JSON serializable
                return jsonify({
                    "results": results_json,
                    "text": text
                }), 200
                
            except Exception as e:
                error_msg = f"Analysis failed: {str(e)}"
                logger.error(error_msg)
                return jsonify(error=error_msg), 500
        
        @self.app.route("/anonymize", methods=["POST"])
        def anonymize() -> Tuple[Response, int]:
            """
            Analyze and anonymize text using EstBERT + Stanza
            
            Expected JSON payload:
            {
                "text": "Minu nimi on Jaan Tamm ja ma elan Tallinnas.",
                "language": "et",
                "anonymizers": { // optional
                    "PERSON": {"type": "replace", "new_value": "[ISIK]"},
                    "LOCATION": {"type": "replace", "new_value": "[ASUKOHT]"}
                },
                "entities": ["PERSON", "LOCATION"] // optional
            }
            """
            try:
                # Parse request JSON
                if not request.is_json:
                    return jsonify(error="Request must be JSON"), 400
                
                data = request.get_json()
                
                # Validate required fields
                if "text" not in data:
                    return jsonify(error="Missing required field: text"), 400
                
                text = data["text"]
                language = data.get("language", "xx")
                anonymizers = data.get("anonymizers")
                entities = data.get("entities")
                
                # Use entities from request or default from config
                entities_to_detect = entities or self.config.get('entities_to_detect', [
                    "PERSON", "ORGANIZATION", "LOCATION", "DATE_TIME",
                    "EMAIL_ADDRESS", "PHONE_NUMBER", "URL", "IP_ADDRESS"
                ])
                
                # First analyze the text
                analyzer_results = self.analyzer.analyze(
                    text=text,
                    entities=entities_to_detect,
                    language=language
                )
                
                # Setup anonymization operators
                operators = {}
                if anonymizers:
                    # Use custom anonymizers from request
                    for entity_type, config in anonymizers.items():
                        operator_type = config.get("type", "replace")
                        params = {}
                        
                        if operator_type == "replace":
                            params["new_value"] = config.get("new_value", f"<{entity_type}>")
                        elif operator_type == "mask":
                            params["masking_char"] = config.get("masking_char", "*")
                            params["chars_to_mask"] = config.get("chars_to_mask", 4)
                            params["from_end"] = config.get("from_end", True)
                        elif operator_type == "redact":
                            pass  # No parameters needed for redact
                        
                        operators[entity_type] = OperatorConfig(operator_type, params)
                else:
                    # Use default Estonian anonymizers from config
                    default_anonymizers = self.config.get('anonymization_config', {}).get('default_operators', {})
                    for entity_type, replacement in default_anonymizers.items():
                        operators[entity_type] = OperatorConfig("replace", {"new_value": replacement})
                
                # Anonymize the text
                anonymized_result = self.anonymizer.anonymize(
                    text=text,
                    analyzer_results=analyzer_results,
                    operators=operators
                )
                
                # Convert items to JSON format
                items_json = []
                for item in anonymized_result.items:
                    items_json.append({
                        "start": item.start,
                        "end": item.end,
                        "entity_type": item.entity_type,
                        "text": item.text,
                        "operator": item.operator
                    })
                
                return jsonify({
                    "text": anonymized_result.text,
                    "items": items_json
                }), 200
                
            except Exception as e:
                error_msg = f"Anonymization failed: {str(e)}"
                logger.error(error_msg)
                return jsonify(error=error_msg), 500
        
        @self.app.route("/recognizers", methods=["GET"])
        def recognizers() -> Tuple[Response, int]:
            """Get list of available recognizers for a language"""
            try:
                language = request.args.get("language", "xx")
                recognizers_list = self.analyzer.get_recognizers(language)
                recognizer_names = [recognizer.name for recognizer in recognizers_list]
                
                return jsonify({
                    "recognizers": recognizer_names,
                    "language": language,
                    "count": len(recognizer_names)
                }), 200
                
            except Exception as e:
                error_msg = f"Failed to get recognizers: {str(e)}"
                logger.error(error_msg)
                return jsonify(error=error_msg), 500
        
        @self.app.route("/supportedentities", methods=["GET"])
        def supported_entities() -> Tuple[Response, int]:
            """Get list of supported entities for a language"""
            try:
                language = request.args.get("language", "xx")
                entities_list = self.analyzer.get_supported_entities(language)
                
                return jsonify({
                    "entities": entities_list,
                    "language": language,
                    "count": len(entities_list)
                }), 200
                
            except Exception as e:
                error_msg = f"Failed to get supported entities: {str(e)}"
                logger.error(error_msg)
                return jsonify(error=error_msg), 500
        
        @self.app.route("/config", methods=["GET"])
        def get_configuration() -> Tuple[Response, int]:
            """Get current API configuration (excluding sensitive data)"""
            try:
                safe_config = {
                    "supported_languages": self.config.get("supported_languages"),
                    "default_score_threshold": self.config.get("default_score_threshold"),
                    "entities_to_detect": self.config.get("entities_to_detect"),
                    "estbert_model": self.config.get("estbert_configuration", {}).get("model_name"),
                    "nlp_engine": self.config.get("nlp_configuration", {}).get("nlp_engine_name"),
                    "custom_recognizers": [
                        {
                            "name": rec.get("name"),
                            "type": rec.get("type"),
                            "supported_entity": rec.get("supported_entity")
                        }
                        for rec in self.config.get("custom_recognizers", [])
                    ]
                }
                return jsonify(safe_config), 200
                
            except Exception as e:
                error_msg = f"Failed to get configuration: {str(e)}"
                logger.error(error_msg)
                return jsonify(error=error_msg), 500

# Application factory
def create_app(config_path: str = "/app/config/presidio-stanza-estbert.yml") -> Flask:
    """Create and configure the Flask application"""
    try:
        server = EstonianPresidioFlaskServer(config_path)
        return server.app
    except Exception as e:
        logger.error(f"Failed to create application: {e}")
        raise

# For running directly
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Estonian Presidio API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", DEFAULT_PORT)), help="Port to bind to")
    parser.add_argument("--config", default="/app/config/presidio-stanza-estbert.yml", help="Configuration file path")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Create Flask app
    app = create_app(args.config)
    
    logger.info(f"Starting Estonian Presidio Flask API server on {args.host}:{args.port}")
    
    # Run Flask app
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug,
        threaded=True
    )