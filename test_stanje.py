"""Testovi za skriveno stanje i didaskalije (F4) — bez API poziva i bez baze.

    python test_stanje.py

Najosjetljivije mjesto je izostanak bloka stanja: model ga ponekad ispusti.
Tada se mora zadržati prethodno stanje — nagli pad povjerenja bez ijednog
razloga u razgovoru je gora greška od zadržanog stanja.
"""
import sys

from stanje import (izdvoji_stanje, krivulja_povjerenja, razdvoji_didaskalije,
                    sazetak_za_evaluatora, sve_otkriveno, zadnji_ishod)

pao = []


def provjeri(naziv, uslov):
    print(("  OK   " if uslov else "  PAO  ") + naziv)
    if not uslov:
        pao.append(naziv)


print("\nIzdvajanje bloka stanja")
t, s = izdvoji_stanje(
    'Pa uzimam neke kapsule, kupio sam ih u sportskoj prodavnici.\n'
    '<stanje povjerenje="6" anksioznost="4" faza="ispitivanje" otkriveno="tribulus" ishod=""/>')
provjeri("blok je uklonjen iz teksta", "<stanje" not in t)
provjeri("govor je ostao netaknut", t.startswith("Pa uzimam neke kapsule"))
provjeri("povjerenje je pročitano", s["povjerenje"] == 6)
provjeri("anksioznost je pročitana", s["anksioznost"] == 4)
provjeri("faza je pročitana", s["faza"] == "ispitivanje")
provjeri("otkrivene činjenice su pročitane", s["otkriveno"] == ["tribulus"])
provjeri("prazan ishod ostaje prazan", s["ishod"] == "")

t, s = izdvoji_stanje('Idem ja ljekaru odmah. <stanje povjerenje="8" anksioznost="6" '
                      'faza="zatvaranje" otkriveno="a;b;c" ishod="prihvatio"/>')
provjeri("više činjenica se razdvaja", s["otkriveno"] == ["a", "b", "c"])
provjeri("ishod je pročitan", s["ishod"] == "prihvatio")

print("\nKad blok fali")
prethodno = {"povjerenje": 7, "anksioznost": 3, "faza": "savjet", "otkriveno": ["x"], "ishod": ""}
t, s = izdvoji_stanje("Replika bez bloka stanja.", prethodno)
provjeri("tekst prolazi netaknut", t == "Replika bez bloka stanja.")
provjeri("zadržava se prethodno povjerenje", s["povjerenje"] == 7)
provjeri("ne pada na nulu", s["povjerenje"] != 0)
t, s = izdvoji_stanje("Bez bloka i bez prethodnog.", None)
provjeri("bez prethodnog vraća None umjesto izmišljenog stanja", s is None)

print("\nPokvarene vrijednosti")
_, s = izdvoji_stanje('X <stanje povjerenje="devet" anksioznost="99" faza="izmisljena" ishod="ok"/>')
provjeri("nebrojiva vrijednost pada na zadano", s["povjerenje"] == 5)
provjeri("vrijednost iznad 10 se odsijeca", s["anksioznost"] == 10)
provjeri("nepoznata faza se odbacuje", s["faza"] == "otvaranje")
provjeri("nepoznat ishod se odbacuje", s["ishod"] == "")
_, s = izdvoji_stanje('X <stanje povjerenje="-3"/>')
provjeri("negativna vrijednost se odsijeca na 0", s["povjerenje"] == 0)

print("\nSažimanje razgovora")
stanja = [
    {"povjerenje": 5, "otkriveno": ["a"], "ishod": ""},
    {"povjerenje": 4, "otkriveno": ["a", "b"], "ishod": ""},
    {"povjerenje": 7, "otkriveno": ["c"], "ishod": "prihvatio"},
]
provjeri("krivulja povjerenja", krivulja_povjerenja(stanja) == [5, 4, 7])
provjeri("otkriveno bez ponavljanja, redom", sve_otkriveno(stanja) == ["a", "b", "c"])
provjeri("zadnji ishod", zadnji_ishod(stanja) == "prihvatio")
provjeri("prazna lista ne ruši", sve_otkriveno([]) == [] and zadnji_ishod(None) == "")

sazetak = sazetak_za_evaluatora(stanja, [{"id": "a", "cinjenica": "prva"},
                                         {"id": "d", "cinjenica": "cetvrta"}])
provjeri("sažetak nosi krivulju", "5 → 4 → 7" in sazetak)
provjeri("izmišljeni id se ne broji", "otkriveno 1 od 2" in sazetak)
provjeri("sažetak imenuje neotkriveno", "cetvrta" in sazetak)
provjeri("sažetak nosi ishod", "Prihvatio savjet" in sazetak)
provjeri("bez stanja nema sažetka", sazetak_za_evaluatora([], None) == "")

print("\nDidaskalije")
k = razdvoji_didaskalije("[žmirka na svjetlo] Ma dobro je, samo mi dajte to.")
provjeri("didaskalija je prepoznata", k[0] == ("didaskalija", "žmirka na svjetlo"))
provjeri("govor je odvojen", k[1] == ("govor", "Ma dobro je, samo mi dajte to."))
k = razdvoji_didaskalije("Ne znam. [spusti glas] Uzimam nešto sa strane.")
provjeri("didaskalija usred replike", len(k) == 3 and k[1][0] == "didaskalija")
provjeri("tekst bez didaskalija ostaje jedan komad",
         razdvoji_didaskalije("Obična replika.") == [("govor", "Obična replika.")])
provjeri("prazan tekst ne ruši", razdvoji_didaskalije("") == [])

print()
if pao:
    print(f"PALO: {len(pao)}")
    sys.exit(1)
print("Svi testovi prolaze.")
