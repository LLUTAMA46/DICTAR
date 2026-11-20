"""Text post-processing: moletilla removal, spell checking, language-aware cleanup."""

import re
from core.moletillas import CA_MOLETILLAS, ES_MOLETILLAS, COMMON_PATTERNS


class TextPostprocessor:
    """Clean transcribed text by removing moletillas and fixing common errors."""

    def __init__(self):
        self.ca_patterns = CA_MOLETILLAS
        self.es_patterns = ES_MOLETILLAS

    def detect_language(self, text: str) -> str:
        """Detect if text is Catalan (ca) or Spanish (es). Defaults to 'ca'."""
        # Simple heuristic: count typical Catalan vs Spanish words
        ca_markers = ['és', 'que', 'per', 'com', 'potser', 'perquè']
        es_markers = ['es', 'que', 'por', 'cómo', 'quizás', 'porque']

        ca_count = sum(1 for marker in ca_markers if marker in text.lower())
        es_count = sum(1 for marker in es_markers if marker in text.lower())

        # If text contains Spanish-specific accented marks or patterns
        if 'á' in text or 'é' in text or 'ó' in text or 'ú' in text:
            if es_count > ca_count:
                return 'es'

        # Default to Catalan if ambiguous
        return 'ca' if ca_count >= es_count else 'es'

    def remove_moletillas(self, text: str, language: str) -> str:
        """Remove filler words based on detected language."""
        patterns = self.ca_patterns if language == 'ca' else self.es_patterns

        result = text
        for pattern, replacement in patterns.items():
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

        return result

    def clean_spacing(self, text: str) -> str:
        """Fix spacing issues: multiple spaces, space before punctuation, dangling punctuation."""
        result = text

        # Multiple spaces to single space
        result = re.sub(r'\s+', ' ', result)

        # Remove space before punctuation
        result = re.sub(r'\s+([.!?,;:])', r'\1', result)

        # Remove space after opening brackets/quotes
        result = re.sub(r'([\(\[\{"\'])\s+', r'\1', result)

        # Remove space before closing brackets/quotes
        result = re.sub(r'\s+([\)\]\}"\'])', r'\1', result)

        # Fix double/multiple punctuation
        result = re.sub(r'([.!?,;:])+', r'\1', result)

        # Remove comma followed by comma or period
        result = re.sub(r',(\s*[,.])', r'\1', result)

        # Remove leading/trailing punctuation and spaces
        result = re.sub(r'^[,\s]+', '', result)
        result = re.sub(r'[,\s]+$', '', result)

        # Fix empty question/exclamation marks
        result = re.sub(r'[¿\?]{2,}', '?', result)
        result = re.sub(r'[¡!]{2,}', '!', result)

        return result.strip()

    def remove_repeated_words(self, text: str) -> str:
        """Remove consecutive repeated words, even when separated by commas."""
        # Words repeated with spaces only: "no no no" -> "no"
        result = re.sub(r'\b(\w+)(\s+\1)+\b', r'\1', text, flags=re.IGNORECASE)
        # Words repeated with optional comma+space: "esticara, esticara" -> "esticara"
        result = re.sub(r'\b(\w+),\s+\1\b', r'\1', result, flags=re.IGNORECASE)
        return result

    def capitalize_properly(self, text: str) -> str:
        """Capitalize first letter and letters after punctuation."""
        if not text:
            return text

        # Capitalize first letter
        result = text[0].upper() + text[1:] if len(text) > 1 else text.upper()

        # Capitalize after sentence-ending punctuation
        result = re.sub(r'([.!?])\s+([a-z])', lambda m: m.group(1) + ' ' + m.group(2).upper(), result)

        return result

    def process(self, text: str, language: str | None = None) -> str:
        """Full post-processing pipeline."""
        if not text or not text.strip():
            return text

        # Idioma triat al menú; si no se'n diu cap, s'endevina
        if language not in ('ca', 'es'):
            language = self.detect_language(text)

        # Remove repeated words first (before other cleanup)
        text = self.remove_repeated_words(text)

        # Remove moletillas (including phrases like "sabes qué digo")
        text = self.remove_moletillas(text, language)

        # Clean spacing and punctuation
        text = self.clean_spacing(text)

        # Capitalize properly
        text = self.capitalize_properly(text)

        return text
