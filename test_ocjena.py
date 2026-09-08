"""Testovi za provjeru ocjene — pokreću se bez API poziva i bez baze.

    python test_ocjena.py

Provjerava tri stvari koje su u reviziji baze od 8. 9. 2026. bile pokvarene:
odbacivanje tvrdnji bez dokaza, računanje ukupne ocjene u Pythonu umjesto u
modelu, i kompatibilnost sa starim zapisima u koloni result_json.
"""
import re
import sys

from ocjena import _normalizuj, provjeri_ocjenu

# Izmišljen razgovor, namjerno nije nijedan stvarni scenarij — repo je javan,
# pa test ne smije odati rješenje slučaja koji polaznici tek trebaju odigrati.
TRANSKRIPT = """Pacijent: Dobar dan. Trebam nešto za bolove u leđima, ukočio sam se.
Farmaceut: Dobar dan. Koliko dugo vas boli i da li uzimate još nešto od lijekova ili biljnih dodataka prehrani?
Pacijent: Boli me od jučer. Uzimam nešto za pritisak, to pijem godinama.
Farmaceut: Razumijem. Da li uzimate još nešto uz te tablete za pritisak?
Pacijent: Pa ne, šta bih drugo uzimao... samo te moje tablete."""

pao = []


def provjeri(naziv, uslov):
    print(("  OK   " if uslov else "  PAO  ") + naziv)
    if not uslov:
        pao.append(naziv)


print("\nprovjeri_ocjenu — dokazi")

r = provjeri_ocjenu({
    "anamneza": 5, "komunikacija": 5, "sigurnost": 5, "ukupna_ocjena": 9.9,
    "pohvale": [
        {"tekst": "Pitao je o trajanju tegobe", "citat": "Koliko dugo vas boli i da li uzimate još nešto"},
        {"tekst": "Bio je izuzetno empatičan", "citat": "razumijem koliko vam je teško, gospodine"},
    ],
    "pitano_ali_neodgovoreno": [
        {"pitanje": "Biljni dodaci", "citat_farmaceuta": "da li uzimate još nešto od lijekova ili biljnih dodataka prehrani",
         "reakcija_pacijenta": "porekao"},
        {"pitanje": "Boja mokraće", "citat_farmaceuta": "kakve je boje vaša mokraća", "reakcija_pacijenta": "porekao"},
    ],
    "nije_pitano": [{"pitanje": "Boja mokraće", "zasto_vazno": "alarm za rabdomiolizu"}],
}, TRANSKRIPT)

provjeri("pohvala s pravim citatom ostaje", len(r["pohvale"]) == 1)
provjeri("pohvala s izmišljenim citatom je odbačena",
         r["pohvale"][0]["tekst"] == "Pitao je o trajanju tegobe")
provjeri("stvarno postavljeno pitanje ostaje", len(r["pitano_ali_neodgovoreno"]) == 1)
provjeri("izmišljeno pitanje je odbačeno",
         r["pitano_ali_neodgovoreno"][0]["pitanje"] == "Biljni dodaci")
provjeri("odbačeno je sačuvano za admina", len(r.get("odbaceno", [])) == 2)

print("\nprovjeri_ocjenu — aritmetika")
provjeri("ukupna ocjena se preračunava, model se ne sluša", r["ukupna_ocjena"] == 5.0)

r2 = provjeri_ocjenu({"anamneza": 7, "komunikacija": 6, "sigurnost": 3, "ukupna_ocjena": 0}, TRANSKRIPT)
provjeri("7/6/3 daje 5.5", r2["ukupna_ocjena"] == 5.5)

r3 = provjeri_ocjenu({"anamneza": 2, "komunikacija": 3, "sigurnost": 0, "ukupna_ocjena": 99}, TRANSKRIPT)
provjeri("2/3/0 daje 1.7", r3["ukupna_ocjena"] == 1.7)

print("\nprovjeri_ocjenu — kompatibilnost")
provjeri("nije_pitano puni staro polje propustena_pitanja",
         r["propustena_pitanja"] == ["Boja mokraće"])

r4 = provjeri_ocjenu({
    "anamneza": 4, "komunikacija": 4, "sigurnost": 4,
    "pohvale": ["stari format, obična rečenica"],
    "propustena_pitanja": ["staro polje ostaje netaknuto"],
}, TRANSKRIPT)
provjeri("stari format pohvala prolazi bez dokaza", r4["pohvale"] == ["stari format, obična rečenica"])
provjeri("staro polje se ne prepisuje", r4["propustena_pitanja"] == ["staro polje ostaje netaknuto"])

print("\n_normalizuj")
provjeri("dijakritika se zanemaruje pri poređenju",
         _normalizuj("Šta kažete, mogu li?") == _normalizuj("sta kazete mogu li"))
provjeri("prekratak citat nije dokaz",
         provjeri_ocjenu({"pohvale": [{"tekst": "x", "citat": "Pa ne"}]}, TRANSKRIPT)["pohvale"] == [])

print()
if pao:
    print(f"PALO: {len(pao)}")
    sys.exit(1)
print("Svi testovi prolaze.")
