"""
Clinical Case Simulator — Edu Pharma Community
Faze 4-6 + Auth + Limit poteza + Auto-evaluacija
"""

import json
import os
import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

# ─── API ključ ────────────────────────────────────────────────────────────────
try:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    load_dotenv()

client = Anthropic()

MAX_POTEZA = 7  # maksimalan broj unosa farmaceuta

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
Rubrika za ocjenjivanje (svaka kategorija 0-10):

ANAMNEZA (tezina 0.4):
- Pitao za trajanje tegobe (2 boda)
- Pitao sta vec koristi i koliko dugo (2 boda)
- Pitao o trudnoci / posebnim stanjima (2 boda)
- Pitao za alergije (2 boda)
- Prepoznao crvene zastavice iz odgovora (2 boda)
KAZNA: ako nije pitao o trudnoci -> max 4/10. Ako nije pitao sta koristi -> max 6/10.

KOMUNIKACIJA (tezina 0.3):
- Koristio razumljiv jezik laika (2 boda)
- Empatican ton, bez osudjivanja (2 boda)
- Provjerio da li je pacijent razumio (2 boda)
- Strukturisan, logican tok razgovora (2 boda)
- Jasno prenio poruku o prekinutoj terapiji i odlasku ljekaru (2 boda)

SIGURNOST (tezina 0.3):
- Odbio izdati Clobetasol bez recepta trudnici (3 boda)
- Rekao da oba preparata treba odmah prekinuti (3 boda)
- Nije preporucio zamjensku terapiju bez pregleda (2 boda)
- Uputio na pregled — ginekolog i/ili dermatolog (2 boda)
KAZNA: ako je izdao kortikosteroid trudnici -> 0/10 za Sigurnost.
"""

# ─── System prompt sa prompt cachingom ───────────────────────────────────────
def napravi_system_prompt(sc):
    staticki_dio = (
        "Ti si pacijent koji je upravo usao u apoteku. "
        "Pravila ponasanja:\n"
        "1. Govori u prvom licu, prirodno, kao obican pacijent — ne kao strucnjak. Koristi jezik laika.\n"
        "2. Odgovaraj kratko: najvise 2 recenice po replici.\n"
        "3. NE otkrivaj sve simptome odjednom. Farmaceut te mora pitati da bi izvukao informacije.\n"
        "4. Budi realistican i blago skeptican — mozes pitati o cijeni ili nuspojavama.\n"
        "5. Ako te farmaceut nista konkretno ne pita, ne nudi informacije sam od sebe.\n"
        "6. Ostani u ulozi pacijenta bez obzira na sve. Nikada ne izlazi iz uloge.\n"
        "7. Govori iskljucivo na bosanskom jeziku."
    )
    dinamicki_dio = (
        f"\n\nGlumaš sljedeću osobu:\n"
        f"- Ime i godine: {sc['ime']}, {sc['godine']}\n"
        f"- Glavna tegoba: {sc['tegoba']}\n"
        f"- Trenutna terapija: {sc['terapija']}\n"
        f"- Skriveni detalji (otkrij SAMO na pravo pitanje): {sc['skriveni_detalji']}"
    )
    return [
        {"type": "text", "text": staticki_dio, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": dinamicki_dio},
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
Ocekivano savjetovanje: {sc['ocekivano_savjetovanje']}

{RUBRIKA}

Transkript razgovora:
{transkript_tekst}

Ocijeni savjetovanje prema rubrici. Vrati SAMO validan JSON, bez ikakvog teksta prije ili poslije:
{{
  "anamneza": <broj 0-10>,
  "komunikacija": <broj 0-10>,
  "sigurnost": <broj 0-10>,
  "ukupna_ocjena": <broj 0.0-10.0>,
  "propustena_pitanja": ["pitanje koje nije postavljeno 1", "pitanje 2"],
  "pohvale": ["sta je farmaceut uradio dobro 1"],
  "smjernice": ["konkretan prijedlog za poboljsanje 1", "prijedlog 2"]
}}"""

    odgovor = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return odgovor.content[0].text


def prikazi_ocjenu(r):
    """Prikaži ocjenu savjetovanja — koristi se i odmah i pri ponovnom pregledu."""
    ukupno = float(r.get("ukupna_ocjena", 0))
    boja = "🟢" if ukupno >= 7 else ("🟡" if ukupno >= 5 else "🔴")

    st.markdown("## Ocjena savjetovanja")
    st.markdown(f"### {boja} Ukupna ocjena: **{ukupno:.1f} / 10**")

    col1, col2, col3 = st.columns(3)
    col1.metric("Anamneza (×0.4)", f"{r.get('anamneza', 0)}/10")
    col2.metric("Komunikacija (×0.3)", f"{r.get('komunikacija', 0)}/10")
    col3.metric("Sigurnost (×0.3)", f"{r.get('sigurnost', 0)}/10")

    st.divider()

    pohvale = r.get("pohvale", [])
    if pohvale:
        st.markdown("#### Šta ste uradili dobro")
        for p in pohvale:
            st.success(p, icon="✅")

    propustena = r.get("propustena_pitanja", [])
    if propustena:
        st.markdown("#### Propuštena pitanja")
        for p in propustena:
            st.warning(p, icon="❓")

    smjernice = r.get("smjernice", [])
    if smjernice:
        st.markdown("#### Smjernice za poboljšanje")
        for s in smjernice:
            st.info(s, icon="💡")


def izvuci_json(tekst):
    """Izvuci JSON iz teksta modela, robustno."""
    tekst = tekst.strip()
    pocetak = tekst.find("{")
    kraj = tekst.rfind("}") + 1
    if pocetak == -1 or kraj == 0:
        return None
    try:
        return json.loads(tekst[pocetak:kraj])
    except json.JSONDecodeError:
        return None


def pokreni_evaluaciju(stanje, sc):
    """Pokreni evaluatora i spremi rezultat u stanje."""
    transkript_tekst = "\n".join(
        f"{'Farmaceut' if p['role'] == 'user' else 'Pacijent'}: {p['content']}"
        for p in stanje["poruke_prikaz"]
    )
    with st.spinner("Evaluator analizira savjetovanje..."):
        json_tekst = pozovi_evaluatora(transkript_tekst, sc)

    rezultat = izvuci_json(json_tekst)
    if rezultat:
        stanje["ocjena"] = rezultat
        stanje["zavrseno"] = True
    else:
        st.error("Greška pri analizi ocjene. Pokušaj kliknuti 'Završi savjetovanje' ponovo.")
        stanje["zavrseno"] = False


# ─── Auth funkcije ────────────────────────────────────────────────────────────
def provjeri_login(email, lozinka):
    try:
        korisnici = dict(st.secrets.get("users", {}))
        return korisnici.get(email.lower().strip()) == lozinka
    except Exception:
        return False


def prikazi_login():
    st.markdown("## Prijava")
    st.markdown("Unesite vaše podatke za pristup aplikaciji.")

    with st.form("login_form"):
        email = st.text_input("Email adresa")
        lozinka = st.text_input("Lozinka", type="password")
        submit = st.form_submit_button("Prijavi se", type="primary")

    if submit:
        if provjeri_login(email, lozinka):
            st.session_state["ulogovan"] = True
            st.session_state["korisnik_email"] = email.lower().strip()
            st.session_state["pokusaji"] = set()
            st.rerun()
        else:
            st.error("Pogrešan email ili lozinka.")

    st.divider()
    st.markdown("**Nemate pristup?**")
    st.info(
        "Pošaljite zahtjev za registraciju na: **semir.mehovic1989@gmail.com**\n\n"
        "U poruci navedite: ime i prezime, instituciju/apoteku i razlog pristupa.",
        icon="📧",
    )


# ─── Streamlit UI ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Clinical Case Simulator",
    page_icon="💊",
    layout="centered",
)

# Disclaimer
st.warning(
    "**NAPOMENA:** Ovaj alat namijenjen je isključivo **edukaciji i vježbi**. "
    "**NIJE** podrška stvarnom kliničkom odlučivanju. Sve osobe su izmišljene.",
    icon="⚠️",
)

st.markdown("## 💊 Clinical Case Simulator")
st.caption("Edu Pharma Community · Semir Mehović, mag. pharm.")
st.divider()

# ─── Provjera prijave ─────────────────────────────────────────────────────────
if not st.session_state.get("ulogovan"):
    prikazi_login()
    st.stop()

# Odjava
with st.sidebar:
    st.markdown(f"**Prijavljeni kao:**\n{st.session_state.get('korisnik_email', '')}")
    if st.button("Odjavi se"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ─── Odabir scenarija (svi scenariji vidljivi, završeni označeni) ─────────────
pokusaji = st.session_state.get("pokusaji", set())

def naziv_za_prikaz(naziv):
    if naziv in pokusaji:
        return "✅ " + naziv
    return naziv

opcije = list(SCENARIJI.keys())
odabrani_naziv = st.selectbox(
    "Odaberi scenarij:",
    opcije,
    format_func=naziv_za_prikaz,
)
sc = SCENARIJI[odabrani_naziv]
vec_odraden = odabrani_naziv in pokusaji

# Podaci o pacijentu
with st.expander("Podaci o pacijentu", expanded=True):
    st.markdown(f"**Ime:** {sc['ime']}  |  **Godine:** {sc['godine']}")
    st.markdown(f"**Tegoba:** {sc['tegoba']}")
    st.markdown(f"**Terapija:** {sc['terapija']}")

st.divider()

# ─── Session state za razgovor ────────────────────────────────────────────────
kljuc = f"chat_{odabrani_naziv}"
if kljuc not in st.session_state:
    st.session_state[kljuc] = {
        "poruke_api": [],
        "poruke_prikaz": [],
        "ocjena": None,
        "zavrseno": False,
        "broj_poteza": 0,
    }

stanje = st.session_state[kljuc]

# ─── Ako je scenarij završen — prikaži transkript i ocjenu (read-only) ────────
if vec_odraden:
    st.info("Ovaj scenarij ste već završili. Ispod možete pregledati transkript i vašu ocjenu.", icon="📋")

    with st.expander("Transkript razgovora", expanded=False):
        for poruka in stanje["poruke_prikaz"]:
            avatar = "🧑‍⚕️" if poruka["role"] == "user" else "🙍"
            with st.chat_message(poruka["role"], avatar=avatar):
                st.markdown(poruka["content"])

    if stanje["ocjena"]:
        prikazi_ocjenu(stanje["ocjena"])
    else:
        st.warning("Ocjena nije dostupna za ovaj scenarij.")
    st.stop()

# ─── Aktivni razgovor ─────────────────────────────────────────────────────────
for poruka in stanje["poruke_prikaz"]:
    avatar = "🧑‍⚕️" if poruka["role"] == "user" else "🙍"
    with st.chat_message(poruka["role"], avatar=avatar):
        st.markdown(poruka["content"])

# Prva poruka pacijenta
if not stanje["poruke_prikaz"] and not stanje["zavrseno"]:
    prva = sc["pocetna_poruka"]
    stanje["poruke_prikaz"].append({"role": "assistant", "content": prva})
    stanje["poruke_api"].append({"role": "assistant", "content": prva})
    with st.chat_message("assistant", avatar="🙍"):
        st.markdown(prva)

# ─── Unos farmaceuta ──────────────────────────────────────────────────────────
if not stanje["zavrseno"]:
    preostalo = MAX_POTEZA - stanje["broj_poteza"]
    st.caption(f"Preostalo unosa: **{preostalo} / {MAX_POTEZA}**")

    unos = st.chat_input("Vaš odgovor (farmaceut)...")
    if unos:
        stanje["poruke_prikaz"].append({"role": "user", "content": unos})
        stanje["poruke_api"].append({"role": "user", "content": unos})
        stanje["broj_poteza"] += 1

        with st.chat_message("user", avatar="🧑‍⚕️"):
            st.markdown(unos)

        if stanje["broj_poteza"] < MAX_POTEZA:
            with st.chat_message("assistant", avatar="🙍"):
                with st.spinner(""):
                    odgovor = pozovi_pacijenta(stanje["poruke_api"], sc)
                st.markdown(odgovor)
                stanje["poruke_prikaz"].append({"role": "assistant", "content": odgovor})
                stanje["poruke_api"].append({"role": "assistant", "content": odgovor})
            st.rerun()
        else:
            st.info(f"Dostigli ste maksimalan broj unosa ({MAX_POTEZA}). Savjetovanje se automatski završava.")
            pokusaji.add(odabrani_naziv)
            st.session_state["pokusaji"] = pokusaji
            pokreni_evaluaciju(stanje, sc)
            st.rerun()

# Ručno završavanje
st.divider()
if not stanje["zavrseno"] and stanje["broj_poteza"] >= 2:
    if st.button("Završi savjetovanje i dobij ocjenu", type="primary"):
        pokusaji.add(odabrani_naziv)
        st.session_state["pokusaji"] = pokusaji
        pokreni_evaluaciju(stanje, sc)
        st.rerun()

# ─── Prikaz ocjene nakon završetka ───────────────────────────────────────────
if stanje["zavrseno"] and stanje["ocjena"]:
    prikazi_ocjenu(stanje["ocjena"])
