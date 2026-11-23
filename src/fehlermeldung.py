"""Validation errors in German, as the trainer reads them when a file or a scenario is refused."""

from collections.abc import Iterable
from typing import Any

MELDUNGEN = {
    "missing": "fehlt",
    "extra_forbidden": "ist hier nicht vorgesehen",
    "literal_error": "muss {expected} sein",
    "enum": "muss {expected} sein",
    "string_type": "muss ein Text sein",
    "int_type": "muss eine ganze Zahl sein",
    "int_parsing": "muss eine ganze Zahl sein",
    "float_type": "muss eine Zahl sein",
    "float_parsing": "muss eine Zahl sein",
    "bool_type": "muss wahr oder falsch sein",
    "bool_parsing": "muss wahr oder falsch sein",
    "list_type": "muss eine Liste sein",
    "dict_type": "muss ein Objekt sein",
    "model_type": "muss ein Objekt sein",
    "model_attributes_type": "muss ein Objekt sein",
    "tuple_type": "muss eine Liste sein",
    "too_short": "hat zu wenige Einträge",
    "too_long": "hat zu viele Einträge",
    "json_invalid": "ist kein gültiges JSON",
}


def deutsch(fehler: Iterable[dict[str, Any]]) -> str:
    """Return validation errors as one German line per fault, each with where it sits."""
    return "\n".join(zeile(eintrag) for eintrag in fehler)


def zeile(eintrag: dict[str, Any]) -> str:
    """Return one validation error as a German line."""
    ort = ".".join(str(teil) for teil in eintrag.get("loc", ()) if teil != "body")
    return f"{ort}: {meldung(eintrag)}" if ort else meldung(eintrag)


def meldung(eintrag: dict[str, Any]) -> str:
    """Return the German message of one validation error."""
    if eintrag["type"] == "value_error":
        return str(eintrag.get("ctx", {}).get("error", eintrag["msg"]))
    vorlage = MELDUNGEN.get(eintrag["type"])
    if vorlage is None:
        return "ist ungültig"
    kontext = {k: str(v).replace(" or ", " oder ") for k, v in eintrag.get("ctx", {}).items()}
    return vorlage.format(**kontext)
