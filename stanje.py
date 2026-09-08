"""Skriveno stanje pacijenta i didaskalije — čist Python, bez Streamlita.

Pacijent na kraju svake replike vraća red koji korisnik nikad ne vidi:

    <stanje povjerenje="6" anksioznost="7" faza="ispitivanje" otkriveno="tribulus" ishod=""/>

Aplikacija ga skida prije prikaza, ali ga ČUVA u historiji koja ide modelu —
tako pacijent vidi svoje prethodno stanje i ne počinje svaki potez iznova.

Model blok ponekad ispusti. Tada se zadržava prethodno stanje umjesto da se
padne na nulu: iznenadni pad povjerenja bez razloga u razgovoru je gora greška
od zadržanog stanja.
"""
import re

FAZE = ("otvaranje", "ispitivanje", "savjet", "otpor", "zatvaranje")
ISHODI = {
    "prihvatio": "Prihvatio savjet",
    "prihvatio_nevoljko": "Prihvatio nevoljko",
    "odbio": "Odbio i otišao",
    "otisao_s_lijekom": "Otišao sa traženim lijekom",
}

_STANJE_RE = re.compile(r"<\s*stanje\b[^>]*/?>", re.IGNORECASE)
_ATRIBUT_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
_DIDASKALIJA_RE = re.compile(r"\[([^\[\]]{1,80})\]")


def _broj(v, zadano=5):
    try:
        return max(0, min(10, int(float(v))))
    except (TypeError, ValueError):
        return zadano


def izdvoji_stanje(tekst, prethodno=None):
    """Vraća (tekst bez bloka, stanje). Ako blok fali, zadržava prethodno stanje."""
    tekst = tekst or ""
    nadjen = _STANJE_RE.search(tekst)
    cist = _STANJE_RE.sub("", tekst).strip()

    if not nadjen:
        return cist, dict(prethodno) if prethodno else None

    atributi = dict(_ATRIBUT_RE.findall(nadjen.group(0)))
    p = prethodno or {}
    faza = (atributi.get("faza") or "").strip().lower()
    ishod = (atributi.get("ishod") or "").strip().lower()
    otkriveno = [x.strip() for x in (atributi.get("otkriveno") or "").split(";") if x.strip()]

    return cist, {
        "povjerenje": _broj(atributi.get("povjerenje"), p.get("povjerenje", 5)),
        "anksioznost": _broj(atributi.get("anksioznost"), p.get("anksioznost", 5)),
        "faza": faza if faza in FAZE else p.get("faza", "otvaranje"),
        "otkriveno": otkriveno,
        "ishod": ishod if ishod in ISHODI else "",
    }


def sve_otkriveno(stanja):
    """Unija svih otkrivenih činjenica kroz razgovor, redom pojavljivanja."""
    vidjeno, red = set(), []
    for s in stanja or []:
        for i in s.get("otkriveno", []):
            if i not in vidjeno:
                vidjeno.add(i)
                red.append(i)
    return red


def zadnji_ishod(stanja):
    for s in reversed(stanja or []):
        if s.get("ishod"):
            return s["ishod"]
    return ""


def krivulja_povjerenja(stanja):
    return [s.get("povjerenje", 5) for s in (stanja or []) if "povjerenje" in s]


def sazetak_za_evaluatora(stanja, cinjenice=None):
    """Kratak tekst koji ide ocjenjivaču kao dodatni dokaz.

    Ocjenjivač iz transkripta ne može znati je li pacijent nešto uskratio zato
    što nije bio pitan ili zato što povjerenje nije bilo dovoljno — ovo mu to kaže.
    """
    if not stanja:
        return ""
    krivulja = krivulja_povjerenja(stanja)
    otkriveno = sve_otkriveno(stanja)
    redovi = [
        "SKRIVENO STANJE PACIJENTA (podatak koji farmaceut nije mogao vidjeti):",
        f"- povjerenje kroz razgovor: {' → '.join(str(x) for x in krivulja)}"
        if krivulja else "- povjerenje: nepoznato",
    ]
    if cinjenice:
        nazivi = {c.get("id"): c.get("cinjenica", "") for c in cinjenice}
        # Model ponekad izmisli id koji nije u listi — takav se ne broji, inace
        # bi ispalo da je otkriveno vise cinjenica nego sto scenarij uopste ima.
        stvarno = [i for i in otkriveno if i in nazivi]
        redovi.append(f"- otkriveno {len(stvarno)} od {len(nazivi)} činjenica")
        propusteno = [nazivi[i] for i in nazivi if i not in stvarno]
        if propusteno:
            redovi.append("- neotkriveno: " + "; ".join(propusteno[:8]))
    elif otkriveno:
        redovi.append("- otkrivene činjenice: " + ", ".join(otkriveno))

    ishod = zadnji_ishod(stanja)
    if ishod:
        redovi.append(f"- ishod razgovora: {ISHODI.get(ishod, ishod)}")
    return "\n".join(redovi)


def razdvoji_didaskalije(tekst):
    """Vraća listu komada [(vrsta, tekst)] gdje je vrsta 'govor' ili 'didaskalija'."""
    komadi, zadnji = [], 0
    for m in _DIDASKALIJA_RE.finditer(tekst or ""):
        prije = tekst[zadnji:m.start()].strip()
        if prije:
            komadi.append(("govor", prije))
        komadi.append(("didaskalija", m.group(1).strip()))
        zadnji = m.end()
    ostatak = (tekst or "")[zadnji:].strip()
    if ostatak:
        komadi.append(("govor", ostatak))
    return komadi
