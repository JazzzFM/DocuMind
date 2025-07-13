"""
Prompt template manager for entity extraction.
Manages document-specific prompt templates and provides dynamic prompt generation.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from documents.config_loader import get_document_type, get_document_types
from documents.exceptions import DocumentClassificationError

logger = logging.getLogger(__name__)


class PromptTemplate:
    """Represents a prompt template for entity extraction."""
    
    def __init__(self, template_content: str, document_type: str):
        """
        Initialize prompt template.
        
        Args:
            template_content: Raw template content with placeholders
            document_type: Document type this template is for
        """
        self.template_content = template_content
        self.document_type = document_type
        self.placeholders = self._extract_placeholders()
    
    def _extract_placeholders(self) -> List[str]:
        """Extract placeholder names from template."""
        import re
        placeholders = re.findall(r'\{(\w+)\}', self.template_content)
        return list(set(placeholders))
    
    def render(self, **kwargs) -> str:
        """
        Render the template with provided values.
        
        Args:
            **kwargs: Values to substitute in template
            
        Returns:
            Rendered prompt string
        """
        try:
            return self.template_content.format(**kwargs)
        except KeyError as e:
            missing_key = str(e).strip("'\"")
            raise DocumentClassificationError(
                f"Missing required template parameter: {missing_key}"
            )
    
    def get_required_placeholders(self) -> List[str]:
        """Get list of required placeholder names."""
        return self.placeholders.copy()


class PromptManager:
    """
    Manages prompt templates for entity extraction across different document types.
    """
    
    def __init__(self, prompts_directory: Optional[str] = None):
        """
        Initialize prompt manager.
        
        Args:
            prompts_directory: Directory containing prompt template files
        """
        if prompts_directory is None:
            prompts_directory = os.path.join(
                Path(__file__).parent.parent.parent,
                'config',
                'prompts'
            )
        
        self.prompts_directory = prompts_directory
        self._templates: Dict[str, PromptTemplate] = {}
        self._default_template: Optional[PromptTemplate] = None
        self._load_templates()
    
    def _load_templates(self):
        """Load all prompt templates from the prompts directory."""
        try:
            prompts_path = Path(self.prompts_directory)
            
            if not prompts_path.exists():
                logger.warning(f"Prompts directory not found: {self.prompts_directory}")
                return
            
            # Load default template first
            default_path = prompts_path / "default.txt"
            if default_path.exists():
                with open(default_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    self._default_template = PromptTemplate(content, "default")
                    logger.debug("Loaded default prompt template")
            
            # Load document-specific templates
            for prompt_file in prompts_path.glob("*.txt"):
                if prompt_file.name == "default.txt":
                    continue  # Already loaded
                
                document_type = prompt_file.stem
                
                try:
                    with open(prompt_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        template = PromptTemplate(content, document_type)
                        self._templates[document_type] = template
                        logger.debug(f"Loaded prompt template for: {document_type}")
                
                except Exception as e:
                    logger.warning(f"Failed to load prompt template {prompt_file}: {e}")
            
            logger.info(f"Loaded {len(self._templates)} document-specific prompt templates")
            
        except Exception as e:
            logger.error(f"Failed to load prompt templates: {e}")
    
    def get_template(self, document_type: str) -> PromptTemplate:
        """
        Get prompt template for a specific document type.
        
        Args:
            document_type: Type of document
            
        Returns:
            PromptTemplate instance
            
        Raises:
            DocumentClassificationError: If template not found and no default available
        """
        # Try to get document-specific template
        if document_type in self._templates:
            return self._templates[document_type]
        
        # Fall back to default template
        if self._default_template:
            return self._default_template
        
        # No templates available
        raise DocumentClassificationError(
            f"No prompt template found for document type '{document_type}' and no default template available"
        )
    
    def create_extraction_prompt(self, document_text: str, document_type: str) -> str:
        """
        Create a complete extraction prompt for a document.
        
        Args:
            document_text: Text content of the document
            document_type: Type of document being processed
            
        Returns:
            Complete prompt string ready for LLM
        """
        try:
            # Get the appropriate template
            template = self.get_template(document_type)
            
            # Get document type configuration
            doc_config = get_document_type(document_type)
            
            # Prepare template variables
            template_vars = {
                'document_text': document_text,
                'document_type': document_type
            }
            
            # If using default template, we need to build entity descriptions
            if template.document_type == "default" and doc_config:
                entity_descriptions = self._build_entity_descriptions(doc_config.entities)
                template_vars['entity_descriptions'] = entity_descriptions
            
            # Render the template
            prompt = template.render(**template_vars)
            
            logger.debug(f"Created extraction prompt for {document_type} ({len(prompt)} characters)")
            
            return prompt
            
        except Exception as e:
            logger.error(f"Failed to create extraction prompt for {document_type}: {e}")
            raise DocumentClassificationError(f"Failed to create extraction prompt: {e}")
    
    def _build_entity_descriptions(self, entities: List[Dict[str, Any]]) -> str:
        """
        Build entity descriptions for default template.
        
        Args:
            entities: List of entity configurations
            
        Returns:
            Formatted entity descriptions string
        """
        descriptions = []
        
        for entity in entities:
            name = entity.get('name', 'unknown')
            entity_type = entity.get('type', 'string')
            required = "REQUIRED" if entity.get('required', False) else "OPTIONAL"
            description = entity.get('description', '')
            
            # Add type-specific guidance
            type_guidance = ""
            if entity_type == 'date':
                type_guidance = " (format: YYYY-MM-DD)"
            elif entity_type == 'amount':
                type_guidance = " (include currency symbol if present)"
            elif entity_type == 'array':
                type_guidance = " (return as array of strings)"
            
            descriptions.append(
                f"- {name} ({entity_type}, {required}): {description}{type_guidance}"
            )
        
        return "\n".join(descriptions)
    
    def validate_prompt_coverage(self) -> Dict[str, Any]:
        """
        Validate that all configured document types have prompt templates.
        
        Returns:
            Validation report dictionary
        """
        try:
            document_types = get_document_types()
            covered_types = set(self._templates.keys())
            configured_types = set(document_types.keys())
            
            missing_templates = configured_types - covered_types
            extra_templates = covered_types - configured_types
            
            report = {
                "total_configured_types": len(configured_types),
                "total_templates": len(self._templates),
                "covered_types": list(covered_types),
                "missing_templates": list(missing_templates),
                "extra_templates": list(extra_templates),
                "has_default_template": self._default_template is not None,
                "coverage_percentage": len(covered_types) / len(configured_types) * 100 if configured_types else 100
            }
            
            if missing_templates:
                logger.warning(f"Document types without prompt templates: {missing_templates}")
            
            if extra_templates:
                logger.info(f"Extra templates found (not in config): {extra_templates}")
            
            return report
            
        except Exception as e:
            logger.error(f"Failed to validate prompt coverage: {e}")
            return {"error": str(e)}
    
    def reload_templates(self):
        """Reload all templates from disk."""
        logger.info("Reloading prompt templates...")
        self._templates.clear()
        self._default_template = None
        self._load_templates()
    
    def create_custom_prompt(self, document_text: str, entities: List[Dict[str, Any]], 
                           document_type: str = "document", 
                           additional_instructions: Optional[str] = None) -> str:
        """
        Create a custom extraction prompt without using templates.
        
        Args:
            document_text: Text content of the document
            entities: List of entities to extract
            document_type: Type of document (for context)
            additional_instructions: Optional additional instructions
            
        Returns:
            Custom prompt string
        """
        entity_descriptions = self._build_entity_descriptions(entities)
        
        instructions = []
        instructions.append("1. Be precise and extract exactly what's written in the document")
        instructions.append("2. For dates, use YYYY-MM-DD format when possible")
        instructions.append("3. For amounts, include currency symbols if present")
        instructions.append("4. For arrays, return as list of strings")
        instructions.append("5. Use null for missing values (do not omit keys)")
        instructions.append("6. If you cannot find a required entity, still include it with null value")
        
        if additional_instructions:
            instructions.append(f"7. {additional_instructions}")
        
        instructions_text = "\n".join(instructions)
        
        prompt = f"""You are an expert at extracting structured information from {document_type} documents.

Extract the following entities from the document text:

{entity_descriptions}

Guidelines:
{instructions_text}

Document text:
{document_text}

Return ONLY a valid JSON object with the extracted entities:"""
        
        return prompt
    
    def get_template_info(self) -> Dict[str, Any]:
        """Get information about loaded templates."""
        return {
            "prompts_directory": self.prompts_directory,
            "total_templates": len(self._templates),
            "document_types": list(self._templates.keys()),
            "has_default_template": self._default_template is not None,
            "template_placeholders": {
                doc_type: template.get_required_placeholders()
                for doc_type, template in self._templates.items()
            }
        }


# Global prompt manager instance
_prompt_manager = None

def get_prompt_manager() -> PromptManager:
    """Get or create global prompt manager instance."""
    global _prompt_manager
    
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    
    return _prompt_manager