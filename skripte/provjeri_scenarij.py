# -*- coding: utf-8 -*-
"""Provjerava generisani scenarij prema standardu scenarij_v2.

    venv/Scripts/python skripte/provjeri_scenarij.py scenario/generisani/scenarij_5.json

Ne trosi API i ne dira bazu. Vraca izlazni kod 1 ako scenarij nije ispravan, pa
ga upsert_scenarij.py moze zvati kao branu prije upisa.

Postoji jer se greske u rubrici ne vide dok neko ne odigra scenarij: kriterij
koji ne zavrsava brojem u zagradi parser tiho preskoci, a kazna koja ne spominje
rijeci iz svog kriterija nikad se ne upali. Oboje izgleda ispravno u JSON-u.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.getcwd())
import rubrika  # noqa: E402

PODRUCJA = ("trudnoca_dojenje", "kardio_interakcije", "geriatrija", "mentalno_zdravlje",
            "pedijatrija", "otc_zloupotreba", "dermatologija")
TEZINE = ("tesko", "ekspertno")

OBAVEZNA = ("id", "naziv", "ime", "godine", "tegoba", "terapija", "pocetna_poruka",
            "crvene_zastavice", "ocekivano", "rubrika", "podrucje", "tezina")

greske, upozorenja = [], []


def greska(tekst):
    greske.append(tekst)


def upozori(tekst):
    upozorenja.append(tekst)


def provjeri_osnovno(sc):
    for polje in OBAVEZNA:
        if not sc.get(polje):
            greska(f"nedostaje obavezno polje: {polje}")
    if sc.get("podrucje") and sc["podrucje"] not in PODRUCJA:
        greska(f"podrucje '{sc['podrucje']}' nije iz popisa: {', '.join(PODRUCJA)}")
    if sc.get("tezina") and sc["tezina"] not in TEZINE:
        greska(f"tezina '{sc['tezina']}' nije 'tesko' ni 'ekspertno'")
    if sc.get("epilog") or sc.get("uzoran_razgovor"):
        upozori("epilog i uzoran_razgovor se generisu iz admin panela, ne pisu rucno")


def provjeri_cinjenice(sc):
    cinjenice = sc.get("cinjenice")
    if not cinjenice:
        greska("nema 'cinjenice' — scenarij bez okidaca je stari oblik, vidi SCENARIJ-V2.md")
        return
    if not 6 <= len(cinjenice) <= 10:
        upozori(f"{len(cinjenice)} cinjenica; standard trazi 6-10")

    oznake = set()
    for i, c in enumerate(cinjenice, 1):
        for polje in ("id", "cinjenica", "okidac"):
            if not c.get(polje):
                greska(f"cinjenica {i}: nedostaje '{polje}'")
        oznaka = c.get("id", "")
        if oznaka in oznake:
            greska(f"cinjenica {i}: oznaka '{oznaka}' se ponavlja")
        oznake.add(oznaka)
        if oznaka != oznaka.lower() or " " in oznaka:
            greska(f"cinjenica {i}: oznaka '{oznaka}' mora biti mala slova bez razmaka")
        if "osjetljivo" not in c:
            greska(f"cinjenica {i}: nedostaje 'osjetljivo' (true/false)")

    osjetljivih = sum(1 for c in cinjenice if c.get("osjetljivo"))
    if osjetljivih < 2:
        greska(f"samo {osjetljivih} osjetljiva cinjenica; standard trazi najmanje 2")


def provjeri_personu(sc):
    p = sc.get("persona")
    if not p:
        greska("nema 'persona' — pacijent bez licnosti govori kao udzbenik")
        return
    pric = p.get("pricljivost")
    if not isinstance(pric, int) or not 1 <= pric <= 5:
        greska(f"persona.pricljivost mora biti cijeli broj 1-5, a jeste: {pric!r}")
    for polje in ("obrazovanje", "raspolozenje"):
        if not p.get(polje):
            greska(f"persona: nedostaje '{polje}'")


def provjeri_otpor(sc):
    otpor = sc.get("otpor")
    if not otpor:
        greska("nema 'otpor' — pacijent koji ne prigovara popusti na prvu rijec")
        return
    redovi = [o.get("redoslijed") for o in otpor]
    if sorted(redovi) != list(range(1, len(otpor) + 1)):
        greska(f"otpor: redoslijed mora ici 1..{len(otpor)}, a jeste {redovi}")
    for i, o in enumerate(otpor, 1):
        if not o.get("replika"):
            greska(f"otpor {i}: nedostaje 'replika'")
        if not o.get("fatalno_ako_izda") and not o.get("uslov_popustanja"):
            greska(f"otpor {i}: prigovor koji nije fatalan mora imati 'uslov_popustanja'")


def provjeri_rubriku(sc):
    tekst = sc.get("rubrika") or ""
    rub = rubrika.parsiraj(tekst)
    if not rub:
        greska("rubrika se ne moze rasclaniti — provjeri format u SCENARIJ-V2.md")
        return

    imena = [k["id"] for k in rub["kategorije"]]
    if imena != ["anamneza", "komunikacija", "sigurnost"]:
        greska(f"rubrika mora imati sve tri kategorije, a ima: {imena}")

    for kat in rub["kategorije"]:
        zbir = sum(k["bodovi"] for k in kat["kriteriji"])
        if zbir != 10:
            greska(f"rubrika/{kat['id']}: bodovi daju {zbir:g}, a moraju 10 "
                   f"({len(kat['kriteriji'])} kriterija)")
        for kr in kat["kriteriji"]:
            if len(kr["tekst"]) < 8:
                greska(f"rubrika/{kr['id']}: opis '{kr['tekst']}' je prekratak da bi se sudio")

    kazne = [kz for kat in rub["kategorije"] for kz in kat["kazne"]]
    if not kazne:
        greska("rubrika nema nijednu kaznu — trazi se bar fatalna greska u Sigurnosti")
    for kz in kazne:
        if kz.get("rucna_provjera"):
            greska(f"kazna '{kz['opis']}' se ne veze ni za jedan kriterij, pa se nikad "
                   f"nece upaliti; prepisi je rijecima iz kriterija na koji se odnosi")

    fatalna = [kz for kz in kazne if kz["max"] == 0]
    if not fatalna:
        greska("nema fatalne greske (kazna '= 0/10') — svaki slucaj mora imati jednu")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    put = sys.argv[1]
    if not os.path.exists(put):
        sys.exit(f"Nema fajla: {put}")
    with io.open(put, encoding="utf-8") as f:
        sc = json.load(f)

    provjeri_osnovno(sc)
    provjeri_cinjenice(sc)
    provjeri_personu(sc)
    provjeri_otpor(sc)
    provjeri_rubriku(sc)

    print(f"\n{sc.get('id', '?')} — {sc.get('naziv', '')}")
    for u in upozorenja:
        print(f"  upozorenje: {u}")
    if greske:
        print(f"\n  NEISPRAVNO — {len(greske)} greska/e:")
        for g in greske:
            print(f"    · {g}")
        print("\n  Popravi pa pokreni ponovo. Upis u bazu se ne radi dok ovo ne prolazi.")
        sys.exit(1)
    print("  Ispravno po standardu scenarij_v2.")


if __name__ == "__main__":
    main()
