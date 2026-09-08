"""Provjera i izracun ocjene — cist Python, bez Streamlita i bez baze.

Namjerno bez zavisnosti da se moze testirati bez pokretanja aplikacije
(test_ocjena.py).
"""
import json
import re

def _normalizuj(t):
    """Za poređenje citata: mala slova, bez dijakritike, bez interpunkcije i viška razmaka."""
    t = (t or "").lower()
    for a, b in (("č", "c"), ("ć", "c"), ("ž", "z"), ("š", "s"), ("đ", "d")):
        t = t.replace(a, b)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def provjeri_ocjenu(r, transkript):
    """Odbacuje tvrdnje bez dokaza i preračunava ukupnu ocjenu u Pythonu.

    Model ne smije ni tvrditi ni računati bez provjere: citat koji se ne nalazi
    u transkriptu je izmišljen dokaz, a ponderisani zbir je aritmetika koju
    Python radi pouzdanije. Odbačene tvrdnje se čuvaju u 'odbaceno' za admina,
    ali se polazniku ne prikazuju.
    """
    if not isinstance(r, dict):
        return r
    tn = _normalizuj(transkript)
    odbaceno = []

    def ima_dokaz(citat):
        c = _normalizuj(citat)
        # Kratak citat je preslab dokaz da bi se na njemu gradila tvrdnja.
        if len(c) < 12:
            return False
        return c in tn

    ocisceno = []
    for p in r.get("pohvale", []) or []:
        if isinstance(p, str):          # stari format — nema šta da se provjeri
            ocisceno.append(p)
        elif ima_dokaz(p.get("citat", "")):
            ocisceno.append(p)
        else:
            odbaceno.append({"vrsta": "pohvala", "sadrzaj": p})
    r["pohvale"] = ocisceno

    ocisceno = []
    for p in r.get("pitano_ali_neodgovoreno", []) or []:
        if isinstance(p, dict) and ima_dokaz(p.get("citat_farmaceuta", "")):
            ocisceno.append(p)
        else:
            odbaceno.append({"vrsta": "pitano_ali_neodgovoreno", "sadrzaj": p})
    r["pitano_ali_neodgovoreno"] = ocisceno

    if odbaceno:
        r["odbaceno"] = odbaceno

    # Ukupna ocjena se računa ovdje, ne u modelu.
    try:
        r["ukupna_ocjena"] = round(
            float(r.get("anamneza", 0)) * 0.4
            + float(r.get("komunikacija", 0)) * 0.3
            + float(r.get("sigurnost", 0)) * 0.3, 1)
    except (TypeError, ValueError):
        pass

    # Kompatibilnost: stari prikaz, žalbe i CSV izvoz čitaju 'propustena_pitanja'.
    if "nije_pitano" in r and "propustena_pitanja" not in r:
        r["propustena_pitanja"] = [
            n.get("pitanje", "") if isinstance(n, dict) else str(n)
            for n in (r.get("nije_pitano") or [])
        ]
    return r


def izvuci_json(tekst):
    p, k = tekst.find("{"), tekst.rfind("}") + 1
    if p == -1 or k == 0:
        return None
    try:
        return json.loads(tekst[p:k])
    except Exception:
        return None
