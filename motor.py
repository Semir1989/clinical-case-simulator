"""Pozivi prema modelu: pacijent, ocjenjivac, generator scenarija."""
import base64
import json

import streamlit as st

from konfig import (JEZIK_PRAVILO, MAX_POTEZA, zabiljezi_gresku, MODEL_EVALUATOR, MODEL_GENERATOR, MODEL_PACIJENT,
                    ai)
from baza import db_log_upotrebu, db_spremi
from ocjena import izvuci_json, provjeri_ocjenu
from stanje import izdvoji_stanje, sazetak_za_evaluatora
from scenariji import SCENARIJI
from promptovi import (EVALUATOR_SHEMA, EVALUATOR_SISTEM, GENERATOR_SISTEM,
                       PACIJENT_PRIRUCNIK)

PERSONA_OPISI = {
    "pricljivost": "Pričljivost: {v} od 5",
    "obrazovanje": "Obrazovanje: {v}",
    "raspolozenje": "Raspoloženje: {v}",
    "zanimanje": "Zanimanje: {v}",
    "porodica": "Porodica i okolnosti: {v}",
    "odnos_prema_lijekovima": "Odnos prema lijekovima: {v}",
}


def opisi_personu(persona):
    if not persona:
        return ""
    redovi = [PERSONA_OPISI[k].format(v=persona[k])
              for k in PERSONA_OPISI if persona.get(k) not in (None, "")]
    if persona.get("zurba"):
        redovi.append("Žuri ti se — više puta to spomeneš.")
    return "\nTVOJA PERSONA (mijenja kako govoriš, ne šta znaš):\n- " + "\n- ".join(redovi) if redovi else ""


def opisi_cinjenice(sc):
    """Lista činjenica s okidačima; ako je nema, vraća stari tekstualni opis.

    Fallback postoji dok se svi scenariji ne konvertuju — scenarij bez liste
    mora i dalje raditi, samo bez okidača.
    """
    cinjenice = sc.get("cinjenice")
    if not cinjenice:
        return ("\nTVOJE SKRIVENE ČINJENICE — daješ ih po pravilu „KADA OTKRIVAŠ, A KADA ŠUTIŠ“, "
                f"a ništa izvan ovoga ne postoji:\n{sc.get('skriveni_detalji', '')}")

    redovi = []
    for c in cinjenice:
        oznaka = " [OSJETLJIVO — prešućuješ iz stida ili straha]" if c.get("osjetljivo") else ""
        redovi.append(
            f"- ({c.get('id', '?')}) {c.get('cinjenica', '')}\n"
            f"  otključava je: {c.get('okidac', 'bilo koje direktno pitanje o ovome')}{oznaka}"
        )
    return ("\nTVOJE ČINJENICE. Ovo je sve što o sebi znaš — ništa izvan ove liste ne postoji.\n"
            "Uz svaku piše njena oznaka u zagradi i pitanje koje je otključava. Kad neku "
            "otkriješ, u blok stanja upisuješ TAČNO tu oznaku iz zagrade, nikad izmišljenu.\n"
            + "\n".join(redovi))


def opisi_otpor(otpor):
    """Prigovori s uslovima popuštanja, redom kojim se iznose."""
    if not otpor:
        return ""
    redovi = []
    for o in sorted(otpor, key=lambda x: x.get("redoslijed", 99)):
        r = ['- "' + o.get("replika", "") + '"']
        if o.get("fatalno_ako_izda"):
            r.append("  OVAJ PRIGOVOR NE POPUŠTAŠ NIKAD, ma šta farmaceut rekao.")
        else:
            r.append("  popuštaš kad farmaceut " + o.get("uslov_popustanja", "objasni razlog")
                     + ", uz povjerenje najmanje " + str(o.get("prag_povjerenja", 5)))
        redovi.append("\n".join(r))
    return ("\nTVOJI PRIGOVORI, redom kojim ih iznosiš — jedan po replici, ne svi odjednom:\n"
            + "\n".join(redovi))


def opisi_znakove(znakovi):
    if not znakovi:
        return ""
    return ("\nŠTA SE NA TEBI VIDI (koristi kao didaskalije u uglastim zagradama, štedljivo):\n"
            + znakovi)


def napravi_system_prompt(sc):
    staticki = PACIJENT_PRIRUCNIK + "\n\n" + JEZIK_PRAVILO
    dinamicki = (
        f"\nGlumaš: {sc['ime']}, {sc['godine']} god.\n"
        f"Tegoba: {sc['tegoba']}\n"
        f"Terapija koju odmah priznaješ: {sc['terapija']}\n"
        + opisi_personu(sc.get("persona"))
        + "\n" + opisi_cinjenice(sc)
        + "\n" + opisi_otpor(sc.get("otpor"))
        + "\n" + opisi_znakove(sc.get("vidljivi_znakovi"))
    )
    return [
        {"type": "text", "text": staticki, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": dinamicki},
    ]


def pozovi_pacijenta(poruke, sc, prethodno_stanje=None, dodatna_uputa=""):
    """Vraća (replika bez bloka stanja, stanje, sirovi odgovor).

    Sirovi odgovor ide natrag u historiju SA blokom stanja — tako pacijent u
    sljedećem potezu vidi svoje prethodno povjerenje i ne počinje iznova.
    """
    sistem = napravi_system_prompt(sc)
    if dodatna_uputa:
        sistem = sistem + [{"type": "text", "text": dodatna_uputa}]
    r = ai.messages.create(
        model=MODEL_PACIJENT, max_tokens=500,
        system=sistem, messages=poruke,
    )
    db_log_upotrebu("poruka", st.session_state.get("odabrani_scenarij", ""),
                    r.usage.input_tokens, r.usage.output_tokens)
    sirovi = r.content[0].text
    cist, novo = izdvoji_stanje(sirovi, prethodno_stanje)
    return cist, novo, sirovi


UPUTA_ZATVARANJE = (
    "[UPUTA, nije replika farmaceuta] Razgovor se završava i farmaceut se oprostio. "
    "Daj SAMO svoju posljednju repliku — kratku, u prvom licu — iz koje se jasno vidi šta ćeš "
    "uraditi kad izađeš iz apoteke. U bloku stanja obavezno upiši fazu zatvaranje i ishod: "
    "prihvatio, prihvatio_nevoljko, odbio ili otisao_s_lijekom."
)


def zatvori_razgovor(poruke, sc, prethodno_stanje=None):
    """Traži završnu repliku prije ocjenjivanja, da polaznik vidi ishod svog rada.

    Uputa ide kao posljednji potez korisnika, ne samo u sistemski prompt: historija
    završava replikom pacijenta, pa bi model bez toga nastavljao tu istu repliku
    umjesto da počne novu — i vraćao prazno.
    """
    try:
        poruke = list(poruke) + [{"role": "user", "content": UPUTA_ZATVARANJE}]
        return pozovi_pacijenta(poruke, sc, prethodno_stanje, UPUTA_ZATVARANJE)
    except Exception as e:
        zabiljezi_gresku(e)
        return "", prethodno_stanje, ""


def pozovi_evaluatora(transkript, sc, broj_poteza=MAX_POTEZA, stanja=None):
    sazetak = sazetak_za_evaluatora(stanja, sc.get("cinjenice"))
    prompt = f"""Ocijeni savjetovanje farmaceuta u apoteci.

Scenarij: {sc['ime']}, {sc['godine']} god. — {sc['tegoba']}
Crvene zastavice: {sc['crvene_zastavice']}
Očekivano savjetovanje: {sc['ocekivano']}

RUBRIKA:
{sc.get('rubrika', '')}

OGRANIČENJE RAZGOVORA: farmaceut je imao najviše {broj_poteza} poteza (poruka). Vidi pravilo 3.

TRANSKRIPT:
{transkript}

{sazetak}

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
    stanja = stanje.get("stanja") or []
    with st.spinner("Analizira savjetovanje..."):
        json_tekst = pozovi_evaluatora(transkript, sc, MAX_POTEZA, stanja)

    rezultat = izvuci_json(json_tekst)
    if rezultat:
        rezultat = provjeri_ocjenu(rezultat, transkript)
        stanje["ocjena"] = rezultat
        stanje["zavrseno"] = True
        db_spremi(st.session_state.get("korisnik_email", ""), sc_id, rezultat, transkript,
                  stanja)
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
