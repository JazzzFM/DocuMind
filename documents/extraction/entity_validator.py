import re
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from dateutil import parser as date_parser
from dataclasses import dataclass
from documents.config_loader import get_document_type
from documents.exceptions import DocumentClassificationError

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of entity validation."""
    value: Any
    is_valid: bool
    error_message: Optional[str] = None
    original_value: Any = None
    validation_applied: Optional[str] = None


@dataclass
class ValidationRule:
    """Represents a validation rule for an entity."""
    entity_name: str
    entity_type: str
    required: bool
    description: str
    pattern: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None


class EntityValidator:
    """
    Advanced entity validator with comprehensive validation and normalization capabilities.
    Handles type-specific validation, format normalization, and error reporting.
    """

    def __init__(self):
        """Initialize the entity validator."""
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "type_specific_stats": {}
        }
        
        # Precompiled regex patterns for common formats
        self.patterns = {
            "email": re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
            "phone": re.compile(r'^[\+]?[1-9][\d\-\(\)\s]{6,20}$'),
            "invoice_number": re.compile(r'^[A-Z0-9\-#]{3,50}$', re.IGNORECASE),
            "currency": re.compile(r'^[\$€£¥]?[\d,]+\.?\d*$'),
            "percentage": re.compile(r'^\d+\.?\d*%?$'),
            "alphanumeric": re.compile(r'^[a-zA-Z0-9\s\-_]+$'),
        }

    def validate_entities(self, extracted_entities: Dict[str, Any], 
                         document_type: str) -> Dict[str, ValidationResult]:
        """
        Validate all entities for a document type.
        
        Args:
            extracted_entities: Dictionary of extracted entities
            document_type: Type of document being validated
            
        Returns:
            Dictionary mapping entity names to ValidationResult objects
        """
        try:
            # Get document type configuration
            doc_config = get_document_type(document_type)
            if not doc_config:
                raise DocumentClassificationError(f"Unknown document type: {document_type}")
            
            # Create validation rules from configuration
            validation_rules = self._create_validation_rules(doc_config.entities)
            
            # Validate each entity
            validation_results = {}
            
            for rule in validation_rules:
                entity_name = rule.entity_name
                raw_value = extracted_entities.get(entity_name)
                
                # Validate the entity
                result = self._validate_single_entity(raw_value, rule)
                validation_results[entity_name] = result
                
                # Update statistics
                self._update_validation_stats(rule.entity_type, result.is_valid)
            
            # Check for required entities
            self._check_required_entities(validation_rules, validation_results)
            
            logger.debug(f"Validated {len(validation_results)} entities for {document_type}")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Entity validation failed for {document_type}: {e}")
            raise DocumentClassificationError(f"Entity validation failed: {e}")

    def _create_validation_rules(self, entities_config: List[Dict[str, Any]]) -> List[ValidationRule]:
        """Create validation rules from entity configuration."""
        rules = []
        
        for entity_config in entities_config:
            rule = ValidationRule(
                entity_name=entity_config['name'],
                entity_type=entity_config['type'],
                required=entity_config.get('required', False),
                description=entity_config.get('description', ''),
                pattern=entity_config.get('pattern'),
                min_length=entity_config.get('min_length'),
                max_length=entity_config.get('max_length'),
                min_value=entity_config.get('min_value'),
                max_value=entity_config.get('max_value')
            )
            rules.append(rule)
        
        return rules

    def _validate_single_entity(self, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate a single entity according to its rule."""
        original_value = value
        
        # Handle null/empty values
        if value is None or (isinstance(value, str) and not value.strip()):
            if rule.required:
                return ValidationResult(
                    value=None,
                    is_valid=False,
                    error_message=f"Required entity '{rule.entity_name}' is missing",
                    original_value=original_value
                )
            else:
                return ValidationResult(
                    value=None,
                    is_valid=True,
                    original_value=original_value
                )
        
        # Validate based on entity type
        try:
            if rule.entity_type == 'string':
                return self._validate_string(value, rule)
            elif rule.entity_type == 'date':
                return self._validate_date(value, rule)
            elif rule.entity_type == 'amount':
                return self._validate_amount(value, rule)
            elif rule.entity_type == 'number':
                return self._validate_number(value, rule)
            elif rule.entity_type == 'array':
                return self._validate_array(value, rule)
            elif rule.entity_type == 'boolean':
                return self._validate_boolean(value, rule)
            else:
                # Unknown type, treat as string
                return self._validate_string(value, rule)
                
        except Exception as e:
            logger.warning(f"Validation error for {rule.entity_name}: {e}")
            return ValidationResult(
                value=original_value,
                is_valid=False,
                error_message=f"Validation error: {str(e)}",
                original_value=original_value
            )

    def _validate_string(self, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate string entities."""
        try:
            # Convert to string
            str_value = str(value).strip()
            
            # Check length constraints
            if rule.min_length and len(str_value) < rule.min_length:
                return ValidationResult(
                    value=str_value,
                    is_valid=False,
                    error_message=f"String too short (min: {rule.min_length})",
                    original_value=value
                )
            
            if rule.max_length and len(str_value) > rule.max_length:
                return ValidationResult(
                    value=str_value[:rule.max_length],
                    is_valid=True,
                    error_message=f"String truncated to {rule.max_length} characters",
                    original_value=value,
                    validation_applied="truncation"
                )
            
            # Check pattern if specified
            if rule.pattern:
                pattern = re.compile(rule.pattern)
                if not pattern.match(str_value):
                    return ValidationResult(
                        value=str_value,
                        is_valid=False,
                        error_message=f"String doesn't match required pattern",
                        original_value=value
                    )
            
            # Additional validation based on entity name patterns
            validation_applied = None
            if 'email' in rule.entity_name.lower():
                if not self.patterns['email'].match(str_value):
                    return ValidationResult(
                        value=str_value,
                        is_valid=False,
                        error_message="Invalid email format",
                        original_value=value
                    )
            
            # Clean and normalize
            cleaned_value = self._clean_string(str_value)
            if cleaned_value != str_value:
                validation_applied = "cleaning"
            
            return ValidationResult(
                value=cleaned_value,
                is_valid=True,
                original_value=value,
                validation_applied=validation_applied
            )
            
        except Exception as e:
            return ValidationResult(
                value=value,
                is_valid=False,
                error_message=f"String validation failed: {str(e)}",
                original_value=value
            )

    def _validate_date(self, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate and normalize date entities."""
        try:
            if isinstance(value, date):
                return ValidationResult(
                    value=value.strftime('%Y-%m-%d'),
                    is_valid=True,
                    original_value=value,
                    validation_applied="format_normalization"
                )
            
            # Try to parse string date
            date_str = str(value).strip()
            
            # Common date patterns to try
            date_patterns = [
                '%Y-%m-%d',       # 2024-01-15
                '%m/%d/%Y',       # 01/15/2024
                '%d/%m/%Y',       # 15/01/2024
                '%Y/%m/%d',       # 2024/01/15
                '%m-%d-%Y',       # 01-15-2024
                '%d-%m-%Y',       # 15-01-2024
                '%B %d, %Y',      # January 15, 2024
                '%b %d, %Y',      # Jan 15, 2024
                '%d %B %Y',       # 15 January 2024
                '%d %b %Y',       # 15 Jan 2024
            ]
            
            # Try exact patterns first
            for pattern in date_patterns:
                try:
                    parsed_date = datetime.strptime(date_str, pattern).date()
                    return ValidationResult(
                        value=parsed_date.strftime('%Y-%m-%d'),
                        is_valid=True,
                        original_value=value,
                        validation_applied="format_normalization"
                    )
                except ValueError:
                    continue
            
            # Try dateutil parser as fallback
            try:
                parsed_date = date_parser.parse(date_str).date()
                return ValidationResult(
                    value=parsed_date.strftime('%Y-%m-%d'),
                    is_valid=True,
                    original_value=value,
                    validation_applied="format_normalization"
                )
            except (ValueError, TypeError):
                pass
            
            return ValidationResult(
                value=date_str,
                is_valid=False,
                error_message="Unable to parse date",
                original_value=value
            )
            
        except Exception as e:
            return ValidationResult(
                value=value,
                is_valid=False,
                error_message=f"Date validation failed: {str(e)}",
                original_value=value
            )

    def _validate_amount(self, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate and normalize monetary amounts."""
        try:
            amount_str = str(value).strip()
            
            # Extract currency symbol
            currency_symbols = ['$', '€', '£', '¥', '₹', '₽']
            currency = None
            
            for symbol in currency_symbols:
                if symbol in amount_str:
                    currency = symbol
                    break
            
            # Clean the amount string
            cleaned_amount = re.sub(r'[^\d.,\-]', '', amount_str)
            
            # Handle comma as thousands separator vs decimal separator
            if ',' in cleaned_amount and '.' in cleaned_amount:
                # Assume comma is thousands separator if it appears before the last 3 digits
                if cleaned_amount.rfind(',') < cleaned_amount.rfind('.') - 3:
                    cleaned_amount = cleaned_amount.replace(',', '')
                else:
                    # European format: use comma as decimal separator
                    cleaned_amount = cleaned_amount.replace('.', '').replace(',', '.')
            elif ',' in cleaned_amount and cleaned_amount.count(',') == 1:
                # Check if comma is likely decimal separator (2-3 digits after)
                parts = cleaned_amount.split(',')
                if len(parts[1]) <= 3:
                    cleaned_amount = cleaned_amount.replace(',', '.')
                else:
                    cleaned_amount = cleaned_amount.replace(',', '')
            
            # Validate numeric value
            try:
                numeric_value = Decimal(cleaned_amount)
                
                # Check value constraints
                if rule.min_value is not None and float(numeric_value) < rule.min_value:
                    return ValidationResult(
                        value=amount_str,
                        is_valid=False,
                        error_message=f"Amount below minimum value ({rule.min_value})",
                        original_value=value
                    )
                
                if rule.max_value is not None and float(numeric_value) > rule.max_value:
                    return ValidationResult(
                        value=amount_str,
                        is_valid=False,
                        error_message=f"Amount above maximum value ({rule.max_value})",
                        original_value=value
                    )
                
                # Format the normalized amount
                if currency:
                    normalized_amount = f"{currency}{numeric_value:,.2f}"
                else:
                    normalized_amount = f"{numeric_value:,.2f}"
                
                return ValidationResult(
                    value=normalized_amount,
                    is_valid=True,
                    original_value=value,
                    validation_applied="normalization"
                )
                
            except InvalidOperation:
                return ValidationResult(
                    value=amount_str,
                    is_valid=False,
                    error_message="Invalid amount format",
                    original_value=value
                )
                
        except Exception as e:
            return ValidationResult(
                value=value,
                is_valid=False,
                error_message=f"Amount validation failed: {str(e)}",
                original_value=value
            )

    def _validate_number(self, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate numeric entities."""
        try:
            # Handle different input types
            if isinstance(value, (int, float)):
                numeric_value = float(value)
            else:
                # Try to convert string to number
                number_str = str(value).strip().replace(',', '')
                numeric_value = float(number_str)
            
            # Check value constraints
            if rule.min_value is not None and numeric_value < rule.min_value:
                return ValidationResult(
                    value=numeric_value,
                    is_valid=False,
                    error_message=f"Number below minimum value ({rule.min_value})",
                    original_value=value
                )
            
            if rule.max_value is not None and numeric_value > rule.max_value:
                return ValidationResult(
                    value=numeric_value,
                    is_valid=False,
                    error_message=f"Number above maximum value ({rule.max_value})",
                    original_value=value
                )
            
            # Return as integer if it's a whole number, otherwise float
            if numeric_value.is_integer():
                return ValidationResult(
                    value=int(numeric_value),
                    is_valid=True,
                    original_value=value
                )
            else:
                return ValidationResult(
                    value=numeric_value,
                    is_valid=True,
                    original_value=value
                )
                
        except (ValueError, TypeError) as e:
            return ValidationResult(
                value=value,
                is_valid=False,
                error_message=f"Invalid number format: {str(e)}",
                original_value=value
            )

    def _validate_array(self, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate array entities."""
        try:
            if isinstance(value, list):
                array_value = value
            elif isinstance(value, str):
                # Try to parse comma-separated values
                array_value = [item.strip() for item in value.split(',') if item.strip()]
            else:
                # Single value, convert to single-item array
                array_value = [value]
            
            # Clean array items
            cleaned_array = []
            for item in array_value:
                if isinstance(item, str):
                    cleaned_item = item.strip()
                    if cleaned_item:
                        cleaned_array.append(cleaned_item)
                else:
                    cleaned_array.append(item)
            
            return ValidationResult(
                value=cleaned_array,
                is_valid=True,
                original_value=value,
                validation_applied="normalization" if cleaned_array != array_value else None
            )
            
        except Exception as e:
            return ValidationResult(
                value=value,
                is_valid=False,
                error_message=f"Array validation failed: {str(e)}",
                original_value=value
            )

    def _validate_boolean(self, value: Any, rule: ValidationRule) -> ValidationResult:
        """Validate boolean entities."""
        try:
            if isinstance(value, bool):
                return ValidationResult(
                    value=value,
                    is_valid=True,
                    original_value=value
                )
            
            # Convert string to boolean
            if isinstance(value, str):
                value_lower = value.lower().strip()
                true_values = {'true', 'yes', '1', 'on', 'enabled', 'y', 't'}
                false_values = {'false', 'no', '0', 'off', 'disabled', 'n', 'f'}
                
                if value_lower in true_values:
                    return ValidationResult(
                        value=True,
                        is_valid=True,
                        original_value=value,
                        validation_applied="conversion"
                    )
                elif value_lower in false_values:
                    return ValidationResult(
                        value=False,
                        is_valid=True,
                        original_value=value,
                        validation_applied="conversion"
                    )
            
            # Try numeric conversion
            try:
                numeric_value = float(value)
                return ValidationResult(
                    value=bool(numeric_value),
                    is_valid=True,
                    original_value=value,
                    validation_applied="conversion"
                )
            except (ValueError, TypeError):
                pass
            
            return ValidationResult(
                value=value,
                is_valid=False,
                error_message="Unable to convert to boolean",
                original_value=value
            )
            
        except Exception as e:
            return ValidationResult(
                value=value,
                is_valid=False,
                error_message=f"Boolean validation failed: {str(e)}",
                original_value=value
            )

    def _clean_string(self, text: str) -> str:
        """Clean and normalize string values."""
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', text).strip()
        
        # Remove common OCR artifacts
        cleaned = cleaned.replace('|', 'I')  # Common OCR mistake
        cleaned = re.sub(r'[^\w\s\-.,@#$%&*()+=:;!?/\\]', '', cleaned)
        
        return cleaned

    def _check_required_entities(self, rules: List[ValidationRule], 
                                results: Dict[str, ValidationResult]):
        """Check that all required entities are present and valid."""
        for rule in rules:
            if rule.required:
                result = results.get(rule.entity_name)
                if not result or not result.is_valid or result.value is None:
                    logger.warning(f"Required entity '{rule.entity_name}' is missing or invalid")

    def _update_validation_stats(self, entity_type: str, is_valid: bool):
        """Update validation statistics."""
        self.validation_stats["total_validations"] += 1
        
        if is_valid:
            self.validation_stats["successful_validations"] += 1
        else:
            self.validation_stats["failed_validations"] += 1
        
        # Type-specific stats
        if entity_type not in self.validation_stats["type_specific_stats"]:
            self.validation_stats["type_specific_stats"][entity_type] = {
                "total": 0, "successful": 0, "failed": 0
            }
        
        type_stats = self.validation_stats["type_specific_stats"][entity_type]
        type_stats["total"] += 1
        
        if is_valid:
            type_stats["successful"] += 1
        else:
            type_stats["failed"] += 1

    def get_validation_summary(self, results: Dict[str, ValidationResult]) -> Dict[str, Any]:
        """Get a summary of validation results."""
        total_entities = len(results)
        valid_entities = sum(1 for r in results.values() if r.is_valid)
        invalid_entities = total_entities - valid_entities
        
        required_entities = []
        optional_entities = []
        missing_required = []
        
        # This would need document type info to determine required/optional
        # For now, just provide basic stats
        
        return {
            "total_entities": total_entities,
            "valid_entities": valid_entities,
            "invalid_entities": invalid_entities,
            "validation_rate": valid_entities / total_entities if total_entities > 0 else 0,
            "errors": [
                {"entity": name, "error": result.error_message}
                for name, result in results.items()
                if not result.is_valid and result.error_message
            ],
            "applied_validations": [
                {"entity": name, "validation": result.validation_applied}
                for name, result in results.items()
                if result.validation_applied
            ]
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get overall validation statistics."""
        return self.validation_stats.copy()

    def reset_statistics(self):
        """Reset validation statistics."""
        self.validation_stats = {
            "total_validations": 0,
            "successful_validations": 0,
            "failed_validations": 0,
            "type_specific_stats": {}
        }
