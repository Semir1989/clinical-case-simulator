"""Testni skup za otpor, povjerenje i ishod (F4). TROSI API, oko 0,03 USD po toku.

    python skripte/test_otpor.py osudjujuci
    python skripte/test_otpor.py empatican
    python skripte/test_otpor.py fatalni

Pokrece cijeli razgovor i uz svaku repliku ispisuje skriveno stanje, da se vidi
da li povjerenje reaguje na nacin komunikacije i da li se prigovori povlace tek
kad je uslov popustanja ispunjen.
"""
import os, sys
sys.path.insert(0, os.getcwd())
from dotenv import load_dotenv
from supabase import create_client
load_dotenv(".env")
from motor import pozovi_pacijenta, zatvori_razgovor   # noqa: E402

_db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

TOKOVI = {
    "osudjujuci": ("scenarij_4", [
        "Kako ste mogli uzimati nesto sa strane a da nikom ne kazete?",
        "To je neodgovorno u vasim godinama. Uzimate li jos nesto?",
        "Ne mogu vam nista dati.",
    ]),
    "empatican": ("scenarij_4", [
        "Dobar dan. Vidim da vam je neugodno — hajde da vidimo sta se desava.",
        "Pitam vas ovo jer neki preparati koji se kupuju van apoteke mogu jako uticati na "
        "lijekove za srce. Ima li nesto sto ste poceli uzimati u zadnjih mjesec dana?",
        "Hvala sto ste mi rekli. To sto ste uzeli moze u kombinaciji s vasim lijekom za "
        "holesterol ostetiti misice, a to objasnjava zasto vas boli cijelo tijelo. Ne mogu vam "
        "dati nista protiv bolova jer bi to prikrilo problem — trebate danas na hitnu.",
        "Razumijem da vam se zuri, ali ovo je stvarno hitno. Prekinite te kapsule odmah.",
    ]),
    "fatalni": ("scenarij_4", [
        "Dobar dan, sta vas muci?",
        "Evo vam ibuprofen 400 mg, uzmite tri puta dnevno, proci ce.",
    ]),
}

def pokreni(ime):
    sid, poruke = TOKOVI[ime]
    sc = _db.table("scenarios").select("*").eq("id", sid).execute().data[0]
    hist = [{"role": "assistant", "content": sc["pocetna_poruka"]}]
    st = None
    print(f"\n{'='*74}\nTOK: {ime} ({sid})\n")
    print(f"  Pacijent: {sc['pocetna_poruka']}\n")
    for p in poruke:
        hist.append({"role": "user", "content": p})
        cist, st, sirovi = pozovi_pacijenta(hist, sc, st)
        hist.append({"role": "assistant", "content": sirovi})
        print(f"  Farmaceut: {p}")
        print(f"  Pacijent:  {cist}")
        if st:
            print(f"     [povjerenje {st['povjerenje']} · anksioznost {st['anksioznost']} · "
                  f"faza {st['faza']} · otkrio {st['otkriveno'] or '-'}]")
        print()
    cist, st, _ = zatvori_razgovor(hist, sc, st)
    print(f"  ZAVRSNA REPLIKA: {cist}")
    if st:
        print(f"     [povjerenje {st['povjerenje']} · ISHOD: {st['ishod'] or 'nije upisan'}]")

if __name__ == "__main__":
    for ime in (sys.argv[1:] or list(TOKOVI)):
        pokreni(ime)
