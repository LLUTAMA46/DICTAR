"""Corrector de Softcatalà (LanguageTool) per al text dictat.

Envia el text al servei públic de Softcatalà, que detecta si és català o
castellà i proposa correccions segons la normativa vigent (IEC per al català).

Criteri prudent: només s'apliquen les correccions SEGURES (accents, diacrítics,
apòstrofs, confusions, puntuació i gramàtica bàsica). No es toca l'estil ni
els noms propis. Si el servei no respon, el text surt tal com era.

Cada canvi queda anotat a «correccions.txt» perquè l'autor el pugui revisar.
"""

import json
import os
import ssl
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime

from config import APP_DATA_DIR
from core import idioma

API_URL = "https://api.softcatala.org/corrector/v2/check"
TIMEOUT_SECONDS = 5
LOG_PATH = os.path.join(APP_DATA_DIR, "correccions.txt")

# Certificats de seguretat: els mateixos que fa servir la connexió amb Groq
# (el Python de python.org no porta els del sistema).
try:
    import certifi
    _SSL = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL = ssl.create_default_context()

# Categories que s'apliquen automàticament (la resta s'ignoren: estil,
# variants regionals, redundàncies...).
SAFE_CATEGORIES = {
    "TYPOS",            # ortografia (amb la protecció de més avall)
    "DIACRITICS",       # és/es, té/te, més/mes...
    "DIACRITICS_IEC",   # diacrítics suprimits el 2017 (dóna -> dona)
    "CONFUSIONS",       # despres -> després
    "APOSTROPHATION",   # de anar -> d'anar
    "PUNCTUATION",      # pero -> , però
    "GRAMMAR",
    "VERBS",            # hi han -> hi ha, tenim que -> hem de
    # Afegides el 20/11/2026 (corrector «una mica més exigent»):
    "CONFUSIONS2",            # apenes -> a penes
    "CONJUNCTIONS",           # conforme -> a mesura que
    "SPELLING",               # soft català -> Softcatalà
    "INCORRECT_EXPRESSIONS",  # lo bo -> el bo
    "REFLEXIVE_VERBS",        # donar-se compte -> adonar-se
}
# Expressament FORA: STYLE, PREFERABLE_EXPRESSIONS (estic entenent -> entenc),
# PREPOSITIONS (proposava «a veure» -> «de veure», erroni), REGIONAL_VERBS,
# TYPOGRAPHY. Són qüestions d'estil o massa insegures: la veu és de l'autor.


def _sense_accents(paraula: str) -> str:
    nfd = unicodedata.normalize("NFD", paraula)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()


def _es_segura(match: dict, text: str) -> bool:
    if not match.get("replacements"):
        return False
    categoria = match["rule"]["category"]["id"]
    if categoria not in SAFE_CATEGORIES:
        return False
    if categoria == "TYPOS":
        inici, llarg = match["offset"], match["length"]
        original = text[inici:inici + llarg]
        proposta = match["replacements"][0]["value"]
        # Només arreglem accents: si la paraula canvia de lletres, no la toquem
        # (pot ser un nom propi o una paraula que el diccionari no coneix).
        if _sense_accents(original) != _sense_accents(proposta):
            return False
        # Paraula amb majúscula enmig de frase: probablement un nom propi.
        abans = text[:inici].rstrip()
        if original[:1].isupper() and abans and abans[-1] not in ".!?":
            return False
    return True


def _anota(original: str, corregit: str, canvis: list[str]) -> None:
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n=== {datetime.now():%d/%m/%Y %H:%M} ===\n")
            f.write(f"Abans:  {original}\n")
            f.write(f"Després: {corregit}\n")
            for c in canvis:
                f.write(f"  · {c}\n")
    except OSError:
        pass


def corregeix(text: str) -> str:
    """Retorna el text amb les correccions segures aplicades."""
    if not text or not text.strip():
        return text
    try:
        dades = urllib.parse.urlencode({
            "language": idioma.CORRECTOR[idioma.actual()],
            "text": text,
        }).encode("utf-8")
        peticio = urllib.request.Request(API_URL, data=dades, method="POST")
        with urllib.request.urlopen(peticio, timeout=TIMEOUT_SECONDS,
                                    context=_SSL) as resp:
            resultat = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return text  # sense connexió o servei aturat: el dictat no s'atura

    segures = [m for m in resultat.get("matches", []) if _es_segura(m, text)]
    if not segures:
        return text

    # S'apliquen de darrere cap endavant perquè les posicions no es moguin.
    corregit = text
    canvis = []
    for m in sorted(segures, key=lambda m: m["offset"], reverse=True):
        inici, llarg = m["offset"], m["length"]
        original = corregit[inici:inici + llarg]
        proposta = m["replacements"][0]["value"]
        corregit = corregit[:inici] + proposta + corregit[inici + llarg:]
        canvis.append(f"«{original}» → «{proposta}»")

    _anota(text, corregit, list(reversed(canvis)))
    return corregit
