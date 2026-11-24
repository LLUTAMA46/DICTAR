"""Sons de dubte que es treuen del text dictat.

Criteri (24/11/2026, decidit pel Lluís): NOMÉS sons, MAI paraules.
Paraules com «em», «heu», «doncs», «o sigui», «vaja», «eh», «pues»,
«bueno», «a lo mejor»... són de l'autor o dels seus personatges i
no s'esborren mai. Còpia de l'antiga llista a el commit anterior del repositori.
"""

# Sons de dubte (es reconeixen igual en català i en castellà)
_SONS = r'\b(?:ehm+|eh{2,}|e{3,}|m{2,}|hm+|uhm+|um{2,}|ah{2,}|u{3,}|h{3,})\b'

CA_MOLETILLAS = {
    _SONS: '',
    r'\byy\b': 'i',
}

ES_MOLETILLAS = {
    _SONS: '',
    r'\byy\b': 'y',
}

# (Es mantenen per compatibilitat amb el codi que les importa.)
COMMON_PATTERNS = {
    r'\s+': ' ',
    r'\s+([.!?,;:])': r'\1',
}
