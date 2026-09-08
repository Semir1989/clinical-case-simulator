"""
Faza 3 — Pacijent-agent u terminalu.
Farmaceut razgovara sa simuliranim pacijentom (Claude u ulozi pacijenta).
Ukucaj 'kraj' da završiš razgovor.
"""

import sys
import os
from anthropic import Anthropic
from dotenv import load_dotenv

# UTF-8 prikaz u terminalu
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Učitaj API ključ
load_dotenv()
client = Anthropic()

# ─── Podaci o pacijentu — mijenjaj ovdje za svaki scenarij ───────────────────
IME = "Lejla"
GODINE = 18
TEGOBA = "svrbež i peckanje kože na grudima, dolazi po još Clobetasol kremu"
TERAPIJA = "vitamini za trudnoću (33. sedmica trudnoće, prva trudnoća)"
SKRIVENI_DETALJI = (
    "već 6 mjeseci koristi Zalim losion i Clobetasol 0.05% kremu zajedno svakodnevno na grudima; "
    "na koži su se pojavile strije i sjajne mrlje koje pripisuje trudnoći; "
    "nije bila kod ljekara, preparate je uzela po preporuci komšinice; "
    "boji se da će koža ostati oštećena"
)
CRVENE_ZASTAVICE = (
    "Clobetasol 0.05% je superpotentni TC — kontraindiciran u trudnoći; "
    "Zalim losion (fenol) toksičan i resorptivan — kontraindiciran u trudnoći; "
    "6 mjeseci primjene = aktivne nuspojave (atrofija, strije, telangiektazije); "
    "hitno uputiti ginekologu i dermatologu; ne izdavati Clobetasol bez recepta"
)
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""Ti si pacijent koji je upravo ušao u apoteku. Glumi sljedeću osobu:
- Ime i godine: {IME}, {GODINE}
- Glavna tegoba: {TEGOBA}
- Trenutna terapija: {TERAPIJA}
- Skriveni detalji (otkrij ih SAMO ako farmaceut postavi pravo pitanje): {SKRIVENI_DETALJI}

Pravila ponašanja:
1. Govori u prvom licu, prirodno, kao običan pacijent — ne kao stručnjak. Koristi jezik laika.
2. Odgovaraj kratko: najviše 2 rečenice po replici.
3. NE otkrivaj sve simptome odjednom. Farmaceut te mora pitati (trajanje, jačina, prateći lijekovi, alergije) da bi izvukao informacije.
4. Budi realističan i blago skeptičan — možeš pitati o cijeni ili nuspojavama.
5. Ako te farmaceut ništa konkretno ne pita, ne nudi informacije sam od sebe.
6. Ostani u ulozi pacijenta bez obzira na sve. Nikada ne izlazi iz uloge i ne spominji da si vještačka inteligencija.
7. Govori na bosanskom jeziku."""

def pokreni_razgovor():
    transkript = []  # čuvamo sve poruke za evaluator u Fazi 5
    poruke = []      # historija za API pozive

    print("=" * 60)
    print(f"PACIJENT: {IME}, {GODINE} god.")
    print(f"TEGOBA:   {TEGOBA}")
    print("=" * 60)
    print("(Ukucaj 'kraj' da završiš savjetovanje)\n")

    # Pacijent se sam javi pri ulasku
    pocetna_poruka = "Dobro jutro. Došla sam malo da se posavjetujem, imate li minute?"
    print(f"Pacijent: {pocetna_poruka}\n")
    poruke.append({"role": "assistant", "content": pocetna_poruka})
    transkript.append({"uloga": "Pacijent", "tekst": pocetna_poruka})

    while True:
        unos = input("Vi (farmaceut): ").strip()
        if not unos:
            continue
        if unos.lower() == "kraj":
            print("\n--- Savjetovanje završeno ---")
            break

        transkript.append({"uloga": "Farmaceut", "tekst": unos})
        poruke.append({"role": "user", "content": unos})

        # Poziv modela
        odgovor = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            system=SYSTEM_PROMPT,
            messages=poruke
        )

        tekst_odgovora = odgovor.content[0].text
        poruke.append({"role": "assistant", "content": tekst_odgovora})
        transkript.append({"uloga": "Pacijent", "tekst": tekst_odgovora})

        print(f"\nPacijent: {tekst_odgovora}\n")

    # Ispiši transkript na kraju
    print("\n=== TRANSKRIPT ===")
    for red in transkript:
        print(f"[{red['uloga']}]: {red['tekst']}")

    return transkript


if __name__ == "__main__":
    pokreni_razgovor()
