"""Moletillas (filler words) and common patterns for text cleanup."""

# Catalan moletillas and patterns
CA_MOLETILLAS = {
    r'\bvaja\b': '',
    r'\beh\b': '',
    r'\bem\b': '',
    r'\bés a dir\b': '',
    r'\bo sigui\b': '',
    r'\bpràcticament\b': '',
    r'\bbasicament\b': '',
    r'\bdoncs\b': '',
    r'\bdons\b': '',
    r'\bpues\b': '',
    r'\bbu\b': '',
    r'\bheu\b': '',
    r'\bpor\b': '',
    r'\bpor favor\b': 'sisplau',
    r'\bmmm\b': '',
    r'\bhhh\b': '',
    r'\bahhh\b': '',
    r'\buuu\b': '',
    r'\bummm\b': '',
    r'\byy\b': 'i',
    r'\bi bueno\b': 'i',
    r'\bbueno bueno\b': '',
}

# Spanish moletillas and patterns
ES_MOLETILLAS = {
    r'[¿]?sabes\s+qué\s+digo[?]?': '',
    r'\bvale\b': '',
    r'\bvaya\b': '',
    r'\beh\b': '',
    r'\bem\b': '',
    r'\bses decir\b': '',
    r'\bo sea\b': '',
    r'\bpues\b': '',
    r'\bpus\b': '',
    r'\bbueno\b': '',
    r'\bahhh\b': '',
    r'\bumm\b': '',
    r'\bmmm\b': '',
    r'\bhhh\b': '',
    r'\buuu\b': '',
    r'\by y\b': 'y',
    r'\bi bueno\b': 'y',
    r'\ba ver\b': '',
    r'\ba lo mejor\b': '',
    r'\btambién también\b': 'también',
}

# Common patterns for both languages
COMMON_PATTERNS = {
    r'\s+': ' ',  # Multiple spaces to single space
    r'([.!?])\s+([a-z])': r'\1 \2',  # Capitalize after punctuation (will be handled elsewhere)
    r'\s+([.!?,;:])': r'\1',  # Remove space before punctuation
}

# Abbreviations to expand (optional)
ABBREVIATIONS = {
    'tb': 'también',
    'tbm': 'también',
    'xq': 'porque',
}
