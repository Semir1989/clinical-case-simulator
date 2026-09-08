"""Testovi za rubriku v2 — parsiranje, izracun i kazne.

    python test_rubrika.py

Ne trosi API i ne dira bazu. Rubrike su namjerno skracene i izmisljene tamo
gdje je moguce — repo je javan, pa test ne smije odati rjesenje slucaja.
"""
import sys

import rubrika

TEKST_ZAREZ = """Ocijeni po ovim kategorijama (svaka 0-10):

ANAMNEZA (tezina 0.4): pitao trajanje tegobe(2), sta koristi i koliko dugo(2), trudnocu/stanja(2), alergije(2), prepoznao zastavice(2)
KAZNA: bez pitanja o trudnoci max 4/10; bez pitanja sta koristi max 6/10

KOMUNIKACIJA (tezina 0.3): jezik laika(2), empatija bez osudjivanja(2), provjerio razumijevanje(2), strukturisan razgovor(2), jasna poruka(2)

SIGURNOST (tezina 0.3): odbio Clobetasol bez recepta(3), savjetovao prekid oba preparata(3), nije predlozio zamjensku terapiju(2), uputio ljekaru(2)
KAZNA: dao kortikosteroid trudnici = 0/10 za Sigurnost"""

TEKST_CRTICE = """ANAMNEZA (tezina 0.4):
- Pitao za suplemente, biljna sredstva, preparate iz sportske prodavnice (2)
- Utvrdio vremenski slijed: kada poceo preparat, kada pocela bol (2)
KAZNA: bez pitanja o suplementima/biljnim preparatima max 4/10

SIGURNOST (tezina 0.3):
- Odbio preporuku OTC analgetika i uputio hitno na Urgentni centar (2)
KAZNA: preporuka simptomatske terapije bez pitanja o suplementima = max 3/10 za Sigurnost"""

pao = []


def provjeri(naziv, uslov):
    print(("  OK   " if uslov else "  PAO  ") + naziv)
    if not uslov:
        pao.append(naziv)


def sve(rub, status):
    return {kr["id"]: {"status": status, "citat": "x"}
            for kat in rub["kategorije"] for kr in kat["kriteriji"]}


print("\nparsiraj — oblici rubrike")

r = rubrika.parsiraj(TEKST_ZAREZ)
provjeri("zarez oblik daje tri kategorije",
         [k["id"] for k in r["kategorije"]] == ["anamneza", "komunikacija", "sigurnost"])
provjeri("svaka kategorija nosi tacno 10 bodova",
         all(sum(k["bodovi"] for k in kat["kriteriji"]) == 10 for kat in r["kategorije"]))
provjeri("tezine se citaju iz teksta",
         [k["tezina"] for k in r["kategorije"]] == [0.4, 0.3, 0.3])

rc = rubrika.parsiraj(TEKST_CRTICE)
provjeri("crtice oblik se parsira isto",
         [k["id"] for k in rc["kategorije"]] == ["anamneza", "sigurnost"])
provjeri("crtice: dva kriterija u anamnezi", len(rc["kategorije"][0]["kriteriji"]) == 2)

rz = rubrika.parsiraj(
    "ANAMNEZA (tezina 0.4): pitao o ocnim simptomima - mutan vid, krugovi oko svjetla(2)")
provjeri("zarez unutar kriterija ne lomi tekst",
         len(rz["kategorije"][0]["kriteriji"]) == 1
         and "krugovi oko svjetla" in rz["kategorije"][0]["kriteriji"][0]["tekst"])

provjeri("prazan tekst vraca None", rubrika.parsiraj("") is None)
provjeri("tekst bez kategorija vraca None", rubrika.parsiraj("nema ovdje nicega") is None)

provjeri("kazne se razvrstavaju na propust i radnju",
         [k["vrsta"] for k in r["kategorije"][0]["kazne"]] == ["propust", "propust"]
         and r["kategorije"][2]["kazne"][0]["vrsta"] == "radnja")

print("\nizracunaj — bodovanje")

o = rubrika.izracunaj(r, sve(r, "DA"))
provjeri("sve DA daje 10/10/10",
         (o["anamneza"], o["komunikacija"], o["sigurnost"]) == (10.0, 10.0, 10.0))
provjeri("sve DA daje ukupno 10.0", o["ukupna_ocjena"] == 10.0)
provjeri("sve DJELIMICNO nosi pola", rubrika.izracunaj(r, sve(r, "DJELIMICNO"))["anamneza"] == 5.0)
provjeri("nepoznat kriterij se broji kao NE", rubrika.izracunaj(r, {})["ukupna_ocjena"] == 0.0)

djelomicno = dict(sve(r, "NE"))
djelomicno.update({"anamneza_1": {"status": "DA"}, "anamneza_2": {"status": "DA"},
                   "anamneza_3": {"status": "DA"}, "komunikacija_1": {"status": "DA"}})
o = rubrika.izracunaj(r, djelomicno)
provjeri("anamneza 3 od 5 kriterija daje 6.0", o["anamneza"] == 6.0)
provjeri("ukupno je ponderisan zbir (6x0.4 + 2x0.3)", o["ukupna_ocjena"] == 3.0)

print("\nkazne — nalaz N2")

r1 = rubrika.za_scenarij({"rubrika": TEKST_ZAREZ}, "scenarij_1")

bez_trudnoce = dict(sve(r1, "DA"))
bez_trudnoce["anamneza_3"] = {"status": "NE"}
o = rubrika.izracunaj(r1, bez_trudnoce)
provjeri("kazna za propust spusta 8.0 na 4.0", o["anamneza"] == 4.0)
provjeri("primijenjena kazna se biljezi",
         any(k["id"] == "anamneza_kazna_1" for k in o["kazne_primijenjene"]))

o = rubrika.izracunaj(r1, sve(r1, "DA"))
provjeri("kazna NE gori kad je pitanje postavljeno", o["anamneza"] == 10.0)
provjeri("nijedna kazna nije primijenjena", o["kazne_primijenjene"] == [])

djelimicno_priznat = dict(sve(r1, "NE"))
djelimicno_priznat["anamneza_3"] = {"status": "DJELIMICNO"}
provjeri("i DJELIMICNO gasi kaznu",
         rubrika.izracunaj(r1, djelimicno_priznat)["kazne_primijenjene"] == [])

print("\nkazne — radnje")

bez_odbijanja = dict(sve(r1, "DA"))
bez_odbijanja["sigurnost_1"] = {"status": "NE"}
provjeri("bez prijave radnje sigurnost ostaje 7.0",
         rubrika.izracunaj(r1, bez_odbijanja)["sigurnost"] == 7.0)
provjeri("prijavljena radnja obara sigurnost na 0",
         rubrika.izracunaj(r1, bez_odbijanja, radnje=["sigurnost_kazna_1"])["sigurnost"] == 0.0)
provjeri("priznat kriterij pretegne nad prijavljenom radnjom",
         rubrika.izracunaj(r1, sve(r1, "DA"), radnje=["sigurnost_kazna_1"])["sigurnost"] == 10.0)

provjeri("rucna ispravka veze se primjenjuje",
         r1["kategorije"][2]["kazne"][0]["vezano_za"] == ["sigurnost_1"])

r4 = rubrika.za_scenarij({"rubrika": TEKST_CRTICE}, "scenarij_4")
suplementi_pitani = dict(sve(r4, "NE"))
suplementi_pitani["anamneza_1"] = {"status": "DA"}
provjeri("kazna iz Sigurnosti se gasi kriterijem iz Anamneze",
         rubrika.izracunaj(r4, suplementi_pitani,
                           radnje=["sigurnost_kazna_1"])["kazne_primijenjene"] == [])

siroka = rubrika.parsiraj("ANAMNEZA (tezina 0.4): pitao trajanje(2)\n"
                          "KAZNA: bez necega sasvim desetog max 1/10")
kazna = siroka["kategorije"][0]["kazne"][0]
provjeri("nepovezana kazna se oznaci za rucnu provjeru",
         kazna["vezano_za"] == [] and kazna["rucna_provjera"] is True)
provjeri("nepovezana kazna nikad ne gori",
         rubrika.izracunaj(siroka, {})["kazne_primijenjene"] == [])

print("\nshema_alata")

s = rubrika.shema_alata(r)
trazeni = s["properties"]["kriteriji"]["required"]
provjeri("shema trazi svih 14 kriterija poimenicno", len(trazeni) == 14)
provjeri("kriteriji nose imena iz rubrike",
         "anamneza_1" in trazeni and "sigurnost_4" in trazeni)
provjeri("status je zatvoren popis",
         s["properties"]["kriteriji"]["properties"]["anamneza_1"]["properties"]["status"]["enum"]
         == ["DA", "DJELIMICNO", "NE"])
provjeri("radnje nude samo kazne vrste radnja",
         s["properties"]["radnje"]["items"]["properties"]["id"]["enum"] == ["sigurnost_kazna_1"])
provjeri("bez radnji nema polja radnje",
         "radnje" not in rubrika.shema_alata(
             rubrika.parsiraj("ANAMNEZA (tezina 0.4): pitao trajanje(2)"))["properties"])
provjeri("shema ne trazi bodove ni ukupnu ocjenu od modela",
         "bodovi" not in str(s) and "ukupna_ocjena" not in str(s))

print()
if pao:
    print("PALO: %d" % len(pao))
    sys.exit(1)
print("Svi testovi prolaze.")
