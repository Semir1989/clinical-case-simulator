"""Testovi za lozinke i uloge (F1) — bez baze i bez API poziva.

    python test_lozinke.py

Pokriva ono što se ne smije pokvariti pri prelasku na bcrypt: da se stara
SHA-256 lozinka i dalje prihvata (inače svi zatečeni korisnici ostaju vani),
da se prepozna kao ona koju treba migrirati, i da bcrypt hash prolazi bez
migracije.
"""
import hashlib
import secrets
import sys
from datetime import datetime, timezone

import bcrypt

from baza import (BROJ_PROMASAJA_ZA_ZAKLJUCAVANJE, ZAKLJUCAVANJE_MINUTA,
                  _minuta_do, hash_loz_bcrypt, je_admin, provjeri_lozinku)
from konfig import ADMIN_EMAIL


pao = []


def provjeri(naziv, uslov):
    print(("  OK   " if uslov else "  PAO  ") + naziv)
    if not uslov:
        pao.append(naziv)


print("\nStara SHA-256 lozinka")
stari = hashlib.sha256("tajna123".encode()).hexdigest()
tacna, migracija = provjeri_lozinku("tajna123", stari)
provjeri("tačna stara lozinka prolazi", tacna)
provjeri("označena je za migraciju", migracija)
tacna, _ = provjeri_lozinku("pogresna", stari)
provjeri("pogrešna lozinka pada", not tacna)

print("\nNovi bcrypt hash")
novi = hash_loz_bcrypt("tajna123")
provjeri("hash je bcrypt format", novi.startswith("$2"))
tacna, migracija = provjeri_lozinku("tajna123", novi)
provjeri("tačna lozinka prolazi", tacna)
provjeri("migracija se više ne traži", not migracija)
tacna, _ = provjeri_lozinku("pogresna", novi)
provjeri("pogrešna lozinka pada", not tacna)
provjeri("dva hasha iste lozinke se razlikuju (so radi)",
         hash_loz_bcrypt("tajna123") != hash_loz_bcrypt("tajna123"))

print("\nPokvareni i prazni hashevi")
tacna, _ = provjeri_lozinku("bilo sta", None)
provjeri("None hash ne ruši prijavu", not tacna)
tacna, _ = provjeri_lozinku("bilo sta", "")
provjeri("prazan hash ne ruši prijavu", not tacna)
tacna, _ = provjeri_lozinku("bilo sta", "$2b$nijevalidan")
provjeri("neispravan bcrypt hash ne ruši prijavu", not tacna)

print("\nZaključavanje")
provjeri("prag je 5 promašaja", BROJ_PROMASAJA_ZA_ZAKLJUCAVANJE == 5)
provjeri("zaključavanje traje 15 min", ZAKLJUCAVANJE_MINUTA == 15)
provjeri("prošlo vrijeme ne drži nalog zaključanim",
         _minuta_do("2020-01-01T00:00:00+00:00") == 0)
provjeri("nevažeći datum ne zaključava nalog zauvijek", _minuta_do("nesto") == 0)
provjeri("None ne ruši provjeru", _minuta_do(None) == 0)

print("\nUloge")
provjeri("admin po ulozi", je_admin({"email": "neko@x.ba", "role": "admin"}))
provjeri("admin po emailu i bez uloge", je_admin({"email": ADMIN_EMAIL}))
provjeri("mentor nije admin", not je_admin({"email": "m@x.ba", "role": "mentor"}))
provjeri("običan korisnik nije admin", not je_admin({"email": "k@x.ba", "role": "korisnik"}))
provjeri("korisnik bez uloge nije admin", not je_admin({"email": "k@x.ba"}))

print()
if pao:
    print(f"PALO: {len(pao)}")
    sys.exit(1)
print("Svi testovi prolaze.")
