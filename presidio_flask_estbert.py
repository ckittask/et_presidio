import yaml
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpArtifacts, NlpEngineProvider
from presidio_analyzer.entity_recognizer import EntityRecognizer
from typing import List


class EstBERTRecognizer(EntityRecognizer):
    """
    Custom recognizer for tartuNLP/EstBERT_NER model
    Maps Estonian labels to Presidio entities
    """
    
    # Map Estonian entities to Presidio-compatible entities
    ENTITIES = [
        "PERSON",           # Nimi -> PERSON
        "ORGANIZATION",     # Asutus -> ORGANIZATION  
        "LOCATION"         # Aadress, GPE -> LOCATION
    ]
    
    def __init__(self, model_name: str = "tartuNLP/EstBERT_NER"):
        super().__init__(
            supported_entities=self.ENTITIES,
            supported_language="xx",  # Estonian
            name="EstBERT_NER_Recognizer"
        )
        
        # Load the EstBERT model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, max_length=512)
        self.model = AutoModelForTokenClassification.from_pretrained(model_name)
        
        # Create pipeline
        self.nlp_pipeline = pipeline(
            "ner",
            model=self.model,
            tokenizer=self.tokenizer,
            aggregation_strategy="simple"
        )
        
        # Label mapping from EstBERT Estonian model to Presidio entities
        self.label_mapping = {
            "PER": "PERSON",
            "ORG": "ORGANIZATION",
            "LOC": "LOCATION",
        }

    def analyze(self, text: str, entities: List[str], nlp_artifacts: NlpArtifacts = None) -> List[RecognizerResult]:
        """
        Analyze text using EstBERT NER model
        """
        results = []
        
        try:
            # Get NER predictions from EstBERT
            ner_results = self.nlp_pipeline(text)
            
            for entity in ner_results:
                # Extract entity type (remove B- or I- prefix if present)
                entity_type = entity['entity_group'].replace('B-', '').replace('I-', '')
                
                # Map Estonian labels to Presidio entity types
                presidio_entity = self.label_mapping.get(entity_type, entity_type)
                
                if presidio_entity and presidio_entity in entities:
                    # Create RecognizerResult
                    result = RecognizerResult(
                        entity_type=presidio_entity,
                        start=entity['start'],
                        end=entity['end'],
                        score=entity['score']
                    )
                    results.append(result)
                    
        except Exception as e:
            print(f"Error in EstBERT analysis: {e}")
            
        return results


def load_presidio_from_config(config_path: str):
    """
    Load complete Presidio analyzer from YAML configuration file
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Create Stanza NLP engine from configuration
    nlp_provider = NlpEngineProvider(
        nlp_configuration=config['nlp_configuration']
    )
    nlp_engine = nlp_provider.create_engine()
    
    # Create analyzer with NLP engine
    analyzer = AnalyzerEngine(
        nlp_engine=nlp_engine,
        supported_languages=config['supported_languages'],
        default_score_threshold=config.get('default_score_threshold', 0.5)
    )
    
    # Add EstBERT recognizer
    estbert_recognizer = EstBERTRecognizer(
        model_name=config['estbert_configuration']['model_name']
    )
    analyzer.registry.add_recognizer(estbert_recognizer)
    analyzer.registry.add_recognizers_from_yaml(config_path)

    
    return analyzer


def validate_config(config_path: str) -> tuple:
    """
    Validate Presidio configuration file
    """
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Check required sections
        required_sections = [
            'supported_languages',
            'nlp_configuration', 
            'estbert_configuration'
        ]
        
        for section in required_sections:
            if section not in config:
                return False, f"Missing required section: {section}"
        
        return True, "Configuration is valid"
        
    except Exception as e:
        return False, f"Configuration error: {str(e)}"

