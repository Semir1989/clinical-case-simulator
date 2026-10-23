"""Šta iz servera smije izaći prema telefonu — čist Python, bez baze i bez mreže.

U Streamlitu je sve živjelo na serveru samo po sebi. U Komunikatoru odgovor
API-ja vidi svako ko otvori devtools, pa se ovdje SVAKO polje navodi poimenično:
ono čega nema na popisu ne izlazi. Skrivene činjenice, okidači, otpor, rubrika,
očekivano savjetovanje, crvene zastavice i blok stanja nikad ne napuštaju server
dok je razgovor u toku. Epilog i ocjena po kriterijima izlaze tek kad je
pokušaj završen — isto kao u Streamlitu.

test_api.py provjerava da nijedan javni oblik ne nosi tajno polje.
"""
from datetime import date, datetime, timezone

from stanje import ISHODI, krivulja_povjerenja, razdvoji_didaskalije, zadnji_ishod

# Granica dužine jedne poruke farmaceuta. Do 23.10.2026 dužinu je posredno držao
# tajmer od 120 s po odgovoru, ali pod satom ljudi nisu stizali napisati ono što
# misle, a istek je jeo unose (5 od 22 partije). Mjereno na 136 poruka: medijan
# 116 znakova, 90% ispod 300, najduža 673 — 500 ne sputava skoro nikoga, a trošak
# po partiji ostaje praktično isti, jer ga drži broj unosa (MAX_POTEZA).
MAX_ZNAKOVA = 500


# ─── Članarina ───────────────────────────────────────────────────────────────

def clanarina_vazi(korisnik, danas=None):
    """Da li korisnik smije igrati. Admin nema rok; ostali moraju imati clan_do.

    Prazan clan_do znači da uplata nije utvrđena — takav nalog NE prolazi, jer je
    Komunikator samo za članove s plaćenom članarinom (odluka 15.10.2026).
    """
    if (korisnik or {}).get("role") == "admin":
        return True
    rok = (korisnik or {}).get("clan_do")
    if not rok:
        return False
    if isinstance(rok, str):
        rok = date.fromisoformat(rok[:10])
    return rok >= (danas or datetime.now(timezone.utc).date())


def javni_korisnik(k):
    return {
        "email": k.get("email", ""),
        "ime": k.get("full_name") or "",
        "nadimak": k.get("nadimak") or "",
        "uloga": k.get("role") or "korisnik",
        "clan_do": (str(k["clan_do"])[:10] if k.get("clan_do") else None),
        "obavijesti_email": k.get("obavijesti_email", True) is not False,
    }


# ─── Scenariji ───────────────────────────────────────────────────────────────

def javni_scenarij(sid, sc, zavrsen=False):
    """Kartica scenarija: samo ono što polaznik vidi PRIJE razgovora."""
    return {
        "id": sid,
        "naziv": sc.get("naziv", ""),
        "pacijent": sc.get("ime", ""),
        "godine": sc.get("godine"),
        "terapija": sc.get("terapija", ""),
        "razlog_posjete": sc.get("tegoba", ""),
        "podrucje": sc.get("podrucje") or "",
        "tezina": sc.get("tezina") or "",
        "zavrsen": bool(zavrsen),
    }


# ─── Razgovor u toku ─────────────────────────────────────────────────────────

def javna_replika(p):
    """Jedna replika: uloga + komadi govora i didaskalija. Blok stanja je već skinut."""
    uloga = "farmaceut" if p["role"] == "user" else "pacijent"
    if uloga == "farmaceut":
        return {"uloga": uloga, "komadi": [{"vrsta": "govor", "tekst": p["content"]}]}
    return {"uloga": uloga,
            "komadi": [{"vrsta": v, "tekst": t} for v, t in razdvoji_didaskalije(p["content"])]}


def javno_stanje(stanje, max_poteza):
    """Razgovor kakav polaznik smije vidjeti: replike i brojači, bez stanja pacijenta."""
    broj = int(stanje.get("broj_poteza") or 0)
    return {
        "replike": [javna_replika(p) for p in stanje.get("poruke_prikaz") or []],
        "broj_poteza": broj,
        "max_poteza": max_poteza,
        "preostalo": max(0, max_poteza - broj),
        "max_znakova": MAX_ZNAKOVA,
        "zavrseno": bool(stanje.get("zavrseno")),
        "moze_zavrsiti": broj >= 2 and not stanje.get("zavrseno"),
    }


# ─── Rezultat ────────────────────────────────────────────────────────────────

def javni_rezultat(rezultat, stanja=None, sc=None):
    """Povratna informacija poslije ispita — obavezno: dobro, loše, propušteno.

    Rezultati v2 nose kriterije s citatima; stariji (v1) samo pohvale,
    smjernice i propuštena pitanja, pa se popunjava ono što postoji.
    """
    r = rezultat or {}
    kriteriji = r.get("kriteriji") or {}
    citati_radnji = {x.get("id"): x.get("citat", "") for x in r.get("radnje") or []
                     if isinstance(x, dict)}

    if kriteriji:
        propusteno = [{"tekst": k.get("tekst", ""), "kategorija": k.get("naziv_kategorije", ""),
                       "zasto": k.get("obrazlozenje", "")}
                      for k in kriteriji.values() if k.get("status") == "NE"]
        djelimicno = [{"tekst": k.get("tekst", ""), "kategorija": k.get("naziv_kategorije", ""),
                       "citat": k.get("citat", ""), "zasto": k.get("obrazlozenje", "")}
                      for k in kriteriji.values() if k.get("status") == "DJELIMICNO"]
        kriteriji_javno = [{"tekst": k.get("tekst", ""), "kategorija": k.get("naziv_kategorije", ""),
                            "status": k.get("status", "NE"), "citat": k.get("citat", ""),
                            "obrazlozenje": k.get("obrazlozenje", ""), "bodovi": k.get("bodovi")}
                           for k in kriteriji.values()]
    else:
        propusteno = [{"tekst": t, "kategorija": "", "zasto": ""}
                      for t in r.get("propustena_pitanja") or []]
        djelimicno, kriteriji_javno = [], []

    lose = [{"opis": k.get("opis", ""), "najvise": k.get("max"),
             "citat": citati_radnji.get(k.get("id"), "")}
            for k in r.get("kazne_primijenjene") or [] if isinstance(k, dict)]

    stanja = stanja or []
    ishod = zadnji_ishod(stanja)
    sc = sc or {}
    return {
        "ocjena": {
            "ukupno": float(r.get("ukupna_ocjena") or 0),
            "anamneza": float(r.get("anamneza") or 0),
            "komunikacija": float(r.get("komunikacija") or 0),
            "sigurnost": float(r.get("sigurnost") or 0),
        },
        "dobro": [{"tekst": p.get("tekst", ""), "citat": p.get("citat", "")}
                  for p in r.get("pohvale") or [] if isinstance(p, dict)]
                 + [{"tekst": p, "citat": ""} for p in r.get("pohvale") or [] if isinstance(p, str)],
        "lose": lose,
        "propusteno": propusteno,
        "djelimicno": djelimicno,
        "smjernice": [s for s in r.get("smjernice") or [] if isinstance(s, str)],
        "kriteriji": kriteriji_javno,
        "ishod": ISHODI.get(ishod, "") if ishod else "",
        "povjerenje": krivulja_povjerenja(stanja),
        "epilog": sc.get("epilog") or "",
        "uzoran_razgovor": sc.get("uzoran_razgovor") or "",
    }


# ─── Ljestvica ───────────────────────────────────────────────────────────────

def javna_ljestvica(lista):
    """db_leaderboard vraća i email — na telefon ide samo nadimak i brojke."""
    return [{"mjesto": i + 1, "nadimak": x.get("ime", ""), "ukupno": x.get("ukupno", 0),
             "slucajeva": x.get("slucajeva", 0), "prosjek": x.get("prosjek", 0)}
            for i, x in enumerate(lista or [])]
