"""Izvlači transkripte iz baze u kalibracija/referenca.json.

    python kalibracija/izvuci_referencu.py

Pokreće se iz korijena projekta. Uzima pokušaje jednog korisnika (zadano: admin)
koji imaju sačuvan transkript i pravi datoteku s referentnim ocjenama koje se
ručno ispravljaju. Rezultat je u .gitignore — transkripti ne idu u javni repo.
"""
import io
import json
import os
import sys

from dotenv import load_dotenv
from supabase import create_client

KORISNIK = sys.argv[1] if len(sys.argv) > 1 else "info@farmaceutupraksi.ba"
IZLAZ = os.path.join("kalibracija", "referenca.json")

# Gdje F0 mijenja ishod, referenca se ne smije preuzeti bez revizije — inače bi
# novi evaluator bio kalibriran prema upravo onoj nepravdi koju F0 uklanja.
NAPOMENE = {
    "scenarij_1": (
        "F0 mijenja ishod. Pitali ste „da li koristite još neke dodatke prehrani ili lijekove“, "
        "a ocjena je svejedno upisala „nije pitao o Zalim losionu“. Provjeri anamnezu."
    ),
    "scenarij_3": (
        "F0 mijenja ishod. Pitali ste za biljne preparate („da li ste uzimali možda nešto od "
        "dodataka na biljnoj bazi“) i pacijentica je porekla. Stara ocjena to nije priznala. "
        "Provjeri anamnezu prije nego posluži kao referenca."
    ),
    "scenarij_4": (
        "F0 mijenja ishod. Dvaput ste pitali za biljne dodatke, a ocjena je svejedno upisala "
        "„nije pitao za suplemente“. Sigurnost 0 vjerovatno stoji (magnezij preporučen bez "
        "kompletne slike), ali anamneza 2 je bila nepravedna."
    ),
}


def main():
    load_dotenv(".env")
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    r = (db.table("attempts")
           .select("scenario_id, completed_at, score, anamneza, komunikacija, sigurnost, transcript")
           .eq("user_email", KORISNIK).not_.is_("transcript", "null")
           .order("completed_at").execute())

    stavke = []
    for a in r.data:
        stavke.append({
            "scenarij": a["scenario_id"],
            "datum": a["completed_at"][:10],
            "referenca": {
                "anamneza": a["anamneza"],
                "komunikacija": a["komunikacija"],
                "sigurnost": a["sigurnost"],
                "ukupno": round(float(a["score"]), 1),
            },
            "potvrdio_semir": False,
            "napomena": NAPOMENE.get(a["scenario_id"], ""),
            "transkript": a["transcript"],
        })

    podaci = {
        "opis": ("Referentne ocjene za evaluator. Ispravi brojeve pod 'referenca' na ono što "
                 "smatraš tačnim i postavi 'potvrdio_semir' na true. Samo potvrđene stavke "
                 "ulaze u mjerenje odstupanja."),
        "korisnik": KORISNIK,
        "stavke": stavke,
    }
    with io.open(IZLAZ, "w", encoding="utf-8") as f:
        json.dump(podaci, f, ensure_ascii=False, indent=2)
    print(f"Upisano {len(stavke)} transkripta u {IZLAZ}")
    for s in stavke:
        oznaka = "  (traži reviziju)" if s["napomena"] else ""
        print(f"  {s['scenarij']} · {s['datum']} · {s['referenca']['ukupno']}/10{oznaka}")


if __name__ == "__main__":
    main()
