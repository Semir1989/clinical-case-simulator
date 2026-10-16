"""Testovi Komunikator API-ja — bez baze, bez Anthropica, bez troška.

Pokretanje iz korijena repoa:
    venv/Scripts/python api/test_api.py

Najvažniji je test curenja: scenarij je napunjen tajnim oznakama (činjenice,
rubrika, crvene zastavice, očekivano, otpor, epilog, blok stanja), pa se
provjerava da se nijedna ne pojavi u odgovoru dok razgovor traje.
"""
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["KOMUNIKATOR_TAJNA"] = "test-tajna-samo-za-testove-0123456789"

from fastapi.testclient import TestClient  # noqa: E402

import api.main as m  # noqa: E402
from api.javno import TAJMER_SEKUNDI, clanarina_vazi, primijeni_tajmer  # noqa: E402

TAJNE = ["TAJNA_CINJENICA", "TAJNI_OKIDAC", "TAJNA_RUBRIKA", "TAJNA_ZASTAVICA",
         "TAJNO_OCEKIVANO", "TAJNI_DETALJ", "TAJNI_OTPOR", "TAJNI_EPILOG", "TAJNI_UZOR",
         "TAJNI_ID_CINJENICE", "<stanje"]

SC = {
    "naziv": "Test slučaj", "ime": "Amra", "godine": 33, "terapija": "sertralin",
    "tegoba": "lupanje srca", "pocetna_poruka": "Dobar dan.", "aktivan": True,
    "podrucje": "psihijatrija", "tezina": "tesko",
    "cinjenice": [{"id": "TAJNI_ID_CINJENICE", "cinjenica": "TAJNA_CINJENICA",
                   "okidac": "TAJNI_OKIDAC", "osjetljivo": True}],
    "rubrika": "TAJNA_RUBRIKA", "crvene_zastavice": "TAJNA_ZASTAVICA",
    "ocekivano": "TAJNO_OCEKIVANO", "skriveni_detalji": "TAJNI_DETALJ",
    "otpor": [{"id": "o1", "replika": "TAJNI_OTPOR"}], "persona": {"pricljivost": 3},
    "epilog": "TAJNI_EPILOG", "uzoran_razgovor": "TAJNI_UZOR",
}
DANAS = date.today()
KORISNICI = {
    "clan@test.ba": {"email": "clan@test.ba", "full_name": "Član", "approved": True,
                     "clan_do": str(DANAS + timedelta(days=30)), "role": "korisnik"},
    "istekao@test.ba": {"email": "istekao@test.ba", "approved": True,
                        "clan_do": str(DANAS - timedelta(days=1)), "role": "korisnik"},
    "bezroka@test.ba": {"email": "bezroka@test.ba", "approved": True, "clan_do": None},
    "neodobren@test.ba": {"email": "neodobren@test.ba", "approved": False,
                          "clan_do": str(DANAS + timedelta(days=30))},
}
NAPREDAK = {}
POKUSAJI = set()


def _lazni_pacijent(poruke, sc, prethodno=None, na_dio=None):
    sirovi = 'Pa [uzdahne] ne znam. <stanje povjerenje="6" otkriveno="TAJNI_ID_CINJENICE"/>'
    if na_dio:
        na_dio("Pa [uzdahne]")
        na_dio(sirovi.split("<")[0])
    return "Pa [uzdahne] ne znam.", {"povjerenje": 6, "otkriveno": ["TAJNI_ID_CINJENICE"],
                                     "faza": "ispitivanje", "ishod": ""}, sirovi


def _lazna_ocjena(stanje, sc, sid, mode, email):
    POKUSAJI.add((email, sid))
    stanje["zavrseno"] = True
    return {"ukupna_ocjena": 4.6, "anamneza": 5, "komunikacija": 4, "sigurnost": 5,
            "pohvale": [{"tekst": "Pitao o simptomu", "citat": "Kada"}],
            "smjernice": ["Pitaj o dodacima"],
            "kriteriji": {"k1": {"status": "NE", "tekst": "Pitao o biljnim preparatima",
                                 "naziv_kategorije": "Anamneza", "obrazlozenje": "ključno"}},
            "kazne_primijenjene": [], "radnje": [], "odbaceno": [{"interno": True}]}


m.db_korisnik = lambda e: KORISNICI.get(e)
m.osvjezi_scenarije = lambda: None
m.SCENARIJI.clear()
m.SCENARIJI["test_1"] = SC
m.db_zavrseni_scenariji = lambda e: {s for (x, s) in POKUSAJI if x == e}
m.db_vec_uradio = lambda e, s: (e, s) in POKUSAJI
m.db_ucitaj_napredak = lambda e, s, mode: json.loads(json.dumps(NAPREDAK[(e, s)])) if (e, s) in NAPREDAK else None
m.db_spremi_napredak = lambda e, s, st, mode: NAPREDAK.__setitem__((e, s), json.loads(json.dumps(st)))
m.db_obrisi_napredak = lambda e, s, mode: NAPREDAK.pop((e, s), None)
m.db_log_upotrebu = lambda *a, **k: None
m.db_poruka_danas = lambda e: 0
m.pozovi_pacijenta_stream = _lazni_pacijent
m.zatvori_razgovor = lambda p, sc, z=None: ("Hvala, idem ljekaru.", z, "Hvala, idem ljekaru.")
m.ocijeni_razgovor = _lazna_ocjena
PQ_POZIVI = []
m.javi_pharma_questu = lambda e, r, sc, sid: PQ_POZIVI.append((e, r["ukupna_ocjena"], sid))

klijent = TestClient(m.app)
greske = []


def provjeri(uslov, opis):
    print(("  OK   " if uslov else "  PAO  ") + opis)
    if not uslov:
        greske.append(opis)


def zaglavlje(email):
    return {"Authorization": "Bearer " + m.napravi_token(email)}


def bez_tajni(tekst, opis):
    nadjene = [t for t in TAJNE if t in tekst]
    provjeri(not nadjene, f"{opis} ne nosi tajne{(' — NAĐENO: ' + ', '.join(nadjene)) if nadjene else ''}")


print("Članarina i pristup")
provjeri(clanarina_vazi({"role": "admin"}), "admin nema rok")
provjeri(not clanarina_vazi({"clan_do": None}), "prazan rok ne prolazi")
provjeri(clanarina_vazi({"clan_do": str(DANAS)}, DANAS), "rok važi uključno s današnjim danom")
provjeri(klijent.get("/scenariji").status_code == 401, "bez tokena → 401")
provjeri(klijent.get("/scenariji", headers={"Authorization": "Bearer pokvaren"}).status_code == 401,
         "pokvaren token → 401")
for email in ("istekao@test.ba", "bezroka@test.ba", "neodobren@test.ba"):
    provjeri(klijent.get("/scenariji", headers=zaglavlje(email)).status_code == 403,
             f"{email} → 403 iako ima važeći token")

print("Tajmer")
s = {"broj_poteza": 1, "zadnji_potez_vrijeme": 1000.0}
provjeri(primijeni_tajmer(s, 7, 1000.0 + 2 * TAJMER_SEKUNDI + 5) == 2 and s["broj_poteza"] == 3,
         "dva istekla roka oduzimaju dva poteza")
s = {"broj_poteza": 6, "zadnji_potez_vrijeme": 0.0}
provjeri(primijeni_tajmer(s, 7, 10 * TAJMER_SEKUNDI) == 1 and s["broj_poteza"] == 7,
         "ne oduzima više poteza nego što je ostalo")

print("Razgovor bez curenja")
h = zaglavlje("clan@test.ba")
r = klijent.get("/scenariji", headers=h)
provjeri(r.status_code == 200 and r.json()["scenariji"][0]["id"] == "test_1", "lista scenarija")
bez_tajni(r.text, "lista scenarija")
r = klijent.post("/scenariji/test_1/pocni", headers=h)
provjeri(r.status_code == 200 and not r.json()["vraceno"], "početak razgovora")
bez_tajni(r.text, "početak razgovora")
provjeri(klijent.post("/scenariji/test_1/zavrsi", headers=h).status_code == 400,
         "završetak prije drugog unosa je odbijen")
for i in range(2):
    r = klijent.post("/scenariji/test_1/poruka", headers=h, json={"tekst": f"Pitanje {i}"})
    provjeri(r.status_code == 200 and "event: stanje" in r.text, f"poruka {i + 1} dobija stanje")
    bez_tajni(r.text, f"tok poruke {i + 1}")
provjeri('"vrsta": "didaskalija"' in r.text, "didaskalija je izdvojena iz govora")
r = klijent.post("/scenariji/test_1/pocni", headers=h)
provjeri(r.json()["vraceno"] and r.json()["razgovor"]["broj_poteza"] == 2, "nastavak prekinutog razgovora")
bez_tajni(r.text, "nastavak razgovora")

print("Istek vremena")
r = klijent.post("/scenariji/test_1/istek", headers=h)
provjeri(r.status_code == 200 and "razgovor" in r.json() and r.json()["razgovor"]["broj_poteza"] == 2,
         "istek prije roka ne ocjenjuje i ne mijenja razgovor")
provjeri(len(NAPREDAK[("clan@test.ba", "test_1")]["poruke_prikaz"]) == 5, "istek ne upisuje poruku")

print("Ocjena i jednokratnost")
r = klijent.post("/scenariji/test_1/zavrsi", headers=h)
j = r.json()
provjeri(r.status_code == 200 and j["ocjena"]["ukupno"] == 4.6, "ocjena stiže")
provjeri(j["dobro"] and j["propusteno"] and "lose" in j and j["smjernice"],
         "povratna informacija: dobro, loše, propušteno, smjernice")
provjeri("odbaceno" not in r.text, "interna polja ocjenjivača ne izlaze")
provjeri(j["epilog"] == "TAJNI_EPILOG", "epilog izlazi tek poslije ocjene")
provjeri(PQ_POZIVI == [("clan@test.ba", 4.6, "test_1")], "ocjena je javljena Pharma Questu")
provjeri(klijent.post("/scenariji/test_1/pocni", headers=h).status_code == 409, "drugi pokušaj je odbijen")
provjeri(klijent.post("/scenariji/test_1/poruka", headers=h, json={"tekst": "x"}).status_code == 409,
         "poruka poslije ocjene je odbijena")

print("Istek svih unosa")
m.SCENARIJI["test_2"] = SC
klijent.post("/scenariji/test_2/pocni", headers=h)
NAPREDAK[("clan@test.ba", "test_2")]["zadnji_potez_vrijeme"] = 1000.0     # davno
r = klijent.post("/scenariji/test_2/istek", headers=h)
provjeri(r.status_code == 200 and r.json().get("rezultat", {}).get("ocjena", {}).get("ukupno") == 4.6,
         "istek svih unosa ocjenjuje i bez ijedne poruke")
provjeri(not any(p["role"] == "user" for p in NAPREDAK.get(("clan@test.ba", "test_2"), {}).get("poruke_prikaz", [])),
         "istek ne dodaje poruku farmaceuta")
bez_tajni(json.dumps(r.json()).replace("TAJNI_EPILOG", "").replace("TAJNI_UZOR", ""), "rezultat isteka (bez epiloga)")

print("Ljestvica")
m.db_leaderboard = lambda p: [{"email": "tajni@mail.ba", "ime": "Farmaceut71", "ukupno": 9, "slucajeva": 2, "prosjek": 4.5}]
r = klijent.get("/ljestvica", headers=h)
provjeri("tajni@mail.ba" not in r.text and "Farmaceut71" in r.text, "ljestvica bez emaila, samo nadimak")

print("Obavijesti o novom slučaju")
KORISNICI["admin@test.ba"] = {"email": "admin@test.ba", "approved": True, "role": "admin"}
SVI = list(KORISNICI.values()) + [
    {"email": "iskljucio@test.ba", "approved": True, "clan_do": str(DANAS + timedelta(days=9)), "obavijesti_email": False}]
m.db_korisnici_za_obavijest = lambda: [u for u in SVI if u.get("approved") and u.get("obavijesti_email", True)]
POSLANO_OBAV, OZNAKE = [], {}
m.posalji_emailove_skupno = lambda poruke: (POSLANO_OBAV.extend(poruke) or len(poruke), [])
m.db_scenariji_obavijesti = lambda: dict(OZNAKE)
m.db_oznaci_obavijest = lambda sid, kada: OZNAKE.__setitem__(sid, kada)
ha = zaglavlje("admin@test.ba")
provjeri(klijent.get("/admin/obavijesti", headers=h).status_code == 403, "član ne vidi admin obavijesti")
r = klijent.get("/admin/obavijesti/test_1", headers=ha)
provjeri(r.status_code == 200 and r.json()["primalaca"] == 1, "pregled: samo član s važećom članarinom")
bez_tajni(r.text, "pregled obavijesti")
r = klijent.post("/admin/obavijesti/test_1", headers=ha, json={})
provjeri(r.status_code == 200 and [p["to"] for p in POSLANO_OBAV] == ["clan@test.ba"],
         "šalje se samo važećim članovima (ne istekao, bez roka, neodobren, isključio, admin)")
provjeri(klijent.post("/admin/obavijesti/test_1", headers=ha, json={}).status_code == 409,
         "druga obavijest za isti slučaj traži izričito ponovno slanje")
provjeri(klijent.post("/ja/obavijesti", headers=h, json={"email": False}).status_code in (200, 500),
         "postavka obavijesti postoji")

print()
print("SVE PROŠLO" if not greske else f"PALO: {len(greske)}")
sys.exit(1 if greske else 0)
