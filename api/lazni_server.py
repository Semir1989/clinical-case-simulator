"""Lokalni API s lažnom bazom i lažnim pacijentom — za ručnu provjeru ekrana
Komunikatora bez Supabasea, bez Anthropica i bez troška.

    venv/Scripts/python api/lazni_server.py        # sluša na :8000, ispiše token

Pa u komunikator/: VITE_API_URL=http://localhost:8000 npx vite --port 5173,
i u konzoli browsera: localStorage.setItem('komunikator.token', '<token>').
Pravi api/main.py se ne mijenja — ovdje se samo podmeću funkcije baze i modela,
isto kao u test_api.py. Ne ide u Docker sliku (Dockerfile kopira fajlove poimenično).
"""
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["KOMUNIKATOR_TAJNA"] = "lokalna-tajna-samo-za-lazni-server-0123456789"

import uvicorn  # noqa: E402

import api.main as m  # noqa: E402

EMAIL = "clan@test.ba"
KORISNIK = {"email": EMAIL, "full_name": "Amela Testić", "nadimak": "Farmaceutka7",
            "approved": True, "role": "korisnik", "clan_do": str(date.today() + timedelta(days=200))}

SC = {
    "naziv": "Lupanje srca i biljni čaj", "ime": "Amra", "godine": 33, "terapija": "sertralin 50 mg",
    "tegoba": "lupanje srca već sedmicu", "pocetna_poruka": "Dobar dan. [nervozno gleda oko sebe] Imate li nešto za smirenje?",
    "aktivan": True, "podrucje": "mentalno_zdravlje", "tezina": "tesko",
    "epilog": "Amra je otišla ljekaru porodične medicine. **Kantarion** je ukinut, a lupanje je prestalo za *pet dana*.",
    "uzoran_razgovor": "Farmaceut: Kada se javlja lupanje?\nPacijent: [uzdahne] Od prošle sedmice.\nFarmaceut: Pijete li još nešto, i čajeve?\nPacijent: Pa pijem kantarion.",
}
SC2 = dict(SC, naziv="Kašalj kod starije osobe", ime="Mujo", godine=78, podrucje="geriatrija", tezina="ekspertno")
m.SCENARIJI.clear()
m.SCENARIJI.update({"scenarij_1": SC, "scenarij_2": SC2})
m.osvjezi_scenarije = lambda: None

NAPREDAK, POKUSAJI = {}, {}
REZ = {"ukupna_ocjena": 6.4, "anamneza": 7, "komunikacija": 6.5, "sigurnost": 5,
       "pohvale": [{"tekst": "Pitali ste o simptomu prije preporuke", "citat": "Kada se javlja lupanje?"}],
       "smjernice": ["Pitajte za **biljne preparate** odvojeno — pacijenti ih ne smatraju lijekovima."],
       "kazne_primijenjene": [{"id": "k1", "opis": "Preporučen preparat prije pune anamneze", "max": 5}],
       "radnje": [{"id": "k1", "citat": "Uzmite valerijanu"}],
       "kriteriji": {
           "a1": {"status": "DA", "tekst": "Pitao o trajanju simptoma", "naziv_kategorije": "Anamneza", "citat": "Kada se javlja lupanje?", "obrazlozenje": "Jasno pitanje."},
           "a2": {"status": "NE", "tekst": "Pitao o biljnim preparatima", "naziv_kategorije": "Anamneza", "obrazlozenje": "Kantarion je ključ slučaja."},
           "k1": {"status": "DJELIMICNO", "tekst": "Objasnio zašto pita", "naziv_kategorije": "Komunikacija", "citat": "Pitam zbog terapije", "obrazlozenje": "Samo jednom."}}}


def _pokusaj(email, sid, mode=None):
    return POKUSAJI.get((email, sid))


m.db_korisnik = lambda e: KORISNIK if e == EMAIL else None
m.db_login = lambda e, l: (KORISNIK, "") if e == EMAIL and l == "lozinka1" else (None, "Pogrešan email ili lozinka.")
m.db_zavrseni_scenariji = lambda e: {s for (x, s) in POKUSAJI if x == e}
m.db_vec_uradio = lambda e, s: (e, s) in POKUSAJI
m.db_ucitaj_napredak = lambda e, s, mode: json.loads(json.dumps(NAPREDAK[(e, s)])) if (e, s) in NAPREDAK else None
m.db_spremi_napredak = lambda e, s, st, mode: NAPREDAK.__setitem__((e, s), json.loads(json.dumps(st)))
m.db_obrisi_napredak = lambda e, s, mode: NAPREDAK.pop((e, s), None)
m.db_log_upotrebu = lambda *a, **k: None
m.db_poruka_danas = lambda e: 0
m.db_pokusaj = _pokusaj
m.db_leaderboard = lambda p: [
    {"email": "x@y", "ime": "Apotekar22", "ukupno": 17.2, "slucajeva": 3, "prosjek": 5.73},
    {"email": EMAIL, "ime": "Farmaceutka7", "ukupno": 6.4, "slucajeva": 1, "prosjek": 6.4}]
m.db_moji_rezultati = lambda e: [{"id": p["id"], "scenario_id": s, "score": p["score"], "mode": "ispit",
                                  "completed_at": p["completed_at"], "appeal_status": p["appeal_status"]}
                                 for (x, s), p in POKUSAJI.items() if x == e]


def _zalba(pid, tekst):
    for p in POKUSAJI.values():
        if p["id"] == pid:
            p.update(appeal_status="otvorena", appeal_text=tekst)
    return True, ""


m.db_posalji_zalbu = _zalba


def _pacijent(poruke, sc, prethodno=None, na_dio=None):
    odg = "[zastane] Pa... pijem i neki čaj od kantariona, sestra mi ga dala. Je li to bitno?"
    for i in range(1, len(odg) + 1, 4):
        time.sleep(0.04)
        if na_dio:
            na_dio(odg[:i])
    n = len([p for p in poruke if p["role"] == "user"])
    return odg, {"povjerenje": min(9, 4 + n), "faza": "ispitivanje", "ishod": ""}, odg + ' <stanje povjerenje="6"/>'


def _ocijeni(stanje, sc, sid, mode, email):
    time.sleep(3)
    transkript = "\n".join(f"{'Farmaceut' if p['role'] == 'user' else 'Pacijent'}: {p['content']}"
                           for p in stanje["poruke_prikaz"])
    POKUSAJI[(email, sid)] = {"id": f"pok-{sid}", "score": REZ["ukupna_ocjena"], "result_json": json.dumps(REZ),
                              "transcript": transkript, "stanje_json": stanje.get("stanja"),
                              "completed_at": datetime.now(timezone.utc).isoformat(),
                              "appeal_status": None, "appeal_text": None, "appeal_response": None}
    stanje["zavrseno"] = True
    return REZ


m.pozovi_pacijenta_stream = _pacijent
m.zatvori_razgovor = lambda p, sc, z=None: ("[klimne] Hvala, otići ću ljekaru.", z, "Hvala, otići ću ljekaru.")
m.ocijeni_razgovor = _ocijeni

if __name__ == "__main__":
    print("TOKEN:", m.napravi_token(EMAIL), flush=True)
    print("Prijava: clan@test.ba / lozinka1", flush=True)
    uvicorn.run(m.app, host="127.0.0.1", port=8000, log_level="warning")
