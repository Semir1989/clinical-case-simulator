"""Testovi za gradnju prompta pacijenta (F3) — bez API poziva i bez baze.

    python test_prompt.py

Najvažnije je da scenarij BEZ liste činjenica i dalje radi po starom. Dok se
svi scenariji ne konvertuju, taj povratak je jedino što ih drži u igri.
"""
import sys

from motor import napravi_system_prompt, opisi_cinjenice, opisi_personu

pao = []


def provjeri(naziv, uslov):
    print(("  OK   " if uslov else "  PAO  ") + naziv)
    if not uslov:
        pao.append(naziv)


NOVI = {
    "ime": "Stefan", "godine": 71,
    "tegoba": "bolovi u mišićima", "terapija": "tablete za pritisak i srce",
    "skriveni_detalji": "stari tekst koji se ne smije koristiti kad ima činjenica",
    "persona": {"pricljivost": 3, "obrazovanje": "srednje", "raspolozenje": "umoran",
                "zurba": True, "zanimanje": "penzioner"},
    "cinjenice": [
        {"id": "tribulus", "cinjenica": "uzima Tribulus 500 mg iz sportske prodavnice",
         "okidac": "pitanje o dodacima prehrani ili biljnim preparatima", "osjetljivo": True},
        {"id": "aspirin", "cinjenica": "uzima mali aspirin 100 mg",
         "okidac": "pitanje uzima li još neke lijekove", "osjetljivo": False},
    ],
}

STARI = {
    "ime": "Lejla", "godine": 18,
    "tegoba": "svrbež kože", "terapija": "vitamini",
    "skriveni_detalji": "koristi klobetazol već šest mjeseci po preporuci komšinice",
}

print("\nScenarij s listom činjenica")
d = napravi_system_prompt(NOVI)[1]["text"]
provjeri("činjenica je u promptu", "Tribulus 500 mg iz sportske prodavnice" in d)
provjeri("okidač je uz činjenicu", "pitanje o dodacima prehrani ili biljnim preparatima" in d)
provjeri("osjetljiva je označena", "[OSJETLJIVO" in d)
provjeri("neosjetljiva nije označena kao osjetljiva",
         d.count("[OSJETLJIVO") == 1)
provjeri("stari tekst se NE koristi kad ima činjenica",
         "stari tekst koji se ne smije koristiti" not in d)

print("\nPersona")
provjeri("pričljivost je u promptu", "Pričljivost: 3 od 5" in d)
provjeri("obrazovanje je u promptu", "Obrazovanje: srednje" in d)
provjeri("žurba je u promptu", "Žuri ti se" in d)
provjeri("prazna persona ne pravi prazan odjeljak", opisi_personu({}) == "")
provjeri("None persona ne ruši gradnju", opisi_personu(None) == "")
provjeri("žurba false se ne spominje", "Žuri ti se" not in opisi_personu({"pricljivost": 2}))

print("\nScenarij bez liste činjenica — povratak na stari tekst")
d2 = napravi_system_prompt(STARI)[1]["text"]
provjeri("stari tekst se koristi", "koristi klobetazol već šest mjeseci" in d2)
provjeri("nema odjeljka o okidačima", "otključava je:" not in d2)
provjeri("prazna lista činjenica takođe pada na stari tekst",
         "klobetazol" in opisi_cinjenice({**STARI, "cinjenice": []}))

print("\nStatični blok")
staticki = napravi_system_prompt(NOVI)[0]
provjeri("statični blok je označen za keširanje",
         staticki.get("cache_control", {}).get("type") == "ephemeral")
provjeri("priručnik nosi pravilo o okidačima", "OKIDAČ" in staticki["text"])
provjeri("priručnik nosi persona sloj", "PERSONA" in staticki["text"])
provjeri("priručnik nosi jezično pravilo", "ijekavskim izgovorom" in staticki["text"])
# 1024 tokena je prag od kojeg Anthropic kesira; bosanski je oko 2 tokena po rijeci.
provjeri("priručnik je dovoljno dug da se kešira (>1024 tokena)",
         len(staticki["text"].split()) > 600)

print()
if pao:
    print(f"PALO: {len(pao)}")
    sys.exit(1)
print("Svi testovi prolaze.")
