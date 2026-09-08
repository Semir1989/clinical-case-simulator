"""Pozivi prema modelu: pacijent, ocjenjivac, generator scenarija."""
import base64
import json

import streamlit as st

from konfig import (JEZIK_PRAVILO, MAX_POTEZA, MODEL_EVALUATOR, MODEL_GENERATOR, MODEL_PACIJENT,
                    ai)
from baza import db_log_upotrebu, db_spremi
from ocjena import izvuci_json, provjeri_ocjenu
from scenariji import SCENARIJI
from promptovi import (EVALUATOR_SHEMA, EVALUATOR_SISTEM, GENERATOR_SISTEM,
                       PACIJENT_PRIRUCNIK)

def napravi_system_prompt(sc):
    staticki = PACIJENT_PRIRUCNIK + "\n\n" + JEZIK_PRAVILO
    dinamicki = (
        f"\nGlumaš: {sc['ime']}, {sc['godine']} god.\n"
        f"Tegoba: {sc['tegoba']}\n"
        f"Terapija koju odmah priznaješ: {sc['terapija']}\n"
        f"Tvoje skrivene činjenice — daješ ih po pravilu „KADA OTKRIVAŠ, A KADA ŠUTIŠ“, "
        f"a ništa izvan ove liste ne postoji:\n{sc['skriveni_detalji']}"
    )
    return [
        {"type": "text", "text": staticki, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": dinamicki},
    ]


def pozovi_pacijenta(poruke, sc):
    r = ai.messages.create(
        model=MODEL_PACIJENT, max_tokens=400,
        system=napravi_system_prompt(sc), messages=poruke,
    )
    db_log_upotrebu("poruka", st.session_state.get("odabrani_scenarij", ""),
                    r.usage.input_tokens, r.usage.output_tokens)
    return r.content[0].text


def pozovi_evaluatora(transkript, sc, broj_poteza=MAX_POTEZA):
    prompt = f"""Ocijeni savjetovanje farmaceuta u apoteci.

Scenarij: {sc['ime']}, {sc['godine']} god. — {sc['tegoba']}
Crvene zastavice: {sc['crvene_zastavice']}
Očekivano savjetovanje: {sc['ocekivano']}

RUBRIKA:
{sc.get('rubrika', '')}

OGRANIČENJE RAZGOVORA: farmaceut je imao najviše {broj_poteza} poteza (poruka). Vidi pravilo 3.

TRANSKRIPT:
{transkript}

Vrati ISKLJUČIVO validan JSON bez ikakvog teksta prije ili poslije, tačno ovog oblika:
{EVALUATOR_SHEMA}"""
    r = ai.messages.create(
        model=MODEL_EVALUATOR, max_tokens=3000, temperature=0,
        system=EVALUATOR_SISTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    db_log_upotrebu("evaluacija", st.session_state.get("odabrani_scenarij", ""),
                    r.usage.input_tokens, r.usage.output_tokens)
    return r.content[0].text


def pokreni_evaluaciju(stanje, sc, sc_id):
    transkript = "\n".join(
        f"{'Farmaceut' if p['role'] == 'user' else 'Pacijent'}: {p['content']}"
        for p in stanje["poruke_prikaz"]
    )
    with st.spinner("Analizira savjetovanje..."):
        json_tekst = pozovi_evaluatora(transkript, sc, MAX_POTEZA)

    rezultat = izvuci_json(json_tekst)
    if rezultat:
        rezultat = provjeri_ocjenu(rezultat, transkript)
        stanje["ocjena"] = rezultat
        stanje["zavrseno"] = True
        db_spremi(st.session_state.get("korisnik_email", ""), sc_id, rezultat, transkript)
    else:
        st.error("Greška pri analizi ocjene. Pokušaj ponovo.")
        stanje["zavrseno"] = False


def generisi_scenarij_iz_pdfa(pdf_bytes, tezina, smjernice):
    """Šalje PDF case report Claudeu i vraća generisani scenarij (dict) ili None."""
    upute = (
        f"Nivo težine: {tezina}.\n"
        + ("Ekspertni nivo: dodaj i drugi sloj problema (npr. interakcija koja se vidi tek "
           "kad se otkrije kompletna terapija) i pojačaj lažni trag.\n"
           if tezina == "Ekspertno" else "")
        + (f"Dodatne smjernice admina: {smjernice.strip()}\n" if smjernice.strip() else "")
        + "Analiziraj priloženi case report i kreiraj scenarij prema uputama."
    )
    r = ai.messages.create(
        model=MODEL_GENERATOR, max_tokens=8000,
        system=GENERATOR_SISTEM,
        messages=[{
            "role": "user",
            "content": [
                {"type": "document", "source": {
                    "type": "base64", "media_type": "application/pdf",
                    "data": base64.standard_b64encode(pdf_bytes).decode(),
                }},
                {"type": "text", "text": upute},
            ],
        }],
    )
    db_log_upotrebu("generisanje_scenarija", "",
                    r.usage.input_tokens, r.usage.output_tokens)
    return izvuci_json(r.content[0].text)


def sljedeci_scenarij_id():
    """Prvi slobodan ID oblika scenarij_N."""
    n = 1
    while f"scenarij_{n}" in SCENARIJI:
        n += 1
    return f"scenarij_{n}"
