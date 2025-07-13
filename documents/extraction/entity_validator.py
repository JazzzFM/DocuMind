from typing import Dict, Any, Optional
from dateutil import parser

class EntityValidator:
    """Validates and cleans extracted entities."""

    def validate(self, extracted: Dict[str, Any], expected_entities: list) -> Dict[str, Any]:
        """Validates and cleans extracted entities based on expected types."""
        validated = {}
        for entity in expected_entities:
            value = extracted.get(entity)
            if value is not None:
                if 'date' in entity:
                    value = self._validate_date(str(value))
                elif 'amount' in entity:
                    value = self._validate_amount(str(value))
                # Add more validation rules as needed
            validated[entity] = value
        return validated

    def _validate_date(self, date_str: str) -> Optional[str]:
        """Validates and formats a date string to ISO 8601."""
        try:
            date_obj = parser.parse(date_str)
            return date_obj.strftime('%Y-%m-%d')
        except ValueError:
            return None

    def _validate_amount(self, amount_str: str) -> Optional[str]:
        """Validates and formats an amount string."""
        # Simple validation: ensure it's a string and can be converted to float
        try:
            float(amount_str.replace('$', '').replace(',', ''))
            return amount_str
        except ValueError:
            return None
