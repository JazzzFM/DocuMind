"""Configuration loader for document types and system settings."""

import os
import yaml
from typing import Dict, List, Any, Optional
from pathlib import Path
from documents.exceptions import DocumentClassificationError


class DocumentTypeConfig:
    """Configuration for a single document type."""
    
    def __init__(self, name: str, description: str, keywords: List[str], 
                 entities: List[Dict[str, Any]], confidence_threshold: float = 0.7):
        self.name = name
        self.description = description
        self.keywords = [kw.lower() for kw in keywords]  # Normalize to lowercase
        self.entities = entities
        self.confidence_threshold = confidence_threshold
        
    def get_required_entities(self) -> List[str]:
        """Get list of required entity names."""
        return [entity['name'] for entity in self.entities if entity.get('required', False)]
    
    def get_optional_entities(self) -> List[str]:
        """Get list of optional entity names."""
        return [entity['name'] for entity in self.entities if not entity.get('required', False)]
    
    def get_entity_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get entity configuration by name."""
        for entity in self.entities:
            if entity['name'] == name:
                return entity
        return None


class ConfigLoader:
    """Loads and validates document type configurations."""
    
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.path.join(
                Path(__file__).parent.parent, 
                'config', 
                'document_types.yaml'
            )
        self.config_path = config_path
        self._document_types: Optional[Dict[str, DocumentTypeConfig]] = None
        
    def load_config(self) -> Dict[str, DocumentTypeConfig]:
        """Load document type configurations from YAML file."""
        if self._document_types is not None:
            return self._document_types
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
                
            self._document_types = {}
            
            for doc_type_key, config in config_data.items():
                # Validate required fields
                self._validate_document_type_config(doc_type_key, config)
                
                # Create DocumentTypeConfig object
                self._document_types[doc_type_key] = DocumentTypeConfig(
                    name=config['name'],
                    description=config['description'],
                    keywords=config['keywords'],
                    entities=config['entities'],
                    confidence_threshold=config.get('confidence_threshold', 0.7)
                )
                
            return self._document_types
            
        except FileNotFoundError:
            raise DocumentClassificationError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise DocumentClassificationError(f"Error parsing YAML configuration: {e}")
        except Exception as e:
            raise DocumentClassificationError(f"Error loading configuration: {e}")
    
    def _validate_document_type_config(self, doc_type_key: str, config: Dict[str, Any]):
        """Validate a single document type configuration."""
        required_fields = ['name', 'description', 'keywords', 'entities']
        
        for field in required_fields:
            if field not in config:
                raise DocumentClassificationError(
                    f"Missing required field '{field}' in document type '{doc_type_key}'"
                )
        
        # Validate keywords
        if not isinstance(config['keywords'], list) or not config['keywords']:
            raise DocumentClassificationError(
                f"Keywords must be a non-empty list for document type '{doc_type_key}'"
            )
        
        # Validate entities
        if not isinstance(config['entities'], list):
            raise DocumentClassificationError(
                f"Entities must be a list for document type '{doc_type_key}'"
            )
            
        for i, entity in enumerate(config['entities']):
            self._validate_entity_config(doc_type_key, i, entity)
    
    def _validate_entity_config(self, doc_type_key: str, entity_index: int, entity: Dict[str, Any]):
        """Validate a single entity configuration."""
        required_fields = ['name', 'type', 'description']
        
        for field in required_fields:
            if field not in entity:
                raise DocumentClassificationError(
                    f"Missing required field '{field}' in entity {entity_index} "
                    f"for document type '{doc_type_key}'"
                )
        
        # Validate entity type
        valid_types = ['string', 'date', 'amount', 'number', 'array', 'boolean']
        if entity['type'] not in valid_types:
            raise DocumentClassificationError(
                f"Invalid entity type '{entity['type']}' in entity {entity_index} "
                f"for document type '{doc_type_key}'. Valid types: {valid_types}"
            )
    
    def get_document_types(self) -> Dict[str, DocumentTypeConfig]:
        """Get all document type configurations."""
        return self.load_config()
    
    def get_document_type(self, doc_type_key: str) -> Optional[DocumentTypeConfig]:
        """Get configuration for a specific document type."""
        document_types = self.load_config()
        return document_types.get(doc_type_key)
    
    def get_all_keywords(self) -> Dict[str, List[str]]:
        """Get all keywords mapped to document types."""
        document_types = self.load_config()
        return {doc_type: config.keywords for doc_type, config in document_types.items()}
    
    def get_document_type_by_name(self, name: str) -> Optional[str]:
        """Get document type key by name."""
        document_types = self.load_config()
        for doc_type_key, config in document_types.items():
            if config.name.lower() == name.lower():
                return doc_type_key
        return None
    
    def reload_config(self):
        """Force reload of configuration from file."""
        self._document_types = None
        return self.load_config()


# Global instance for easy access
_config_loader = ConfigLoader()

def get_config_loader() -> ConfigLoader:
    """Get the global configuration loader instance."""
    return _config_loader

def get_document_types() -> Dict[str, DocumentTypeConfig]:
    """Get all document type configurations (convenience function)."""
    return _config_loader.get_document_types()

def get_document_type(doc_type_key: str) -> Optional[DocumentTypeConfig]:
    """Get configuration for a specific document type (convenience function)."""
    return _config_loader.get_document_type(doc_type_key)