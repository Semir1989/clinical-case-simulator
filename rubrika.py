"""Rubrika v2 — kriteriji kao struktura, ne kao slobodan tekst.

Ovdje živi sve što se tiče rubrike: parsiranje starog tekstualnog oblika u
strukturu, izračun ocjene iz statusa po kriteriju, i shema alata kojom se
evaluator prisiljava da vrati tačno te kriterije.

Namjerno bez Streamlita i bez baze — sve se može testirati bez pokretanja
aplikacije (test_rubrika.py).

STATUSI po kriteriju:
    DA          — kriterij ispunjen, nosi pune bodove
    DJELIMICNO  — djelimično ispunjen, nosi pola bodova
    NE          — nije ispunjen, nosi nula

Zašto se bodovi računaju ovdje a ne u modelu: kalibracija na Semirova tri
transkripta pokazala je da model pogađa anamnezu i komunikaciju (odstupanje
0.33 boda), ali sigurnost sistematski podbacuje za 1.33 — sabiranje mu ne ide.
Model sada samo sudi kriterij po kriterij; zbrajanje radi Python.

DVIJE VRSTE KAZNI. Stara rubrika ih je miješala u jednu rečenicu, a ponašaju
se suprotno:

    propust — "bez pitanja o trudnoci max 4/10". Gori kad farmaceut NIJE
              uradio nešto. Veže se za kriterije i gori samo ako su svi ti
              kriteriji NE. Ovo je nalaz N2 pretvoren u strukturu: dok je
              kazna bila samo rečenica u promptu, model ju je palio i kad je
              pitanje bilo postavljeno.
    radnja  — "dao kortikosteroid trudnici = 0/10". Gori kad je farmaceut
              nešto URADIO. Nijedan kriterij ne opisuje tu radnju, pa je model
              mora prijaviti izričito i s citatom.

Nijedna kazna ne gori ako je ijedan kriterij koji spominje priznat.
"""
import re

STATUSI = ("DA", "DJELIMICNO", "NE")
UDIO = {"DA": 1.0, "DJELIMICNO": 0.5, "NE": 0.0}

KATEGORIJE = (
    ("anamneza", "Anamneza", 0.4),
    ("komunikacija", "Komunikacija", 0.3),
    ("sigurnost", "Sigurnost", 0.3),
)

# "sta koristi i koliko dugo(2)" — hvata sve do zagrade s brojem, pa zarezi
# unutar samog kriterija ("mutan vid, krugovi oko svjetla") ostaju netaknuti.
_KRITERIJ = re.compile(r"(?P<tekst>[^()]*(?:\([^\d)][^)]*\)[^()]*)*?)\((?P<bodovi>\d+(?:[.,]\d+)?)\)")

# "bez pitanja o trudnoci max 4/10"  |  "dao kortikosteroid trudnici = 0/10"
_KAZNA_MAX = re.compile(r"^(?P<opis>.+?)\s*(?:=\s*)?max\s*(?P<max>\d+(?:[.,]\d+)?)\s*/\s*10", re.I)
_KAZNA_NULA = re.compile(r"^(?P<opis>.+?)\s*=\s*(?P<max>\d+(?:[.,]\d+)?)\s*/\s*10", re.I)

# Kazna koja počinje ovako opisuje propust; sve ostalo je radnja.
_PROPUST = re.compile(r"^(bez|nije|ne\s|niti|propustio|izostal)", re.I)

_STOP = {
    "bez", "pitanja", "pitanje", "pitao", "nije", "sta", "koji", "koje", "koja", "ili", "sa",
    "za", "o", "u", "i", "je", "su", "se", "na", "od", "do", "kao", "ako", "max", "svih",
    "bilo", "kojeg", "uz", "te", "ni", "niti", "da", "li", "ijednog", "ijedno", "eksplicitno",
    "aktivno", "utvrdio", "prepoznao", "savjetovao", "preporucio", "preporuka", "dao",
}

# Bosanski mijenja nastavke ("trudnoci" / "trudnocu"), pa se poredi korijen.
_KORIJEN = 5


def _broj(t):
    return float(str(t).replace(",", "."))


def _korijeni(t):
    t = (t or "").lower()
    for a, b in (("č", "c"), ("ć", "c"), ("ž", "z"), ("š", "s"), ("đ", "d")):
        t = t.replace(a, b)
    return {r[:_KORIJEN] for r in re.findall(r"[a-z0-9]+", t) if r not in _STOP and len(r) > 2}


def parsiraj(tekst):
    """Pretvara staru tekstualnu rubriku u strukturu.

    Podnosi oba oblika koja postoje u scenarijima: nabrajanje zarezom u jednom
    redu (scenariji 1, 2 i 3) i crtice u zasebnim redovima (scenarij 4).
    Vraća None ako u tekstu nema nijedne prepoznate kategorije.
    """
    if not tekst:
        return None

    nazivi = {n.upper(): (i, n, t) for i, n, t in KATEGORIJE}
    kategorije, tekuca = [], None

    for red in tekst.splitlines():
        red = red.strip()
        if not red:
            continue

        zaglavlje = re.match(
            r"^([A-Za-zČĆŽŠĐčćžšđ]+)\s*\(\s*tezina\s*(\d+(?:[.,]\d+)?)\s*\)\s*:\s*(.*)$",
            red, re.I)
        if zaglavlje and zaglavlje.group(1).upper() in nazivi:
            kid, naziv, _ = nazivi[zaglavlje.group(1).upper()]
            tekuca = {"id": kid, "naziv": naziv, "tezina": _broj(zaglavlje.group(2)),
                      "kriteriji": [], "kazne": []}
            kategorije.append(tekuca)
            _dodaj_kriterije(tekuca, zaglavlje.group(3))
            continue

        if tekuca is None:
            continue

        if red.upper().startswith("KAZNA"):
            _dodaj_kazne(tekuca, red.split(":", 1)[-1])
            continue

        _dodaj_kriterije(tekuca, red)

    if not kategorije:
        return None

    _povezi_kazne(kategorije)
    return {"verzija": 2, "kategorije": kategorije}


def _dodaj_kriterije(kat, tekst):
    """Vadi sve "opis(bodovi)" iz jednog reda, bez obzira na zareze u opisu."""
    for m in _KRITERIJ.finditer(tekst or ""):
        opis = m.group("tekst").strip().strip(",;").strip().lstrip("-*. ").strip()
        if not opis:
            continue
        kat["kriteriji"].append({
            "id": "%s_%d" % (kat["id"], len(kat["kriteriji"]) + 1),
            "tekst": opis,
            "bodovi": _broj(m.group("bodovi")),
        })


def _dodaj_kazne(kat, tekst):
    for komad in (tekst or "").split(";"):
        komad = komad.strip()
        if not komad:
            continue
        # "za Sigurnost" na kraju samo ponavlja kategoriju u kojoj kazna vec stoji
        komad = re.sub(r"\s*za\s+(anamnez\w*|komunikacij\w*|sigurnost)\s*$", "", komad, flags=re.I)
        m = _KAZNA_MAX.match(komad) or _KAZNA_NULA.match(komad)
        if not m:
            continue
        opis = m.group("opis").strip(" .;=")
        kat["kazne"].append({
            "id": "%s_kazna_%d" % (kat["id"], len(kat["kazne"]) + 1),
            "opis": opis,
            "max": _broj(m.group("max")),
            "vrsta": "propust" if _PROPUST.match(opis) else "radnja",
            "vezano_za": [],
        })


def _povezi_kazne(kategorije):
    """Veže svaku kaznu za kriterije o kojima govori.

    Traži se po svim kategorijama, ne samo unutar vlastite: kazna „preporuka
    simptomatske terapije bez pitanja o suplementima“ stoji pod Sigurnošću, a
    govori o kriteriju iz Anamneze.

    Prag je dvije zajedničke riječi jer jedna prečesto spoji nevezane stavke.
    Kad kazna ima svega dvije nosive riječi, spušta se na jednu — inače kratke
    kazne poput „bez pitanja o trudnoci“ nikad ne bi našle svoj kriterij.
    """
    svi = [(kr, kat) for kat in kategorije for kr in kat["kriteriji"]]
    for kat in kategorije:
        for kazna in kat["kazne"]:
            rk = _korijeni(kazna["opis"])
            prag = 2 if len(rk) >= 3 else 1
            najbolji, najvise = [], 0
            for kr, _ in svi:
                preklop = len(rk & _korijeni(kr["tekst"]))
                if preklop > najvise:
                    najbolji, najvise = [kr["id"]], preklop
                elif preklop == najvise and preklop > 0:
                    najbolji.append(kr["id"])
            kazna["vezano_za"] = najbolji if najvise >= prag else []
            # Kazna za propust bez ijednog vezanog kriterija ne moze zagorjeti.
            kazna["rucna_provjera"] = (kazna["vrsta"] == "propust" and not kazna["vezano_za"])


# ─── Rucne ispravke veza ─────────────────────────────────────────────────────
# Automatsko vezanje ide po zajednickim korijenima rijeci i na sest mjesta je
# promasilo. Svaka ispravka ispod je provjerena rucno; bez njih bi kazne gorjele
# na krivom okidacu (ili ne bi gorjele kad treba).
ISPRAVKE_VEZA = {
    "scenarij_1": {
        # "dao kortikosteroid trudnici" nema veze s tim je li pitao za trudnocu,
        # nego s tim je li odbio izdati.
        "sigurnost_kazna_1": ["sigurnost_1"],
    },
    "scenarij_2": {
        # Rijeci "biljni preparat" postoje i u Sigurnosti, pa je kazna iz
        # Anamneze zavrsila vezana za pogresnu kategoriju.
        "anamneza_kazna_1": ["anamneza_2", "anamneza_3"],
        "anamneza_kazna_2": ["anamneza_4"],
        "sigurnost_kazna_1": ["sigurnost_1"],
    },
    "scenarij_3": {
        # Izdavanje se gasi ako je odbio ijedno od dvoje — i pakovanje i kapi.
        "sigurnost_kazna_1": ["sigurnost_3", "sigurnost_4"],
        # "tretirao kao gripu bez hitnog upucivanja" gasi se hitnim upucivanjem.
        "sigurnost_kazna_2": ["sigurnost_2"],
    },
    "scenarij_4": {
        # Najvaznija ispravka: kazna govori "bez pitanja o suplementima", pa se
        # mora gasiti kriterijem o suplementima. Bas na ovom mjestu je stari
        # ocjenjivac Semiru upisao propust koji nije napravio (nalaz N2).
        "sigurnost_kazna_2": ["anamneza_2"],
    },
}


def za_scenarij(sc, sid=None):
    """Vraća rubriku v2 za scenarij — gotovu iz podataka ili parsiranu iz teksta.

    Scenariji jos nose rubriku kao tekst, pa se struktura racuna u letu i
    dopunjava rucnim ispravkama veza. Kad generator jednom pocne pisati
    rubrika_v2 direktno, ova funkcija ce je samo proslijediti.
    """
    r = sc.get("rubrika_v2") or parsiraj(sc.get("rubrika", ""))
    if not r:
        return None
    sid = sid or sc.get("id")
    for kid, vezano in (ISPRAVKE_VEZA.get(sid) or {}).items():
        for kat in r.get("kategorije", []):
            for kazna in kat.get("kazne", []):
                if kazna["id"] == kid:
                    kazna["vezano_za"] = list(vezano)
                    kazna["rucna_provjera"] = False
    return r


def izracunaj(rubrika, ocjene, radnje=None):
    """Računa bodove po kategoriji iz statusa po kriteriju.

    `ocjene` je {id_kriterija: {"status": "DA"|"DJELIMICNO"|"NE", ...}}.
    `radnje` je popis id-ova kazni vrste "radnja" koje je model prijavio.
    Vraća {"anamneza": 6.0, ..., "ukupna_ocjena": 5.6, "kazne_primijenjene": [...]}.

    Bodovi se skaliraju na 0-10 i kad zbir bodova u rubrici nije tačno 10, pa
    naknadno dopisan kriterij ne pomjeri skalu ispod nogu ranijim rezultatima.
    """
    radnje = set(radnje or ())
    izlaz, primijenjene = {}, []

    for kat in rubrika.get("kategorije", []):
        moguce = sum(k["bodovi"] for k in kat["kriteriji"])
        osvojeno = 0.0
        for kr in kat["kriteriji"]:
            status = (ocjene.get(kr["id"]) or {}).get("status", "NE")
            osvojeno += kr["bodovi"] * UDIO.get(status, 0.0)

        bod = round(10.0 * osvojeno / moguce, 1) if moguce else 0.0

        for kazna in kat.get("kazne", []):
            if _kazna_gori(kazna, ocjene, radnje) and bod > kazna["max"]:
                bod = kazna["max"]
                primijenjene.append({"id": kazna["id"], "opis": kazna["opis"],
                                     "max": kazna["max"], "kategorija": kat["id"]})

        izlaz[kat["id"]] = round(bod, 1)

    izlaz["ukupna_ocjena"] = round(
        sum(izlaz.get(kat["id"], 0) * kat["tezina"] for kat in rubrika.get("kategorije", [])), 1)
    izlaz["kazne_primijenjene"] = primijenjene
    return izlaz


def _kazna_gori(kazna, ocjene, radnje):
    """Nijedna kazna ne gori ako je ijedan kriterij koji spominje priznat."""
    vezani = kazna.get("vezano_za") or []
    priznat = any((ocjene.get(kid) or {}).get("status", "NE") != "NE" for kid in vezani)
    if priznat:
        return False
    if kazna.get("vrsta") == "radnja":
        return kazna["id"] in radnje
    # Propust bez vezanih kriterija nema na cemu da gori — radije propustena
    # kazna nego lazna optuzba, jer je lazna optuzba bila cijeli nalaz N2.
    return bool(vezani)


def kazne_radnje(rubrika):
    """Popis kazni koje model mora sam prijaviti (vrsta "radnja")."""
    return [k for kat in rubrika.get("kategorije", []) for k in kat.get("kazne", [])
            if k.get("vrsta") == "radnja"]


def kriterij_po_id(rubrika, kid):
    for kat in rubrika.get("kategorije", []):
        for kr in kat["kriteriji"]:
            if kr["id"] == kid:
                return kr, kat
    return None, None


def shema_alata(rubrika):
    """Gradi input_schema za tool use — model mora vratiti tačno ove kriterije.

    Svaki kriterij je zaseban objekt s obaveznim statusom i citatom, pa model
    ne može preskočiti kriterij niti izmisliti novi. Bodove ne traži uopšte —
    njih računa izracunaj().
    """
    svojstva, obavezni = {}, []
    for kat in rubrika.get("kategorije", []):
        for kr in kat["kriteriji"]:
            svojstva[kr["id"]] = {
                "type": "object",
                "description": "%s: %s" % (kat["naziv"], kr["tekst"]),
                "properties": {
                    "status": {"type": "string", "enum": list(STATUSI)},
                    "citat": {"type": "string",
                              "description": "Doslovan citat farmaceuta iz transkripta koji "
                                             "dokazuje status. Obavezan za DA i DJELIMICNO, "
                                             "prazan za NE."},
                    "obrazlozenje": {"type": "string",
                                     "description": "Jedna recenica upucena polazniku."},
                },
                "required": ["status", "citat", "obrazlozenje"],
            }
            obavezni.append(kr["id"])

    shema = {
        "type": "object",
        "properties": {
            # Popis ide PRVI namjerno. Model pise polja redom kojim su navedena,
            # pa kad prvo prepise sva pitanja, sudi na osnovu popisa umjesto po
            # dojmu. To je isti dvokoracni postupak koji je zatvorio nalaz N2,
            # samo sto ga sada drzi shema a ne recenica u promptu.
            "pitanja_farmaceuta": {
                "type": "array",
                "description": "Doslovan citat svakog pitanja i zahtjeva koji je farmaceut "
                               "uputio pacijentu, redom. Prepisuje se znak po znak, s "
                               "pravopisnim greskama. Vise pitanja u jednoj poruci idu kao "
                               "zasebni unosi. Popuni ovo prije bilo kakvog suda.",
                "items": {"type": "string"},
            },
            "kriteriji": {"type": "object", "properties": svojstva, "required": obavezni},
            "pohvale": {
                "type": "array", "description": "Najvise tri stvari koje je uradio dobro.",
                "items": {"type": "object",
                          "properties": {"tekst": {"type": "string"},
                                         "citat": {"type": "string"}},
                          "required": ["tekst", "citat"]},
            },
            "smjernice": {
                "type": "array", "description": "Najvise tri upute za sljedeci put.",
                "items": {"type": "string"},
            },
        },
        "required": ["pitanja_farmaceuta", "kriteriji", "pohvale", "smjernice"],
    }

    radnje = kazne_radnje(rubrika)
    if radnje:
        popis = "; ".join("%s = %s" % (k["id"], k["opis"]) for k in radnje)
        shema["properties"]["radnje"] = {
            "type": "array",
            "description": "Id svake stete koju je farmaceut STVARNO ucinio u transkriptu. "
                           "Prazno ako nijedne nema. Mogucnosti: " + popis,
            "items": {"type": "object",
                      "properties": {"id": {"type": "string",
                                            "enum": [k["id"] for k in radnje]},
                                     "citat": {"type": "string",
                                               "description": "Doslovan citat koji to dokazuje."}},
                      "required": ["id", "citat"]},
        }
        shema["required"].append("radnje")
    return shema
