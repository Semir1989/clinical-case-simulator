"""
Clinical Case Simulator — Edu Pharma Community
Faze 4, 5, 6: Streamlit interfejs + Evaluator + Prompt caching + Disclaimer
"""

import json
import sys
import os
import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

# ─── Scenariji ────────────────────────────────────────────────────────────────
SCENARIJI = {
    "Scenarij 1 — Trudnica i topikalni kortikosteroidi": {
        "ime": "Lejla",
        "godine": 18,
        "tegoba": "svrbež i peckanje kože na grudima, dolazi po još Clobetasol kremu",
        "terapija": "vitamini za trudnoću (33. sedmica trudnoće, prva trudnoća)",
        "skriveni_detalji": (
            "već 6 mjeseci koristi Zalim losion i Clobetasol 0.05% kremu zajedno svakodnevno na grudima; "
            "na koži su se pojavile strije i sjajne mrlje koje pripisuje trudnoći; "
            "nije bila kod ljekara, preparate je uzela po preporuci komšinice; "
            "boji se da će koža ostati oštećena"
        ),
        "crvene_zastavice": (
            "Clobetasol 0.05% je superpotentni TC — kontraindiciran u trudnoći; "
            "Zalim losion (fenol) toksičan i resorptivan — kontraindiciran u trudnoći; "
            "6 mjeseci primjene = aktivne nuspojave; hitno uputiti ginekologu i dermatologu"
        ),
        "ocekivano_savjetovanje": (
            "Farmaceut pita o trudnoći i gestacijskoj sedmici; pita šta već koristi i koliko dugo; "
            "prepoznaje Clobetasol kao superpotentni TC kontraindiciran u trudnoći; "
            "odbija izdati bez recepta; savjetuje prekid oba preparata i hitnu posjetu ljekaru."
        ),
        "pocetna_poruka": "Dobro jutro, trebala bih još jednu Clobetasol kremu, ponestaje mi.",
    },
}

RUBRIKA = """
## Rubrika za ocjenjivanje (svaka kategorija 0–10)

### Anamneza (težina 0.4)
- Pitao za trajanje tegobe (2 boda)
- Pitao šta već koristi i koliko dugo (2 boda)
- Pitao o trudnoći / posebnim stanjima (2 boda)
- Pitao za alergije (2 boda)
- Prepoznao crvene zastavice iz odgovora (2 boda)
> Kazna: ako nije pitao o trudnoći → max 4/10. Ako nije pitao šta koristi → max 6/10.

### Komunikacija (težina 0.3)
- Koristio razumljiv jezik laika (2 boda)
- Empatičan ton, bez osuđivanja (2 boda)
- Provjerio da li je pacijent razumio (2 boda)
- Strukturisan, logičan tok razgovora (2 boda)
- Jasno prenio poruku o prekinutoj terapiji i odlasku ljekaru (2 boda)

### Sigurnost preporuke (težina 0.3)
- Odbio izdati Clobetasol bez recepta trudnici (3 boda)
- Rekao da oba preparata treba odmah prekinuti (3 boda)
- Nije preporučio zamjensku terapiju bez pregleda (2 boda)
- Uputio na pregled — ginekolog i/ili dermatolog (2 boda)
> Kazna: ako je izdao kortikosteroid trudnici → 0/10 za Sigurnost.
"""

# ─── Gradnja system prompta sa prompt cachingom ───────────────────────────────
def napravi_system_prompt(sc):
    staticki_dio = (
        "Ti si pacijent koji je upravo ušao u apoteku. "
        "Pravila ponašanja:\n"
        "1. Govori u prvom licu, prirodno, kao običan pacijent — ne kao stručnjak. Koristi jezik laika.\n"
        "2. Odgovaraj kratko: najviše 2 rečenice po replici.\n"
        "3. NE otkrivaj sve simptome odjednom. Farmaceut te mora pitati da bi izvukao informacije.\n"
        "4. Budi realističan i blago skeptičan — možeš pitati o cijeni ili nuspojavama.\n"
        "5. Ako te farmaceut ništa konkretno ne pita, ne nudi informacije sam od sebe.\n"
        "6. Ostani u ulozi pacijenta bez obzira na sve. Nikada ne izlazi iz uloge.\n"
        "7. Govori isključivo na bosanskom jeziku."
    )
    dinamicki_dio = (
        f"\n\nGlumaš sljedeću osobu:\n"
        f"- Ime i godine: {sc['ime']}, {sc['godine']}\n"
        f"- Glavna tegoba: {sc['tegoba']}\n"
        f"- Trenutna terapija: {sc['terapija']}\n"
        f"- Skriveni detalji (otkrij SAMO na pravo pitanje): {sc['skriveni_detalji']}"
    )
    # Prompt caching: statički dio se kešira, dinamički se mijenja po scenariju
    return [
        {
            "type": "text",
            "text": staticki_dio,
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": dinamicki_dio,
        },
    ]


def pozovi_pacijenta(poruke, sc):
    odgovor = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=napravi_system_prompt(sc),
        messages=poruke,
    )
    return odgovor.content[0].text


def pozovi_evaluatora(transkript_tekst, sc):
    prompt = f"""Si klinički evaluator koji ocjenjuje savjetovanje farmaceuta u apoteci.

Scenarij: {sc['ime']}, {sc['godine']} god. — {sc['tegoba']}
Terapija pacijenta: {sc['terapija']}
Crvene zastavice: {sc['crvene_zastavice']}
Očekivano savjetovanje: {sc['ocekivano_savjetovanje']}

{RUBRIKA}

## Transkript razgovora
{transkript_tekst}

## Zadatak
Ocijeni farmaceutovo savjetovanje prema rubrici. Vrati ISKLJUČIVO validan JSON u ovom formatu:
{{
  "anamneza": <broj 0-10>,
  "komunikacija": <broj 0-10>,
  "sigurnost": <broj 0-10>,
  "ukupna_ocjena": <broj 0-10 na dvije decimale>,
  "propustena_pitanja": ["pitanje 1", "pitanje 2"],
  "pohvale": ["šta je farmaceut uradio dobro"],
  "smjernice": ["konkretan prijedlog za poboljšanje 1", "konkretan prijedlog 2"]
}}
Bez teksta izvan JSON-a."""

    odgovor = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return odgovor.content[0].text


# ─── Streamlit UI ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Clinical Case Simulator",
    page_icon="💊",
    layout="centered",
)

# Disclaimer
st.warning(
    "**NAPOMENA:** Ovaj alat namijenjen je isključivo **edukaciji i vježbi** farmaceutskog savjetovanja. "
    "**NIJE** podrška stvarnom kliničkom odlučivanju. Sve osobe i scenariji su izmišljeni.",
    icon="⚠️",
)

# Naslov
col1, col2 = st.columns([1, 5])
with col1:
    st.markdown("### 💊")
with col2:
    st.markdown("## Clinical Case Simulator")
    st.caption("Edu Pharma Community · Semir Mehović, mag. pharm.")

st.divider()

# Odabir scenarija
odabrani_naziv = st.selectbox("Odaberi scenarij:", list(SCENARIJI.keys()))
sc = SCENARIJI[odabrani_naziv]

# Prikaz podataka o pacijentu
with st.expander("Podaci o pacijentu", expanded=True):
    st.markdown(f"**Ime:** {sc['ime']}  |  **Godine:** {sc['godine']}")
    st.markdown(f"**Tegoba:** {sc['tegoba']}")
    st.markdown(f"**Terapija:** {sc['terapija']}")

st.divider()

# Inicijalizacija session state
kljuc = f"chat_{odabrani_naziv}"
if kljuc not in st.session_state:
    st.session_state[kljuc] = {
        "poruke_api": [],
        "poruke_prikaz": [],
        "ocjena": None,
        "zavrseno": False,
    }

stanje = st.session_state[kljuc]

# Reset dugme
if st.button("Novi razgovor", type="secondary"):
    st.session_state[kljuc] = {
        "poruke_api": [],
        "poruke_prikaz": [],
        "ocjena": None,
        "zavrseno": False,
    }
    st.rerun()

# Prikaz historije chata
for poruka in stanje["poruke_prikaz"]:
    with st.chat_message(poruka["role"], avatar="🧑‍⚕️" if poruka["role"] == "user" else "🙍"):
        st.markdown(poruka["content"])

# Prva poruka pacijenta
if not stanje["poruke_prikaz"] and not stanje["zavrseno"]:
    prva = sc["pocetna_poruka"]
    stanje["poruke_prikaz"].append({"role": "assistant", "content": prva})
    stanje["poruke_api"].append({"role": "assistant", "content": prva})
    with st.chat_message("assistant", avatar="🙍"):
        st.markdown(prva)

# Unos farmaceuta
if not stanje["zavrseno"]:
    unos = st.chat_input("Vaš odgovor (farmaceut)...")
    if unos:
        stanje["poruke_prikaz"].append({"role": "user", "content": unos})
        stanje["poruke_api"].append({"role": "user", "content": unos})
        with st.chat_message("user", avatar="🧑‍⚕️"):
            st.markdown(unos)

        with st.chat_message("assistant", avatar="🙍"):
            with st.spinner("Pacijent odgovara..."):
                odgovor = pozovi_pacijenta(stanje["poruke_api"], sc)
            st.markdown(odgovor)
            stanje["poruke_prikaz"].append({"role": "assistant", "content": odgovor})
            stanje["poruke_api"].append({"role": "assistant", "content": odgovor})

# Dugme za završetak i ocjenu
st.divider()
if not stanje["zavrseno"] and len(stanje["poruke_prikaz"]) >= 3:
    if st.button("Završi savjetovanje i dobij ocjenu", type="primary"):
        stanje["zavrseno"] = True

        transkript_tekst = "\n".join(
            f"{'Farmaceut' if p['role'] == 'user' else 'Pacijent'}: {p['content']}"
            for p in stanje["poruke_prikaz"]
        )

        with st.spinner("Evaluator analizira savjetovanje..."):
            json_tekst = pozovi_evaluatora(transkript_tekst, sc)

        try:
            # Izvuci JSON čak i ako model doda tekst oko njega
            pocetak = json_tekst.find("{")
            kraj = json_tekst.rfind("}") + 1
            rezultat = json.loads(json_tekst[pocetak:kraj])
            stanje["ocjena"] = rezultat
        except Exception:
            st.error("Greška pri parsiranju ocjene. Pokušaj ponovo.")
            stanje["zavrseno"] = False

        st.rerun()

# Prikaz ocjene
if stanje["zavrseno"] and stanje["ocjena"]:
    r = stanje["ocjena"]
    st.markdown("## Ocjena savjetovanja")

    # Ukupna ocjena
    ukupno = r.get("ukupna_ocjena", 0)
    boja = "🟢" if ukupno >= 7 else ("🟡" if ukupno >= 5 else "🔴")
    st.markdown(f"### {boja} Ukupna ocjena: **{ukupno:.1f} / 10**")

    # Tabela po kategorijama
    st.markdown("#### Ocjene po kategorijama")
    col1, col2, col3 = st.columns(3)
    col1.metric("Anamneza (×0.4)", f"{r.get('anamneza', 0)}/10")
    col2.metric("Komunikacija (×0.3)", f"{r.get('komunikacija', 0)}/10")
    col3.metric("Sigurnost (×0.3)", f"{r.get('sigurnost', 0)}/10")

    st.divider()

    # Pohvale
    pohvale = r.get("pohvale", [])
    if pohvale:
        st.markdown("#### Šta ste uradili dobro")
        for p in pohvale:
            st.success(p, icon="✅")

    # Propuštena pitanja
    propustena = r.get("propustena_pitanja", [])
    if propustena:
        st.markdown("#### Propuštena pitanja")
        for p in propustena:
            st.warning(p, icon="❓")

    # Smjernice za poboljšanje
    smjernice = r.get("smjernice", [])
    if smjernice:
        st.markdown("#### Smjernice za poboljšanje")
        for s in smjernice:
            st.info(s, icon="💡")

    st.divider()
    st.caption("Za novi pokušaj klikni 'Novi razgovor' na vrhu.")
