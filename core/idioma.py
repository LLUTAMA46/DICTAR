"""Idioma de dictat triat per l'usuari: català (per defecte) o castellà.

Es canvia des del menú de la icona de l'SFlow (barra de dalt) i es recorda
en un fitxer petit, «idioma.txt», perquè l'SFlow el mantingui en reiniciar.
"""

import os

from config import APP_DATA_DIR

_FITXER = os.path.join(APP_DATA_DIR, "idioma.txt")
IDIOMES = ("ca", "es")

# Frase d'orientació per a l'escolta de la veu: li indica l'idioma i que
# posi comes i punts. (Es poden afegir noms propis habituals de l'usuari.)
VOCABULARI = {
    "ca": "Dictat en català, amb comes i punts. Escriptor, ordinador, Softcatalà.",
    "es": "Dictado en castellano, con comas y puntos. Escritor, ordenador.",
}

# Idioma per al corrector de Softcatalà.
CORRECTOR = {"ca": "ca-ES", "es": "es"}

_actual = None


def actual() -> str:
    global _actual
    if _actual is None:
        try:
            with open(_FITXER, encoding="utf-8") as f:
                valor = f.read().strip()
            _actual = valor if valor in IDIOMES else "ca"
        except OSError:
            _actual = "ca"
    return _actual


def canvia(nou: str) -> None:
    global _actual
    if nou not in IDIOMES:
        return
    _actual = nou
    try:
        with open(_FITXER, "w", encoding="utf-8") as f:
            f.write(nou)
    except OSError:
        pass
