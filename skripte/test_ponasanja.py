"""Testni skup realizma pacijenta — pokreće se poslije svake izmjene priručnika.

    python skripte/test_ponasanja.py            # svi testovi
    python skripte/test_ponasanja.py 1 4        # samo odabrani

TROŠI API — jedan poziv po testu, oko 0,005 USD.

Ovo nisu unit testovi: model nije determinističan i sud je na čovjeku. Skripta
pokreće razgovor, ispisuje odgovor pacijenta i uz njega napiše šta se očekuje,
plus automatsku provjeru gdje je moguća (npr. da se pojavi riječ „Tribulus“).
"""
import os
import sys

sys.path.insert(0, os.getcwd())

from dotenv import load_dotenv                      # noqa: E402
from supabase import create_client                  # noqa: E402

load_dotenv(".env")
from konfig import MODEL_PACIJENT, ai               # noqa: E402
from motor import napravi_system_prompt             # noqa: E402

_db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


def scenarij(sid):
    r = _db.table("scenarios").select("*").eq("id", sid).execute()
    if not r.data:
        sys.exit(f"Scenarij {sid} nije u bazi.")
    return r.data[0]


# (broj, scenarij, opis, poruke farmaceuta redom, šta se očekuje, obavezan izraz)
TESTOVI = [
    (1, "scenarij_4", "Otkrivanje na drugo pitanje o dodacima",
     ["Dobar dan. Da li uzimate još nešto od lijekova ili biljnih dodataka prehrani?",
      "Pitam jer neki prirodni preparati mogu jako uticati na lijekove za srce. "
      "Ima li nešto što ste kupili van apoteke — kapsule, prašak, bilo šta?"],
     "Na drugo pitanje MORA priznati Tribulus. Prvo smije oklijevati.",
     ["tribulus", "kapsul", "sportsk", "prirodn"]),

    (2, "scenarij_4", "Rafal od četiri pitanja",
     ["Koliko dugo vas boli? Kakve je boje mokraća? Uzimate li statine? Bole li vas prsa?"],
     "Odgovara na najviše dva pitanja i kaže da ne stiže sve.", []),

    (3, "scenarij_3", "Žargon bez objašnjenja",
     ["Vjerovatno je riječ o antiholinergičkom efektu dekstrometorfana s midrijazom."],
     "Pacijentica s osnovnim obrazovanjem mora pitati šta to znači.", []),

    (4, "scenarij_3", "Otvoreno pitanje — pričljivost 4",
     ["Dobar dan. Kako se osjećate ovih dana?"],
     "Duži odgovor, 2–5 rečenica, smije skrenuti na svakodnevicu. NE otkriva očne simptome.",
     []),

    (5, "scenarij_1", "Otvoreno pitanje — pričljivost 2",
     ["Dobro jutro. Kako ste, kako se osjećate?"],
     "Kratak, zatvoren odgovor. Vidno kraći od testa 4.", []),

    (6, "scenarij_4", "Pitanje o podatku kojeg nema u činjenicama",
     ["Koliki vam je bio pritisak jutros kad ste mjerili?"],
     "Mora reći da ne zna ili da nije mjerio. NE smije izmisliti broj.", []),

    (7, "scenarij_4", "Osuđujući ton — osjetljiva činjenica ostaje skrivena",
     ["Kako ste mogli uzimati nešto sa strane a da nikom ne kažete?"],
     "Zatvara se, kraći odgovor. Ne mora priznati Tribulus na ovakvo pitanje.", []),

    (8, "scenarij_3", "Prihvatanje tuđe pretpostavke",
     ["Vidim da vas boli koljeno. Koliko dugo to traje?"],
     "MORA ispraviti farmaceuta — koljeno nije među njenim činjenicama.", []),
]


def pokreni(t):
    broj, sid, opis, poruke, ocekivano, izrazi = t
    sc = scenarij(sid)
    sistem = napravi_system_prompt(sc)

    historija = [{"role": "assistant", "content": sc["pocetna_poruka"]}]
    print(f"\n{'=' * 72}\nTEST {broj} · {sid} · {opis}")
    print(f"Očekivano: {ocekivano}\n")
    print(f"  Pacijent: {sc['pocetna_poruka']}")

    zadnji = ""
    for p in poruke:
        historija.append({"role": "user", "content": p})
        r = ai.messages.create(model=MODEL_PACIJENT, max_tokens=400,
                               system=sistem, messages=historija)
        zadnji = r.content[0].text
        historija.append({"role": "assistant", "content": zadnji})
        print(f"\n  Farmaceut: {p}")
        print(f"  Pacijent:  {zadnji}")

    print(f"\n  [duzina zadnjeg odgovora: {len(zadnji.split())} rijeci]")
    if izrazi:
        nasao = [i for i in izrazi if i.lower() in zadnji.lower()]
        if nasao:
            print(f"  AUTOMATSKA PROVJERA: PROSAO — nadjeno {nasao}")
        else:
            print(f"  AUTOMATSKA PROVJERA: PAO — nije nadjen nijedan od {izrazi}")
            return False
    return True


if __name__ == "__main__":
    trazeni = {int(a) for a in sys.argv[1:] if a.isdigit()}
    pali = []
    for t in TESTOVI:
        if trazeni and t[0] not in trazeni:
            continue
        if not pokreni(t):
            pali.append(t[0])
    print(f"\n{'=' * 72}")
    if pali:
        print(f"Automatska provjera pala za testove: {pali}")
    print("Ostale testove ocijeni sam — model nije determinističan.")
