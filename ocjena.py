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
        return _ima_dokaz(citat, tn)

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


def _ima_dokaz(citat, tn):
    """Provjerava stoji li citat zaista u transkriptu.

    Model rado spoji dva udaljena navoda u jedan citat s tri tačke
    ("Koliko dugo pijete... da li su to bili lijekovi u kesicama"). Oba dijela
    su doslovna, pa je dokaz valjan — ali kao jedan niz ne postoji nigdje u
    transkriptu. Zato se citat prvo razlomi na tri tačke, pa se svaki dio traži
    zasebno. Bez ovoga su valjane presude padale na NE.

    Prekratki odlomci (ispod 6 znakova) se preskaču — ne dokazuju ništa, a
    lako se slučajno poklope. Bar jedan dio mora biti pun citat (12+ znakova).
    """
    dijelovi = [_normalizuj(d) for d in re.split(r"\s*(?:\.\.\.|…)\s*", citat or "")]
    dijelovi = [d for d in dijelovi if len(d) >= 6]
    if not dijelovi or not any(len(d) >= 12 for d in dijelovi):
        return False
    return all(d in tn for d in dijelovi)


def provjeri_kriterije(sirovo, transkript, rub):
    """Provjerava presude ocjenjivača v2 i računa ocjenu iz njih.

    Model sudi, Python provjerava i broji. Svaki DA i DJELIMICNO mora nositi
    citat koji zaista stoji u transkriptu — bez njega presuda pada na NE, jer
    bi inače izmišljen dokaz nosio prave bodove. Isto vrijedi za prijavljene
    radnje: kazna od 0/10 ne smije se osloniti na rečenicu koje nema.

    Vraća rječnik u istom obliku koji čita ostatak aplikacije (anamneza,
    komunikacija, sigurnost, ukupna_ocjena, pohvale, smjernice), uz nova polja
    'kriteriji' i 'kazne_primijenjene' koja hrani ekran s dokazima.
    """
    import rubrika  # lokalno: ocjena.py ostaje upotrebljiv i bez rubrike

    if not isinstance(sirovo, dict):
        return None
    tn = _normalizuj(transkript)
    odbaceno = []

    kriteriji = {}
    for kid, presuda in (sirovo.get("kriteriji") or {}).items():
        kr, kat = rubrika.kriterij_po_id(rub, kid)
        if not kr:
            continue                      # model je izmislio kriterij
        status = (presuda or {}).get("status", "NE")
        citat = (presuda or {}).get("citat", "") or ""
        if status in ("DA", "DJELIMICNO") and not _ima_dokaz(citat, tn):
            odbaceno.append({"vrsta": "kriterij", "id": kid, "sadrzaj": presuda})
            status, citat = "NE", ""
        kriteriji[kid] = {
            "status": status,
            "citat": citat,
            "obrazlozenje": (presuda or {}).get("obrazlozenje", ""),
            "tekst": kr["tekst"],
            "bodovi": kr["bodovi"],
            "kategorija": kat["id"],
            "naziv_kategorije": kat["naziv"],
        }

    # Kriterij koji model uopste nije vratio ne smije tiho nestati sa ekrana.
    for kat in rub.get("kategorije", []):
        for kr in kat["kriteriji"]:
            kriteriji.setdefault(kr["id"], {
                "status": "NE", "citat": "", "obrazlozenje": "",
                "tekst": kr["tekst"], "bodovi": kr["bodovi"],
                "kategorija": kat["id"], "naziv_kategorije": kat["naziv"],
            })

    radnje = []
    for r in (sirovo.get("radnje") or []):
        if isinstance(r, dict) and _ima_dokaz(r.get("citat", ""), tn):
            radnje.append(r)
        else:
            odbaceno.append({"vrsta": "radnja", "sadrzaj": r})

    pohvale = []
    for p in (sirovo.get("pohvale") or []):
        if isinstance(p, dict) and _ima_dokaz(p.get("citat", ""), tn):
            pohvale.append(p)
        else:
            odbaceno.append({"vrsta": "pohvala", "sadrzaj": p})

    bodovi = rubrika.izracunaj(rub, kriteriji, [r["id"] for r in radnje])

    rezultat = {
        "verzija": 2,
        "pitanja_farmaceuta": sirovo.get("pitanja_farmaceuta") or [],
        "kriteriji": kriteriji,
        "radnje": radnje,
        "pohvale": pohvale,
        "smjernice": sirovo.get("smjernice") or [],
        "anamneza": bodovi.get("anamneza", 0),
        "komunikacija": bodovi.get("komunikacija", 0),
        "sigurnost": bodovi.get("sigurnost", 0),
        "ukupna_ocjena": bodovi.get("ukupna_ocjena", 0),
        "kazne_primijenjene": bodovi.get("kazne_primijenjene", []),
    }

    # Stari prikaz, zalbe i CSV izvoz citaju ova dva polja.
    propusteno = [k for k in kriteriji.values()
                  if k["status"] == "NE" and k["kategorija"] == "anamneza"]
    rezultat["nije_pitano"] = [{"pitanje": k["tekst"], "zasto_vazno": k["obrazlozenje"]}
                               for k in propusteno]
    rezultat["propustena_pitanja"] = [k["tekst"] for k in propusteno]

    if odbaceno:
        rezultat["odbaceno"] = odbaceno
    return rezultat


def izvuci_json(tekst):
    p, k = tekst.find("{"), tekst.rfind("}") + 1
    if p == -1 or k == 0:
        return None
    try:
        return json.loads(tekst[p:k])
    except Exception:
        return None
