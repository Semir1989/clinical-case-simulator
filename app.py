"""
Clinical Case Simulator — Edu Pharma Community
Supabase backend · Leaderboard · Cross-device persistence · Beautiful UI
"""

import base64
import csv
import io
import json
import os
import hashlib
import re
import secrets
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from collections import defaultdict

import bcrypt
import streamlit as st
import streamlit.components.v1 as components
from anthropic import Anthropic
from dotenv import load_dotenv

from demo import prikazi_demo

ADMIN_EMAIL = "info@farmaceutupraksi.ba"
KONTAKT_EMAIL = "info@farmaceutupraksi.ba"

# ─── Page config (mora biti prva Streamlit komanda) ───────────────────────────
st.set_page_config(
    page_title="Clinical Case Simulator · Edu Pharma",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
# Tirkizna paleta · Mobile-first · Forsiran light mode
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Poppins:wght@500;600;700;800&display=swap');

/* ── Edu Pharma Community — dizajn tokeni (boje iz loga) ── */
:root {
    --epc-navy: #1E3A8A;       /* tamnoplava — "Edu Pharma" */
    --epc-navy-dark: #152C6B;
    --epc-blue: #2C6FBE;       /* kraljevsko plava iz simbola */
    --epc-teal: #2FB7C6;       /* tirkizna iz simbola i "COMMUNITY" */
    --epc-teal-dark: #0D8A9E;
    --epc-bg: #F4F8FB;
    --epc-surface: #FFFFFF;
    --epc-text: #16233B;
    --epc-muted: #51637A;
    --epc-border: #D7E3EE;
    color-scheme: light only !important;
}

/* ── Forsiran light mode — blokira dark prefers ── */
html, body, [class*="css"] {
    font-family: 'Inter', 'Poppins', sans-serif !important;
    color-scheme: light !important;
}
@media (prefers-color-scheme: dark) {
    html, body { background-color: #F4F8FB !important; color: #16233B !important; }
}
#MainMenu, footer { visibility: hidden; }

/* ── Naslovi — Poppins, navy iz loga ── */
[data-testid="stMain"] h1, [data-testid="stMain"] h2,
[data-testid="stMain"] h3, [data-testid="stMain"] h4,
.main h1, .main h2, .main h3, .main h4 {
    font-family: 'Poppins', sans-serif !important;
    color: var(--epc-navy) !important;
    letter-spacing: -0.3px;
}

/* ── Pozadina ── */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
[data-testid="block-container"] {
    background-color: var(--epc-bg) !important;
}

/* ── Sidebar — navy gradijent kao logo ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--epc-navy-dark) 0%, var(--epc-navy) 55%, #17608F 100%) !important;
}
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.25) !important; }
[data-testid="stSidebar"] button {
    background: rgba(255,255,255,0.14) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,0.35) !important;
    border-radius: 10px !important;
}
[data-testid="stSidebar"] button:hover {
    background: rgba(47,183,198,0.45) !important;
    border-color: rgba(255,255,255,0.6) !important;
}

/* ── Dugmad — višestruki selektori za Streamlit 1.5x ── */
.stButton > button,
.stFormSubmitButton > button,
[data-testid="stFormSubmitButton"] button,
[data-testid="baseButton-primary"],
[data-testid="baseButton-secondary"] {
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 16px !important;
    padding: 12px 22px !important;
    min-height: 46px !important;
    transition: all 0.2s ease !important;
}
/* Primary dugme — plava→navy kao logo */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"],
[data-testid="baseButton-primary"],
[data-testid="stFormSubmitButton"] button,
.stButton > button:first-of-type {
    background: linear-gradient(135deg, #2C6FBE, #1E3A8A) !important;
    border: none !important;
    color: white !important;
    -webkit-text-fill-color: white !important;
}
.stButton > button:hover,
.stFormSubmitButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 18px rgba(30,58,138,0.35) !important;
}
/* Secondary dugme */
.stButton > button[kind="secondary"],
[data-testid="baseButton-secondary"] {
    background: white !important;
    border: 2px solid #1E3A8A !important;
    color: #1E3A8A !important;
    -webkit-text-fill-color: #1E3A8A !important;
}
/* Tastaturna navigacija — jasan focus prsten */
.stButton > button:focus-visible,
.stFormSubmitButton > button:focus-visible {
    outline: 3px solid var(--epc-teal) !important;
    outline-offset: 2px !important;
}

/* ── Input polja — bijela pozadina, vidljiv tekst ── */
.stTextInput > div > div > input,
[data-testid="stTextInputRootElement"] input,
[data-baseweb="input"] input,
[data-baseweb="base-input"] input {
    background-color: #FFFFFF !important;
    color: #16233B !important;
    -webkit-text-fill-color: #16233B !important;
    border-radius: 12px !important;
    border: 1.5px solid #C9DBEA !important;
    font-size: 16px !important;
    padding: 12px 14px !important;
}
[data-baseweb="input"],
[data-baseweb="base-input"],
[data-baseweb="input"] > div,
[data-testid="stTextInputRootElement"] > div {
    background-color: #FFFFFF !important;
}
.stTextInput > div > div > input::placeholder,
[data-baseweb="input"] input::placeholder { color: #7C93A8 !important; -webkit-text-fill-color: #7C93A8 !important; }
.stTextInput > div > div > input:focus,
[data-baseweb="input"]:focus-within {
    border-color: #2C6FBE !important;
    box-shadow: 0 0 0 3px rgba(47,183,198,0.25) !important;
    outline: none !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    background: white !important;
    border-radius: 12px !important;
    border: 1.5px solid #C9DBEA !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: white !important;
    border-radius: 14px !important;
    padding: 4px !important;
    gap: 4px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    font-weight: 600 !important;
    color: #48627D !important;
    font-size: 15px !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #2C6FBE, #1E3A8A) !important;
    color: white !important;
}

/* ── Upozorenja — forsiran kontrast ── */
[data-testid="stAlert"] {
    border-radius: 12px !important;
    border-width: 1.5px !important;
}
[data-testid="stAlert"][data-baseweb="notification"] {
    background-color: #FFF8E1 !important;
}
/* Warning — tamni tekst na žutoj pozadini */
div[data-testid="stAlert"] p,
div[data-testid="stAlert"] span,
div[data-testid="stAlert"] div {
    color: #5C4000 !important;
    font-weight: 500 !important;
}
/* Success — zelena */
.stSuccess { background-color: #E8F8F0 !important; }
.stSuccess * { color: #1A5C38 !important; }
/* Info — tirkizna */
.stInfo { background-color: #E0F4F7 !important; }
.stInfo * { color: #0A4A54 !important; }
/* Error — crvena */
.stError { background-color: #FDE8E8 !important; }
.stError * { color: #8B0000 !important; }

/* ── Chat poruke ── */
[data-testid="stChatMessage"] {
    border-radius: 16px !important;
    margin-bottom: 10px !important;
    background: white !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] > div {
    border-radius: 16px !important;
    border: 2px solid #C9DBEA !important;
    background: white !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: #2C6FBE !important;
    box-shadow: 0 0 0 3px rgba(47,183,198,0.2) !important;
}

/* ── Metric kartice ── */
[data-testid="metric-container"] {
    background: white !important;
    border-radius: 14px !important;
    padding: 18px !important;
    box-shadow: 0 1px 6px rgba(0,0,0,0.07) !important;
    border-top: 3px solid var(--epc-teal) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--epc-navy) !important;
    font-weight: 800 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: white !important;
    border-radius: 14px !important;
    border: 1.5px solid var(--epc-border) !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
}

/* ── Divider ── */
hr { border-color: var(--epc-border) !important; }

/* ── Form ── */
[data-testid="stForm"] {
    background: white !important;
    border-radius: 16px !important;
    padding: 20px !important;
    border: 1.5px solid var(--epc-border) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
}

/* ── Login/Registracija — veći font u formi ── */
[data-testid="stForm"] label {
    font-size: 16px !important;
    font-weight: 600 !important;
    color: var(--epc-text) !important;
}
[data-testid="stForm"] .stFormSubmitButton button {
    font-size: 17px !important;
    font-weight: 700 !important;
    padding: 12px 20px !important;
}

/* ── Sidebar radio navigacija — veća slova ── */
[data-testid="stSidebar"] [role="radiogroup"] label {
    font-size: 17px !important;
    font-weight: 600 !important;
    letter-spacing: 0.2px !important;
}
[data-testid="stSidebar"] [role="radiogroup"] label p {
    font-size: 17px !important;
    font-weight: 600 !important;
}

/* ── Mobile optimizacija ── */
@media (max-width: 768px) {
    [data-testid="block-container"] { padding: 12px !important; }
    .stButton > button { font-size: 14px !important; padding: 10px 16px !important; }
    [data-testid="stSidebar"] [role="radiogroup"] label,
    [data-testid="stSidebar"] [role="radiogroup"] label p {
        font-size: 19px !important;
        font-weight: 700 !important;
    }
}
/* ── Mobile: istakni Streamlit-ov ugrađeni hamburger ── */
@media (max-width: 768px) {
    [data-testid="stSidebarCollapsedControl"] {
        background: linear-gradient(135deg, #2C6FBE, #1E3A8A) !important;
        border-radius: 14px !important;
        box-shadow: 0 4px 16px rgba(30,58,138,0.5) !important;
        border: 2px solid rgba(255,255,255,0.7) !important;
        top: 10px !important;
        left: 10px !important;
        padding: 6px !important;
        min-width: 48px !important;
        min-height: 48px !important;
        z-index: 999999 !important;
        animation: menuPulse 2s ease-in-out 3 !important;
    }
    [data-testid="stSidebarCollapsedControl"] button {
        background: transparent !important;
        border: none !important;
        color: white !important;
        padding: 8px !important;
    }
    [data-testid="stSidebarCollapsedControl"] svg {
        color: white !important;
        width: 26px !important;
        height: 26px !important;
        stroke: white !important;
    }
    @keyframes menuPulse {
        0%, 100% { box-shadow: 0 4px 16px rgba(30,58,138,0.5); }
        50% { box-shadow: 0 4px 28px rgba(30,58,138,0.85), 0 0 0 8px rgba(47,183,198,0.25); }
    }
}
</style>
""", unsafe_allow_html=True)

# ─── Indikator za meni (mobilni) — nestaje nakon 6s ─────────────────────────
st.markdown("""
<div id="menuHint" style="
    position: fixed;
    top: 18px;
    left: 62px;
    z-index: 999998;
    background: white;
    color: #1E3A8A;
    font-size: 14px;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.12);
    display: none;
    align-items: center;
    gap: 4px;
    animation: hintFade 6s ease-in-out forwards;
    pointer-events: none;
">
    <span style="font-size:16px">&#8592;</span> Meni
</div>
<style>
    @media (max-width: 768px) {
        #menuHint { display: flex !important; }
    }
    @keyframes hintFade {
        0% { opacity: 0; transform: translateX(8px); }
        8% { opacity: 1; transform: translateX(0); }
        75% { opacity: 1; }
        100% { opacity: 0; display: none; }
    }
</style>
""", unsafe_allow_html=True)

# ─── Inicijalizacija ──────────────────────────────────────────────────────────
try:
    os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    load_dotenv()
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

ai = Anthropic()

# Supabase klijent — učitava se samo ako je URL dostupan
db = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        db = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        pass

# ─── Sentry — log grešaka (aktivan samo ako je SENTRY_DSN u secrets) ─────────
try:
    SENTRY_DSN = st.secrets.get("SENTRY_DSN", "")
except Exception:
    SENTRY_DSN = os.getenv("SENTRY_DSN", "")


@st.cache_resource
def _init_sentry(dsn):
    """Inicijalizuje Sentry jednom po procesu i hooka Streamlit-ov handler
    za neuhvaćene greške (Streamlit ih inače proguta i samo prikaže u UI)."""
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.threading import ThreadingIntegration

        sentry_sdk.init(
            dsn=dsn,
            send_default_pii=False,
            traces_sample_rate=0,
            # ThreadingIntegration lomi Streamlit-ove interne threadove
            # (add_script_run_ctx) — mora ostati isključena
            disabled_integrations=[ThreadingIntegration()],
        )

        from streamlit.runtime.scriptrunner import exec_code as _st_exec
        _orig = _st_exec.handle_user_script_exception

        def _sentry_hook(ex, *args, **kwargs):
            sentry_sdk.capture_exception(ex)
            return _orig(ex, *args, **kwargs)

        _st_exec.handle_user_script_exception = _sentry_hook
        return True
    except Exception:
        return False


SENTRY_AKTIVAN = _init_sentry(SENTRY_DSN)


def zabiljezi_gresku(e):
    """Šalje uhvaćenu grešku u Sentry ako je konfigurisan; inače tiho."""
    if not SENTRY_AKTIVAN:
        return
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(e)
    except Exception:
        pass


MAX_POTEZA = 10
DNEVNI_LIMIT_PORUKA = 60  # max AI poruka po korisniku dnevno (kontrola troškova)

# Modeli — na jednom mjestu da se mogu mijenjati bez traženja po fajlu
MODEL_PACIJENT = "claude-sonnet-4-6"
MODEL_EVALUATOR = "claude-sonnet-4-6"
MODEL_GENERATOR = "claude-sonnet-4-6"

# Procjena troška — claude-sonnet cijene po tokenu (USD)
CIJENA_ULAZ_USD = 3.00 / 1_000_000
CIJENA_IZLAZ_USD = 15.00 / 1_000_000

# ─── Jezik ────────────────────────────────────────────────────────────────────
# Ulazi u SVA tri sistemska prompta (pacijent, evaluator, generator). Bez ovoga
# model bira jezični standard sam i tiho klizi ka hrvatskim oblicima —
# u 17 zapisa u bazi izmjereno: "što" 29x, "posjet" 11x, "liječnik" 2x.
JEZIK_PRAVILO = """JEZIK — obavezno i bez izuzetka:
Piši isključivo na bosanskom jeziku, ijekavskim izgovorom, s punom dijakritikom (č, ć, ž, š, đ).
Koristi: šta (ne "što"), ljekar (ne "liječnik" ni "lekar"), sedmica (ne "tjedan" ni "nedelja"),
hiljada (ne "tisuća"), uslov (ne "uvjet"), apoteka (ne "ljekarna"), dodatak prehrani,
historija (ne "povijest"), takođe, općenito, hemija, sedmično, mjesec.
Nikad ekavicu i nikad hrvatske oblike."""

# ─── DB funkcije ──────────────────────────────────────────────────────────────
# ─── Lozinke ─────────────────────────────────────────────────────────────────
# Do septembra 2026. lozinke su čuvane kao goli SHA-256 bez soli — takav hash se
# razbija gotovim tablicama ako baza ikad procuri. Prelazi se na bcrypt, ali bez
# prekida za korisnike: stari hash se i dalje prihvata pri prijavi i tada se
# odmah tiho prepisuje bcrypt hashom (vidi migriraj_hash u db_login).
BROJ_PROMASAJA_ZA_ZAKLJUCAVANJE = 5
ZAKLJUCAVANJE_MINUTA = 15


def hash_loz(lozinka: str) -> str:
    """Legacy SHA-256. Ostaje samo da se stare lozinke mogu provjeriti."""
    return hashlib.sha256(lozinka.encode()).hexdigest()


def hash_loz_bcrypt(lozinka: str) -> str:
    return bcrypt.hashpw(lozinka.encode(), bcrypt.gensalt()).decode()


def provjeri_lozinku(lozinka: str, sacuvani_hash: str):
    """Vraća (tačna_lozinka, treba_migraciju)."""
    h = sacuvani_hash or ""
    if h.startswith("$2"):                      # bcrypt
        try:
            return bcrypt.checkpw(lozinka.encode(), h.encode()), False
        except ValueError:
            return False, False
    return secrets.compare_digest(h, hash_loz(lozinka)), True


def nadimak_za(korisnik, email=""):
    """Javno ime na ljestvici. Pravo ime i institucija se tamo nikad ne prikazuju.

    Zatečeni korisnici nemaju nadimak — dok ga ne postave dobijaju stabilnu
    neutralnu oznaku izvedenu iz emaila, koja ne otkriva ko su.
    """
    n = (korisnik or {}).get("nadimak") or ""
    if n.strip():
        return n.strip()
    em = (korisnik or {}).get("email") or email or ""
    return "Farmaceut-" + hashlib.sha256(em.encode()).hexdigest()[:4].upper()


def je_admin(korisnik=None):
    """Uloga iz baze, uz email kao sigurnosnu mrežu.

    ADMIN_EMAIL ostaje kao fallback da pogrešan upis u koloni 'role' nikad ne
    zaključa Semira izvan admin panela.
    """
    k = korisnik if korisnik is not None else (st.session_state.get("korisnik") or {})
    return (k.get("role") == "admin") or (k.get("email", "") == ADMIN_EMAIL)


def je_mentor(korisnik=None):
    k = korisnik if korisnik is not None else (st.session_state.get("korisnik") or {})
    return k.get("role") in ("mentor", "admin") or je_admin(k)


def db_postavi_ulogu(email, uloga):
    if not db:
        return False, "Baza podataka nije dostupna."
    if uloga not in ("korisnik", "mentor", "admin"):
        return False, "Nepoznata uloga."
    if email == ADMIN_EMAIL and uloga != "admin":
        return False, "Glavnom administratoru se uloga ne može oduzeti."
    try:
        db.table("users").update({"role": uloga}).eq("email", email).execute()
        return True, "ok"
    except Exception as e:
        zabiljezi_gresku(e)
        return False, f"Greška: {e}"


def nadimak_slobodan(nadimak, email):
    if not db:
        return True
    try:
        r = db.table("users").select("email, nadimak").execute()
        n = nadimak.strip().lower()
        return not any((u.get("nadimak") or "").strip().lower() == n
                       and u["email"] != email for u in (r.data or []))
    except Exception:
        return True


def db_postavi_nadimak(email, nadimak):
    if not db:
        return False, "Baza podataka nije dostupna."
    n = (nadimak or "").strip()
    if len(n) < 3:
        return False, "Nadimak mora imati najmanje 3 znaka."
    if len(n) > 24:
        return False, "Nadimak može imati najviše 24 znaka."
    if "@" in n:
        return False, "Nadimak ne smije sadržavati email adresu."
    if not nadimak_slobodan(n, email):
        return False, "Taj nadimak je već zauzet. Izaberite drugi."
    try:
        db.table("users").update({"nadimak": n}).eq("email", email).execute()
        return True, "ok"
    except Exception as e:
        zabiljezi_gresku(e)
        return False, f"Greška: {e}"


def db_registruj(email, lozinka, ime, institucija, nadimak=""):
    if not db:
        return False, "Baza podataka nije dostupna."
    try:
        r = db.table("users").select("email").eq("email", email.lower().strip()).execute()
        if r.data:
            return False, "Email je već registrovan."
        db.table("users").insert({
            "email": email.lower().strip(),
            "password_hash": hash_loz_bcrypt(lozinka),
            "full_name": ime.strip(),
            "institution": institucija.strip(),
            "nadimak": (nadimak or "").strip() or None,
            "approved": False,   # pristup odobrava iskljucivo admin, rucno
        }).execute()
        return True, "ok"
    except Exception as e:
        zabiljezi_gresku(e)
        return False, f"Greška: {e}"


def _minuta_do(vrijeme_iso):
    try:
        do = datetime.fromisoformat(vrijeme_iso.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return 0
    return max(0, int((do - datetime.now(timezone.utc)).total_seconds() // 60) + 1)


def db_login(email, lozinka):
    if not db:
        return None, "Baza podataka nije dostupna."
    try:
        em = email.lower().strip()
        r = db.table("users").select("*").eq("email", em).execute()
        # Ista poruka za nepostojeći email i za pogrešnu lozinku — inače ekran
        # prijave sam otkriva ko je registrovan.
        if not r.data:
            return None, "Pogrešan email ili lozinka."
        k = r.data[0]

        zakljucan_do = k.get("locked_until")
        if zakljucan_do and _minuta_do(zakljucan_do) > 0:
            return None, (f"Nalog je zaključan zbog previše pogrešnih pokušaja. "
                          f"Pokušajte ponovo za {_minuta_do(zakljucan_do)} min.")

        tacna, treba_migraciju = provjeri_lozinku(lozinka, k.get("password_hash"))
        if not tacna:
            promasaji = int(k.get("failed_logins") or 0) + 1
            izmjena = {"failed_logins": promasaji}
            if promasaji >= BROJ_PROMASAJA_ZA_ZAKLJUCAVANJE:
                izmjena["locked_until"] = (
                    datetime.now(timezone.utc) + timedelta(minutes=ZAKLJUCAVANJE_MINUTA)
                ).isoformat()
            try:
                db.table("users").update(izmjena).eq("email", em).execute()
            except Exception:
                pass        # brojač ne smije oboriti prijavu ako kolone još nema
            if promasaji >= BROJ_PROMASAJA_ZA_ZAKLJUCAVANJE:
                return None, (f"Nalog je zaključan na {ZAKLJUCAVANJE_MINUTA} min zbog "
                              f"{promasaji} pogrešna pokušaja prijave.")
            preostalo = BROJ_PROMASAJA_ZA_ZAKLJUCAVANJE - promasaji
            return None, f"Pogrešan email ili lozinka. Preostalo pokušaja: {preostalo}."

        # Uspjeh: brojač na nulu, i tiha migracija starog SHA-256 hasha na bcrypt.
        izmjena = {"failed_logins": 0, "locked_until": None}
        if treba_migraciju:
            izmjena["password_hash"] = hash_loz_bcrypt(lozinka)
        try:
            db.table("users").update(izmjena).eq("email", em).execute()
            k.update(izmjena)
        except Exception as e:
            zabiljezi_gresku(e)

        if k.get("suspended", False):
            return None, "Vaš nalog je privremeno suspendovan. Kontaktirajte administratora."
        if not k.get("approved", False):
            return None, ("Vaš nalog čeka odobrenje administratora. Pristup je otvoren samo članovima "
                          f"Edu Pharma Community. Kontakt: {KONTAKT_EMAIL}")
        return k, "ok"
    except Exception as e:
        zabiljezi_gresku(e)
        return None, f"Greška: {e}"


def db_zavrseni_scenariji(email):
    """Svi završeni scenariji jednim upitom.

    Lista scenarija je ranije zvala db_vec_uradio dvaput po scenariju, a
    Streamlit prerenderuje pri svakoj interakciji — uz 15 scenarija to je 30
    upita po kliku.
    """
    if not db:
        return set()
    try:
        r = db.table("attempts").select("scenario_id").eq("user_email", email).execute()
        return {a["scenario_id"] for a in (r.data or [])}
    except Exception:
        return set()


def db_vec_uradio(email, scenario_id):
    if not db:
        return False
    try:
        r = db.table("attempts").select("id").eq("user_email", email).eq("scenario_id", scenario_id).execute()
        return len(r.data) > 0
    except Exception:
        return False


def db_spremi(email, scenario_id, rezultat, transkript=""):
    if not db:
        return
    red = {
        "user_email": email,
        "scenario_id": scenario_id,
        "score": float(rezultat.get("ukupna_ocjena", 0)),
        "anamneza": int(rezultat.get("anamneza", 0)),
        "komunikacija": int(rezultat.get("komunikacija", 0)),
        "sigurnost": int(rezultat.get("sigurnost", 0)),
        "result_json": json.dumps(rezultat, ensure_ascii=False),
    }
    try:
        db.table("attempts").insert({**red, "transcript": transkript}).execute()
    except Exception:
        # Fallback ako kolona 'transcript' još ne postoji u bazi
        try:
            db.table("attempts").insert(red).execute()
        except Exception as e:
            # Gubitak rezultata korisnika — kritično, mora u log grešaka
            zabiljezi_gresku(e)


def db_dohvati_ocjenu(email, scenario_id):
    if not db:
        return None
    try:
        r = db.table("attempts").select("result_json").eq("user_email", email).eq("scenario_id", scenario_id).execute()
        if r.data and r.data[0].get("result_json"):
            return json.loads(r.data[0]["result_json"])
    except Exception:
        pass
    return None


def db_moji_rezultati(email):
    if not db:
        return []
    try:
        r = db.table("attempts").select("*").eq("user_email", email).order("completed_at", desc=True).execute()
        return r.data
    except Exception:
        return []


def db_leaderboard(period):
    if not db:
        return []
    try:
        now = datetime.now(timezone.utc)
        if period == "sedmicno":
            od = (now - timedelta(days=7)).isoformat()
        elif period == "mjesecno":
            od = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif period == "godisnje":
            od = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        else:
            od = "2020-01-01T00:00:00+00:00"

        r = db.table("attempts").select("user_email, score, anamneza, komunikacija, sigurnost").gte("completed_at", od).execute()
        if not r.data:
            return []

        skupovi = defaultdict(lambda: {"scores": [], "anamneza": [], "komunikacija": [], "sigurnost": []})
        for row in r.data:
            skupovi[row["user_email"]]["scores"].append(float(row["score"]))
            if row.get("anamneza") is not None:
                skupovi[row["user_email"]]["anamneza"].append(float(row["anamneza"]))
            if row.get("komunikacija") is not None:
                skupovi[row["user_email"]]["komunikacija"].append(float(row["komunikacija"]))
            if row.get("sigurnost") is not None:
                skupovi[row["user_email"]]["sigurnost"].append(float(row["sigurnost"]))

        emailovi = list(skupovi.keys())
        im = db.table("users").select("email, nadimak").in_("email", emailovi).execute()
        info = {u["email"]: u for u in im.data}

        lista = []
        for em, data in skupovi.items():
            k = info.get(em, {})
            scores = data["scores"]
            avg_a = round(sum(data["anamneza"]) / len(data["anamneza"]), 1) if data["anamneza"] else 0
            avg_k = round(sum(data["komunikacija"]) / len(data["komunikacija"]), 1) if data["komunikacija"] else 0
            avg_s = round(sum(data["sigurnost"]) / len(data["sigurnost"]), 1) if data["sigurnost"] else 0
            lista.append({
                "email": em,
                # Ljestvica je javna unutar zajednice — ide samo nadimak.
                "ime": nadimak_za(k, em),
                "institucija": "",
                "ukupno": round(sum(scores), 2),
                "slucajeva": len(scores),
                "prosjek": round(sum(scores) / len(scores), 2),
                "avg_anamneza": avg_a,
                "avg_komunikacija": avg_k,
                "avg_sigurnost": avg_s,
            })

        lista.sort(key=lambda x: x["ukupno"], reverse=True)
        return lista
    except Exception:
        return []


# ─── Admin DB funkcije ───────────────────────────────────────────────────────
def db_neodobreni_korisnici():
    if not db:
        return []
    try:
        r = db.table("users").select("*").eq("approved", False).execute()
        return r.data or []
    except Exception:
        return []


def db_odobri_korisnika(email):
    if not db:
        st.error("Baza podataka nije dostupna.")
        return False
    try:
        db.table("users").update({"approved": True}).eq("email", email).execute()
        return True
    except Exception as e:
        st.error(f"DB greška (odobri): {e}")
        return False


def db_odbij_korisnika(email):
    if not db:
        st.error("Baza podataka nije dostupna.")
        return False
    try:
        db.table("users").delete().eq("email", email).execute()
        return True
    except Exception as e:
        st.error(f"DB greška (odbij): {e}")
        return False


def db_svi_korisnici():
    if not db:
        return []
    try:
        r = db.table("users").select("*").eq("approved", True).order("full_name").execute()
        return r.data or []
    except Exception:
        return []


def db_resetuj_lozinku(email):
    """Postavlja privremenu lozinku i vraća je (None uz grešku)."""
    if not db:
        st.error("Baza podataka nije dostupna.")
        return None
    try:
        abeceda = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
        privremena = "".join(secrets.choice(abeceda) for _ in range(10))
        db.table("users").update({"password_hash": hash_loz_bcrypt(privremena),
                                  "failed_logins": 0, "locked_until": None}).eq("email", email).execute()
        return privremena
    except Exception as e:
        st.error(f"DB greška (reset lozinke): {e}")
        return None


def db_postavi_suspenziju(email, suspendovan):
    if not db:
        st.error("Baza podataka nije dostupna.")
        return False
    try:
        db.table("users").update({"suspended": suspendovan}).eq("email", email).execute()
        return True
    except Exception as e:
        st.error(f"DB greška (suspenzija): {e}")
        return False


def db_pokusaji_korisnika(email):
    """Svi pokušaji jednog korisnika, s transkriptom (za admin pregled)."""
    if not db:
        return []
    try:
        r = db.table("attempts").select("*").eq("user_email", email).order("completed_at", desc=True).execute()
        return r.data or []
    except Exception:
        return []


def db_obrisi_sve_podatke(email):
    """GDPR brisanje: uklanja nalog i SVE povezane podatke (pokušaji,
    transkripti, žalbe, log korištenja)."""
    if not db:
        st.error("Baza podataka nije dostupna.")
        return False
    try:
        db.table("attempts").delete().eq("user_email", email).execute()
        db.table("usage_log").delete().eq("user_email", email).execute()
        db.table("users").delete().eq("email", email).execute()
        return True
    except Exception as e:
        zabiljezi_gresku(e)
        st.error(f"DB greška (GDPR brisanje): {e}")
        return False


def db_svi_pokusaji_export():
    """Svi pokušaji (bez transkripta) za CSV export."""
    if not db:
        return []
    try:
        r = db.table("attempts").select(
            "user_email, scenario_id, score, anamneza, komunikacija, sigurnost, "
            "completed_at, appeal_status"
        ).order("completed_at", desc=True).execute()
        return r.data or []
    except Exception as e:
        zabiljezi_gresku(e)
        return []


def napravi_csv(zaglavlje, redovi):
    """Gradi CSV bajtove (UTF-8 sa BOM-om, ';' separator — radi u Excelu)."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\n")
    w.writerow(zaglavlje)
    w.writerows(redovi)
    return buf.getvalue().encode("utf-8-sig")


# ─── Žalbe na ocjenu ─────────────────────────────────────────────────────────
def db_posalji_zalbu(attempt_id, tekst):
    if not db:
        return False, "Baza podataka nije dostupna."
    try:
        db.table("attempts").update({
            "appeal_status": "otvorena",
            "appeal_text": tekst.strip(),
        }).eq("id", attempt_id).execute()
        return True, "ok"
    except Exception as e:
        return False, f"Greška: {e}"


def db_otvorene_zalbe():
    if not db:
        return []
    try:
        r = db.table("attempts").select("*").eq("appeal_status", "otvorena").order("completed_at", desc=True).execute()
        return r.data or []
    except Exception:
        return []


def db_rijesi_zalbu(attempt_id, status, odgovor, nove_ocjene=None):
    """Zatvara žalbu ('rijesena'/'odbijena'); opcionalno ispravlja ocjene."""
    if not db:
        st.error("Baza podataka nije dostupna.")
        return False
    try:
        payload = {"appeal_status": status, "appeal_response": odgovor.strip()}
        if nove_ocjene:
            a = int(nove_ocjene["anamneza"])
            k = int(nove_ocjene["komunikacija"])
            s = int(nove_ocjene["sigurnost"])
            ukupna = round(a * 0.4 + k * 0.3 + s * 0.3, 2)
            payload.update({"anamneza": a, "komunikacija": k, "sigurnost": s, "score": ukupna})
            r = db.table("attempts").select("result_json").eq("id", attempt_id).execute()
            if r.data and r.data[0].get("result_json"):
                rez = json.loads(r.data[0]["result_json"])
                rez.update({
                    "anamneza": a, "komunikacija": k, "sigurnost": s,
                    "ukupna_ocjena": ukupna, "korigovano_od_admina": True,
                })
                payload["result_json"] = json.dumps(rez, ensure_ascii=False)
        db.table("attempts").update(payload).eq("id", attempt_id).execute()
        return True
    except Exception as e:
        st.error(f"DB greška (žalba): {e}")
        return False


# ─── Log korištenja — analitika, troškovi, dnevni limit ──────────────────────
def db_log_upotrebu(event, scenario_id="", tokens_in=0, tokens_out=0):
    if not db:
        return
    try:
        db.table("usage_log").insert({
            "user_email": st.session_state.get("korisnik_email", ""),
            "event": event,
            "scenario_id": scenario_id,
            "tokens_in": int(tokens_in),
            "tokens_out": int(tokens_out),
        }).execute()
    except Exception:
        pass


def db_poruka_danas(email):
    """Broj AI poruka korisnika danas (za dnevni limit). Fail-open na 0."""
    if not db:
        return 0
    try:
        od = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        r = (db.table("usage_log").select("id", count="exact")
             .eq("user_email", email).eq("event", "poruka").gte("created_at", od).execute())
        return r.count or 0
    except Exception:
        return 0


def db_statistika():
    """Sirovi podaci za admin statistiku (pokušaji, korisnici, upotreba 30 dana)."""
    if not db:
        return None
    try:
        pokusaji = db.table("attempts").select(
            "user_email, scenario_id, score, completed_at").execute().data or []
        korisnici = db.table("users").select("email, approved").execute().data or []
        od30 = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        upotreba = db.table("usage_log").select(
            "user_email, event, scenario_id, tokens_in, tokens_out, created_at"
        ).gte("created_at", od30).execute().data or []
        return {"pokusaji": pokusaji, "korisnici": korisnici, "upotreba": upotreba}
    except Exception:
        return None


# ─── CMS: scenariji iz baze ──────────────────────────────────────────────────
@st.cache_data(ttl=120)
def _ucitaj_db_scenarije():
    """Scenariji iz Supabase — nadjačavaju/dopunjuju ugrađene (isti id)."""
    if not db:
        return {}
    try:
        r = db.table("scenarios").select("*").execute()
        out = {}
        for red in r.data or []:
            out[red["id"]] = {
                "naziv": red.get("naziv") or red["id"],
                "ime": red.get("ime") or "",
                "godine": red.get("godine") or 0,
                "tegoba": red.get("tegoba") or "",
                "terapija": red.get("terapija") or "",
                "skriveni_detalji": red.get("skriveni_detalji") or "",
                "crvene_zastavice": red.get("crvene_zastavice") or "",
                "ocekivano": red.get("ocekivano") or "",
                "pocetna_poruka": red.get("pocetna_poruka") or "",
                "rubrika": red.get("rubrika") or "",
                "aktivan": bool(red.get("active", False)),
                "_iz_baze": True,
            }
        return out
    except Exception:
        return {}


def db_scenarij_spremi(sid, podaci):
    """Upsert scenarija u bazu (podaci = dict s poljima tabele scenarios)."""
    if not db:
        st.error("Baza podataka nije dostupna.")
        return False
    try:
        db.table("scenarios").upsert({"id": sid.strip(), **podaci}).execute()
        _ucitaj_db_scenarije.clear()
        return True
    except Exception as e:
        st.error(f"DB greška (scenarij): {e}")
        return False


def db_scenarij_aktivan(sid, aktivan):
    if not db:
        return False
    try:
        db.table("scenarios").update({"active": aktivan}).eq("id", sid).execute()
        _ucitaj_db_scenarije.clear()
        return True
    except Exception as e:
        st.error(f"DB greška (scenarij): {e}")
        return False


def db_scenarij_obrisi(sid):
    if not db:
        return False
    try:
        db.table("scenarios").delete().eq("id", sid).execute()
        _ucitaj_db_scenarije.clear()
        return True
    except Exception as e:
        st.error(f"DB greška (scenarij): {e}")
        return False


# ─── Objave / banner ─────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def _ucitaj_objave():
    if not db:
        return []
    try:
        r = (db.table("announcements").select("*")
             .eq("active", True).order("created_at", desc=True).execute())
        return r.data or []
    except Exception:
        return []


def db_objave_sve():
    if not db:
        return []
    try:
        r = db.table("announcements").select("*").order("created_at", desc=True).execute()
        return r.data or []
    except Exception:
        return []


def db_objava_nova(tekst, tip):
    if not db:
        st.error("Baza podataka nije dostupna.")
        return False
    try:
        db.table("announcements").insert({"tekst": tekst.strip(), "tip": tip, "active": True}).execute()
        _ucitaj_objave.clear()
        return True
    except Exception as e:
        st.error(f"DB greška (objava): {e}")
        return False


def db_objava_aktivna(oid, aktivna):
    if not db:
        return False
    try:
        db.table("announcements").update({"active": aktivna}).eq("id", oid).execute()
        _ucitaj_objave.clear()
        return True
    except Exception as e:
        st.error(f"DB greška (objava): {e}")
        return False


def db_objava_obrisi(oid):
    if not db:
        return False
    try:
        db.table("announcements").delete().eq("id", oid).execute()
        _ucitaj_objave.clear()
        return True
    except Exception as e:
        st.error(f"DB greška (objava): {e}")
        return False


# ─── Email notifikacije (Resend) ─────────────────────────────────────────────
def posalji_email(to_email, subject, html):
    """Generičko slanje jednog emaila preko Resend HTTP API-ja."""
    try:
        api_key = st.secrets.get("RESEND_API_KEY", "")
        from_email = st.secrets.get("RESEND_FROM", "onboarding@resend.dev")

        if not api_key:
            return False, "RESEND_API_KEY nije konfigurisan u secrets."

        payload = json.dumps({
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html,
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status in (200, 201):
                return True, "ok"
            else:
                return False, f"Resend status: {resp.status}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        zabiljezi_gresku(e)
        return False, f"Resend HTTP {e.code}: {body}"
    except Exception as e:
        zabiljezi_gresku(e)
        return False, str(e)


def email_okvir(sadrzaj_html):
    """Zajednički HTML okvir (header + footer) za sve emailove."""
    return f"""
    <div style="font-family:Inter,sans-serif;max-width:520px;margin:0 auto;padding:32px">
        <div style="text-align:center;margin-bottom:24px">
            <h2 style="color:#1E3A8A;margin:0">Clinical Case Simulator</h2>
            <p style="color:#64748b;margin:4px 0 0">Edu Pharma Community</p>
        </div>
        {sadrzaj_html}
        <p style="color:#64748b;font-size:13px;margin-top:24px;border-top:1px solid #e2e8f0;padding-top:16px">
            Edu Pharma Community · Farmaceutski trening
        </p>
    </div>
    """


def posalji_email_odobrenje(korisnik_email, korisnik_ime):
    sadrzaj = f"""
        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:20px;text-align:center;margin-bottom:20px">
            <div style="font-size:18px;font-weight:600;color:#166534;margin-bottom:8px">&#10003;</div>
            <div style="font-size:18px;font-weight:600;color:#166534">Nalog odobren!</div>
        </div>
        <p style="color:#1e293b;font-size:15px;line-height:1.6">
            Poštovani/a <strong>{korisnik_ime}</strong>,
        </p>
        <p style="color:#1e293b;font-size:15px;line-height:1.6">
            Vaš nalog na platformi <strong>Clinical Case Simulator</strong> je odobren.
            Sada se možete prijaviti i započeti rad na kliničkim scenarijima.
        </p>
    """
    return posalji_email(
        korisnik_email,
        "Vaš nalog je odobren — Clinical Case Simulator",
        email_okvir(sadrzaj),
    )


def posalji_email_masovni(to_email, korisnik_ime, subject, poruka_tekst):
    """Masovni email — čisti tekst admina pretvara u HTML unutar okvira."""
    tijelo = poruka_tekst.strip().replace("\n", "<br>")
    sadrzaj = f"""
        <p style="color:#1e293b;font-size:15px;line-height:1.6">
            Poštovani/a <strong>{korisnik_ime}</strong>,
        </p>
        <p style="color:#1e293b;font-size:15px;line-height:1.6">{tijelo}</p>
    """
    return posalji_email(to_email, subject, email_okvir(sadrzaj))


# ─── Scenariji ────────────────────────────────────────────────────────────────
SCENARIJI = {
    "scenarij_1": {
        "naziv": "Scenarij 1 — Trudnica i topikalni kortikosteroidi",
        "ime": "Lejla",
        "godine": 18,
        "tegoba": "svrbež i peckanje kože na grudima, dolazi po još Clobetasol kremu",
        "terapija": "vitamini za trudnoću (33. sedmica trudnoće, prva trudnoća)",
        "skriveni_detalji": (
            "već 6 mjeseci koristi Zalim losion i Clobetasol 0.05% kremu zajedno svakodnevno; "
            "na koži su se pojavile strije i sjajne mrlje koje pripisuje trudnoći; "
            "nije bila kod ljekara, uzela preparate po preporuci komšinice"
        ),
        "crvene_zastavice": (
            "Clobetasol 0.05% kontraindiciran u trudnoći; "
            "Zalim losion (fenol) toksičan u trudnoći; "
            "6 mjeseci primjene = aktivne nuspojave; hitno uputiti ginekologu i dermatologu"
        ),
        "ocekivano": (
            "Pita o trudnoći i gestacijskoj sedmici; pita šta već koristi i koliko dugo; "
            "prepoznaje Clobetasol kao superpotentni TC kontraindiciran u trudnoći; "
            "odbija izdati bez recepta; savjetuje prekid oba preparata i hitnu posjetu ljekaru."
        ),
        "pocetna_poruka": "Dobro jutro, trebala bih još jednu Clobetasol kremu, ponestaje mi.",
        "rubrika": """Ocijeni po ovim kategorijama (svaka 0-10):

ANAMNEZA (tezina 0.4): pitao trajanje tegobe(2), sta koristi i koliko dugo(2), trudnocu/stanja(2), alergije(2), prepoznao zastavice(2)
KAZNA: bez pitanja o trudnoci max 4/10; bez pitanja sta koristi max 6/10

KOMUNIKACIJA (tezina 0.3): jezik laika(2), empatija bez osudjivanja(2), provjerio razumijevanje(2), strukturisan razgovor(2), jasna poruka(2)

SIGURNOST (tezina 0.3): odbio Clobetasol bez recepta(3), savjetovao prekid oba preparata(3), nije predlozio zamjensku terapiju(2), uputio ljekaru(2)
KAZNA: dao kortikosteroid trudnici = 0/10 za Sigurnost""",
    },
    "scenarij_2": {
        "naziv": "Scenarij 2 — Palpitacije i biljni dodatak prehrani",
        "ime": "Amra",
        "godine": 33,
        "tegoba": "epizode lupanja srca koje traju već nekoliko dana, došla po nešto za smirenje",
        "terapija": "od prije 3 mjeseca koristi lijekove na recept, kvetiapin 100 mg i sertralin 50 mg",
        "skriveni_detalji": (
            "Ima bračne probleme i osjećaj potištenosti koji traje oko mjesec dana; "
            "prije tri sedmice počela uzimati biljni dodatak prehrani u kapsulama koji joj je preporučila prijateljica "
            "(na kutiji piše da je biljka sa žutim cvijetom, uzima 300 mg dnevno); "
            "od prošle sedmice ima znojenje, nesanicu i česte epizode lupanja srca, "
            "i u mirovanju i pri naporu, traju manje od minut i prestanu same; "
            "sinoć je bila na plesanju salse i na plesnom podiju joj je srce počelo jako lupati, "
            "trajalo je oko minut i uplašila se; "
            "bila je kod ljekara — na prijemu su joj izmjerili puls 150-160 otkucaja, "
            "krvni pritisak 110/68, uradili EKG koji je pokazao supraventrikularnu tahikardiju, "
            "svi laboratorijski nalazi uredni (krvna slika, biohemija, troponin negativan), "
            "uradili su ultrazvuk srca koji je bio potpuno uredan; "
            "ljekar joj je rekao da je srce strukturno zdravo i da prekine sa tim biljnim dodatkom; "
            "nije rekla ljekaru tačno šta uzima jer joj je bilo neugodno; "
            "nema bolova u grudima, nema otežanog disanja, nije se onesvijestila; "
            "ne koristi nikakve druge lijekove, ne puši, ne pije alkohol redovno"
        ),
        "crvene_zastavice": (
            "Biljni dodatak sa žutim cvijetom = kantarion (Hypericum perforatum); "
            "kantarion može izazvati supraventrikularnu tahikardiju čak i bez prethodne srčane bolesti; "
            "vremenski slijed: simptomi počeli 3 sedmice nakon početka uzimanja; "
            "kantarion je induktor CYP 3A4 enzima i može uzrokovati opasne interakcije sa mnogim lijekovima; "
            "simptomi znojenja i nesanice mogu ukazivati na serotonergičke efekte kantariona; "
            "potrebno je odmah prekinuti uzimanje dodatka i uputiti na kontrolu kod ljekara/kardiologa"
        ),
        "ocekivano": (
            "Pita kako se osjeća i koje simptome ima; pita koliko dugo traju palpitacije i kada su počele; "
            "pita da li uzima neke lijekove, dodatke prehrani ili biljne preparate; "
            "pita detalje o biljnom dodatku (šta piše na kutiji, koliko dugo ga uzima, ko joj ga je preporučio); "
            "prepoznaje vezu između biljnog dodatka (kantarion) i palpitacija; "
            "pita da li je bila kod ljekara i šta su joj rekli; "
            "savjetuje da odmah prestane uzimati biljni dodatak; "
            "objašnjava da biljni dodaci nisu bezopasni i da mogu imati ozbiljne nuspojave; "
            "uputuje na kontrolu kod kardiologa; "
            "ne preporučuje zamjenski biljni preparat za raspoloženje bez konsultacije sa ljekarom."
        ),
        "pocetna_poruka": "Dobar dan. Imate li nešto za smirenje? Srce mi lupa već danima, ne znam šta da radim.",
        "rubrika": """Ocijeni po ovim kategorijama (svaka 0-10):

ANAMNEZA (tezina 0.4): pitao koliko dugo traju simptomi i kada su poceli(2), pitao koje lijekove/dodatke prehrani koristi(2), pitao detalje o biljnom dodatku (opis, doza, trajanje)(2), pitao da li je bila kod ljekara i sta su utvrdili(2), prepoznao vezu kantarion-palpitacije(2)
KAZNA: bez pitanja o dodacima prehrani/biljnim preparatima max 3/10; bez pitanja da li je posjetila ljekara max 5/10

KOMUNIKACIJA (tezina 0.3): jezik laika bez medicinskog zargona(2), empatija i razumijevanje za strah pacijentice(2), provjerio da li je razumjela savjete(2), strukturisan razgovor sa logicnim redoslijedom pitanja(2), jasna i nedvosmislena poruka o prekidu dodatka(2)

SIGURNOST (tezina 0.3): savjetovao odmah prekid biljnog dodatka(3), objasnio da biljni preparati mogu imati ozbiljne nuspojave(2), uputio na kontrolu kod kardiologa/ljekara(3), nije preporucio zamjenski biljni preparat bez konsultacije sa ljekarom(2)
KAZNA: preporucio nastavak uzimanja biljnog dodatka = 0/10 za Sigurnost; preporucio drugi biljni lijek za raspolozenje bez upucivanja ljekaru = max 3/10 za Sigurnost""",
    },
}

# ─── AI ───────────────────────────────────────────────────────────────────────
SCENARIJI.update(_ucitaj_db_scenarije())


# ─── Priručnik ponašanja pacijenta ───────────────────────────────────────────
# Statični blok — identičan za sve scenarije, pa se kešira (Anthropic kešira
# tek od 1024 tokena; raniji prompt od ~120 tokena nikad nije bio keširan).
# Zamjenjuje ranija pravila "ne otkrivaj bez pitanja" + "budi blago skeptičan",
# koja su zajedno činila ključne činjenice nedostižnim bez obzira na kvalitet
# razgovora (nalaz N1 iz revizije baze, 8. 9. 2026).
PACIJENT_PRIRUCNIK = """Ti glumiš pacijenta u javnoj apoteci u Bosni i Hercegovini. Farmaceut je
osoba s druge strane pulta. Nikad ne izlaziš iz uloge i nikad ne spominješ da si vještačka
inteligencija, model ni simulacija — čak i ako te farmaceut direktno pita.

KO SI
Ti si obična osoba, ne ljekar i ne udžbenik. Lijekove opisuješ laički: "one male bijele za
pritisak", "krema iz plave tube", "kesice što se rastope u vodi". Tačan naziv znaš izgovoriti
samo ako je u tvojim činjenicama i samo kad te farmaceut pita šta piše na kutiji ili ako imaš
kutiju kod sebe.

ŠTA ZNAŠ
Znaš isključivo ono što piše u tvojoj tegobi, terapiji i skrivenim činjenicama. To je jedini
izvor istine o tebi.
- Ako te pitaju nešto čega tamo nema, kažeš da ne znaš, da se ne sjećaš ili da nisi mjerila.
  NIKAD ne izmišljaš brojeve, datume, doze, nazive lijekova ni nalaze.
- Ako farmaceut u pitanje ugradi nešto što ti nisi rekao i što nije među tvojim činjenicama
  ("taj vaš bol u leđima...", "pošto vam se vrti u glavi..."), ispravi ga ili reci da to nisi
  spomenuo. NE prihvataš tuđe pretpostavke o sebi i ne slažeš se iz pristojnosti.
- Ako ti farmaceut sam ponudi dijagnozu ili objašnjenje, možeš reagovati ("aha", "nisam znala"),
  ali ne potvrđuješ simptom koji nemaš.

KADA OTKRIVAŠ, A KADA ŠUTIŠ — najvažnije pravilo
Ti sam od sebe ne iznosiš skrivene činjenice. Ali čim farmaceut postavi pitanje koje pokriva
neku od njih, tu činjenicu MORAŠ dati. Šutnja je dozvoljena samo dok pitanje nije postavljeno.
- Pitanje pokriva činjenicu i kad nije doslovno: "uzimate li još nešto?", "pijete li kakve
  dodatke, čajeve ili vitamine?", "ima li još nešto što uzimate na svoju ruku?" — sve to
  pokriva biljne preparate, suplemente i OTC lijekove. Odgovaraš kao laik ("uzimam neke
  kapsule, prijateljica mi preporučila"), ali ne poričeš da ih uzimaš.
- Činjenicu koju prešućuješ zbog stida ili straha daješ na drugo postavljanje istog pitanja,
  ili odmah ako je farmaceut objasnio zašto pita ili pokazao razumijevanje. Možeš oklijevati
  jednu repliku ("pa... ne znam je li to bitno..."), ali onda kažeš.
- NIKAD ne odgovaraš "ne uzimam ništa" ako u tvojim činjenicama piše da nešto uzimaš. Umjesto
  poricanja koristi oklijevanje, umanjivanje ili laičko opisivanje ("to nije lijek, to je
  prirodno").
- Nikad ne odgovaraš na pitanje koje farmaceut nije postavio, i nikad ne izgovaraš zaključak
  umjesto njega.

KAKO GOVORIŠ
Dužina zavisi od pitanja, ne od pravila. Na otvoreno pitanje ("kako se osjećate?", "pričajte
mi") odgovaraš s dvije do četiri rečenice i smiješ ubaciti digresiju iz svakodnevice — unuk,
posao, komšiluk, red kod ljekara. Na zatvoreno pitanje odgovaraš kratko, jednom ili dvjema
rečenicama.
- Ako farmaceut u jednoj poruci postavi tri ili više pitanja, odgovoriš na prva dva i kažeš da
  ne stižeš sve ("polako, šta ste ono prvo pitali?"). To je normalna ljudska reakcija.
- Ako farmaceut upotrijebi stručni izraz bez objašnjenja (kontraindikacija, interakcija,
  CYP3A4, superpotentni, adherencija, aura), a ti nisi visokoobrazovana osoba, pitaš šta to
  znači ili pokažeš da si pogrešno razumjela.
- Ako te farmaceut pita jesi li razumjela, ponavljaš savjet svojim riječima. Ako je objašnjenje
  bilo žargonsko ili nejasno, ponavljaš ga pogrešno.
- Govoriš prirodnim sarajevskim govorom: "ba", "bolan", "hajde", "šta ću", "eto", "hvala Bogu",
  "je l' da", skraćeno "'oću", "'ajmo". Registar je razgovorni, ne knjiški, ali bez vulgarnosti
  i bez pretjerivanja — jedna do dvije takve riječi po replici, ne više.

DRŽANJE
Došao si sa svojim zahtjevom i držiš ga se dok ti farmaceut ne dâ razlog da odustaneš. Smiješ
pitati svoje: koliko košta, ima li nešto jeftinije, koliko brzo djeluje, je li opasno. Ako te
farmaceut odbije bez objašnjenja, ne prihvataš to odmah — pitaš zašto ili ponoviš zahtjev
jednom. Ako ti objasni konkretan rizik i ponudi šta dalje, popuštaš.

FORMAT
Odgovaraš samo replikom pacijenta, u prvom licu, bez navodnika i bez imena ispred. Bez
opisa scene, bez uputa farmaceutu i bez komentara izvan uloge."""


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


# ─── Ocjenjivač ──────────────────────────────────────────────────────────────
# Raniji poziv nije imao sistemski prompt, temperaturu ni obavezan dokaz, pa je
# model sam birao metodologiju i pod naslov "propuštena pitanja" upisivao sve
# što nije SAZNATO — uključujući i ono što je farmaceut uredno pitao, a pacijent
# uskratio (nalaz N2). Otud dvokorak: prvo ispiši sva pitanja doslovno, pa tek
# onda sudi, i to samo o onome čega u tom popisu nema.
EVALUATOR_SISTEM = """Ti si iskusan mentor u javnoj apoteci u Bosni i Hercegovini i ocjenjuješ
farmaceutsko savjetovanje u simulaciji. Ocjenjuješ pošteno, po dokazima iz transkripta, i
nikad ne izmišljaš propuste.

RADIŠ U DVA KORAKA — redoslijed je obavezan.

KORAK 1 — POPIS. Prije bilo kakvog suda pročitaj transkript i doslovno ispiši SVAKO pitanje i
svaki zahtjev koji je farmaceut uputio pacijentu, redom, u polje "pitanja_farmaceuta". Prepisuješ
tačno onako kako je napisano, uključujući pravopisne greške. Ako je u jednoj poruci više pitanja,
svako ide kao zaseban unos.

KORAK 2 — SUD. Tek sada ocjenjuješ, i to isključivo na osnovu tog popisa i transkripta.

PRAVILA KOJA SE NE SMIJU PREKRŠITI:

1. PITANO NIJE ISTO ŠTO I SAZNATO. Ako je farmaceut postavio pitanje, a pacijent uskratio,
   umanjio ili porekao odgovor, to je ponašanje pacijenta — NE propust farmaceuta. Takav slučaj
   ide u "pitano_ali_neodgovoreno" i boduje se KAO DA je pitanje postavljeno, jer i jeste.
   U "nije_pitano" smije ući samo ono čega u popisu iz koraka 1 nema ni u širem smislu.
   Šire znači: "uzimate li još nešto?" pokriva biljne preparate, suplemente i OTC lijekove;
   "koliko dugo?" pokriva vremenski slijed; "jeste li bili kod ljekara?" pokriva nalaze.
   Prije nego išta upišeš u "nije_pitano", provjeri popis još jednom.

2. SVAKA POHVALA I SVAKI UNOS U "pitano_ali_neodgovoreno" MORA NOSITI DOSLOVAN CITAT iz
   transkripta. Citat prepisuješ znak po znak. Tvrdnja bez citata bit će odbačena prije nego
   je polaznik vidi, pa je nemoj ni pisati.

3. RAZGOVOR JE OGRANIČEN BROJEM POTEZA. Broj je naveden u zadatku. Ne kažnjavaš farmaceuta zato
   što nije stigao produbiti ono što je pacijent iznio u posljednjoj ili pretposljednjoj replici —
   nije imao potez na raspolaganju. Ako je farmaceut ispravno reagovao na kasno otkriven podatak,
   to je pohvala, ne propust.

4. NE KAŽNJAVAŠ DVAPUT. Isti propust ne ide i u "nije_pitano" i u "smjernice" kao zasebna stavka.

5. KAZNE IZ RUBRIKE primjenjuješ doslovno i navodiš ih u "kazne_primijenjene". Kazna vezana za
   pitanje koje jeste postavljeno (vidi pravilo 1) se NE primjenjuje.

BODOVANJE. Anamneza, komunikacija i sigurnost svaka 0-10, po kriterijima iz rubrike.
Ukupna ocjena = anamneza x 0.4 + komunikacija x 0.3 + sigurnost x 0.3, zaokruženo na jednu
decimalu. Izračunaj pažljivo.

TON. Pišeš polazniku, ne o njemu. Konkretno, bez fraza, bez moralisanja. Smjernice su upute za
sljedeći put, a ne prepričavanje propusta.

""" + JEZIK_PRAVILO


EVALUATOR_SHEMA = """{
 "pitanja_farmaceuta": ["doslovan citat svakog pitanja/zahtjeva farmaceuta, redom"],
 "anamneza": <0-10>,
 "komunikacija": <0-10>,
 "sigurnost": <0-10>,
 "ukupna_ocjena": <0.0-10.0>,
 "nije_pitano": [{"pitanje": "šta je trebalo pitati", "zasto_vazno": "jedna rečenica"}],
 "pitano_ali_neodgovoreno": [{"pitanje": "šta je farmaceut pitao",
                              "citat_farmaceuta": "doslovan citat iz transkripta",
                              "reakcija_pacijenta": "kako je pacijent izbjegao odgovor"}],
 "kazne_primijenjene": ["naziv kazne iz rubrike koja je primijenjena"],
 "pohvale": [{"tekst": "šta je uradio dobro", "citat": "doslovan citat iz transkripta"}],
 "smjernice": ["konkretna uputa za sljedeći put"]
}"""


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


def _normalizuj(t):
    """Za poređenje citata: mala slova, bez dijakritike, bez interpunkcije i viška razmaka."""
    t = (t or "").lower()
    for a, b in (("č", "c"), ("ć", "c"), ("ž", "z"), ("š", "s"), ("đ", "d")):
        t = t.replace(a, b)
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def provjeri_ocjenu(r, transkript):
    """Odbacuje tvrdnje bez dokaza i preračunava ukupnu ocjenu u Pythonu.

    Model ne smije ni tvrditi ni računati bez provjere: citat koji se ne nalazi
    u transkriptu je izmišljen dokaz, a ponderisani zbir je aritmetika koju
    Python radi pouzdanije. Odbačene tvrdnje se čuvaju u 'odbaceno' za admina,
    ali se polazniku ne prikazuju.
    """
    if not isinstance(r, dict):
        return r
    tn = _normalizuj(transkript)
    odbaceno = []

    def ima_dokaz(citat):
        c = _normalizuj(citat)
        # Kratak citat je preslab dokaz da bi se na njemu gradila tvrdnja.
        if len(c) < 12:
            return False
        return c in tn

    ocisceno = []
    for p in r.get("pohvale", []) or []:
        if isinstance(p, str):          # stari format — nema šta da se provjeri
            ocisceno.append(p)
        elif ima_dokaz(p.get("citat", "")):
            ocisceno.append(p)
        else:
            odbaceno.append({"vrsta": "pohvala", "sadrzaj": p})
    r["pohvale"] = ocisceno

    ocisceno = []
    for p in r.get("pitano_ali_neodgovoreno", []) or []:
        if isinstance(p, dict) and ima_dokaz(p.get("citat_farmaceuta", "")):
            ocisceno.append(p)
        else:
            odbaceno.append({"vrsta": "pitano_ali_neodgovoreno", "sadrzaj": p})
    r["pitano_ali_neodgovoreno"] = ocisceno

    if odbaceno:
        r["odbaceno"] = odbaceno

    # Ukupna ocjena se računa ovdje, ne u modelu.
    try:
        r["ukupna_ocjena"] = round(
            float(r.get("anamneza", 0)) * 0.4
            + float(r.get("komunikacija", 0)) * 0.3
            + float(r.get("sigurnost", 0)) * 0.3, 1)
    except (TypeError, ValueError):
        pass

    # Kompatibilnost: stari prikaz, žalbe i CSV izvoz čitaju 'propustena_pitanja'.
    if "nije_pitano" in r and "propustena_pitanja" not in r:
        r["propustena_pitanja"] = [
            n.get("pitanje", "") if isinstance(n, dict) else str(n)
            for n in (r.get("nije_pitano") or [])
        ]
    return r


def izvuci_json(tekst):
    p, k = tekst.find("{"), tekst.rfind("}") + 1
    if p == -1 or k == 0:
        return None
    try:
        return json.loads(tekst[p:k])
    except Exception:
        return None


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


# ─── AI Generator scenarija (admin) ──────────────────────────────────────────
GENERATOR_SISTEM = """Ti si arhitekta kliničkih simulacija za edukaciju farmaceuta — spoj kliničkog \
farmakologa, iskusnog javnog farmaceuta iz Bosne i Hercegovine i dizajnera OSCE ispita. \
Iz naučnog case reporta (PDF) gradiš scenarij za simulator u kojem AI glumi pacijenta koji ulazi \
u javnu apoteku, a farmaceut-polaznik kroz razgovor od najviše 10 poteza mora otkriti skriveni \
problem i sigurno savjetovati.

PRINCIPI DIZAJNA — svi su OBAVEZNI:

1. TRANSPOZICIJA U APOTEKU: Slučaj iz bolničkog/naučnog konteksta prebaci u realan prvi kontakt u \
apoteci u BiH — trenutak PRIJE postavljanja dijagnoze iz rada, kada je farmaceut mogao biti prva \
linija koja hvata problem. Pacijent dolazi s banalnim, svakodnevnim zahtjevom (nešto protiv bolova, \
"nešto za smirenje", ponovna kupovina preparata...) koji prikriva ozbiljan problem iz case reporta.

2. LOKALIZACIJA: Bosansko ime pacijenta, prirodan govor laika na bosanskom jeziku, lijekovi i \
dodaci prehrani koji realno postoje na tržištu BiH (koristi INN nazive ili brendove prisutne u BiH). \
Doze i klinički detalji moraju ostati vjerni case reportu.

3. SKRIVENI DETALJI: Pacijent NIŠTA ključno ne otkriva sam. Razbij kliničku sliku na 6-10 \
konkretnih činjenica koje se otkrivaju SAMO na ciljano pitanje (vremenski slijed simptoma, tačna \
terapija s dozama, OTC/biljni preparati, nalazi ljekara ako ih ima, navike, komorbiditeti). \
Pacijent lijekove opisuje kao laik ("male bijele tablete za pritisak"), ne farmakološki. \
Uključi i razlog zašto nešto prešućuje (stid, strah, misli da nije važno).

4. KRITIČKO RAZMIŠLJANJE — slučaj mora biti TEŽAK: \
(a) ugradi barem jedan lažni trag (red herring) — plauzibilno ali pogrešno objašnjenje koje se nudi \
površnom ispitivaču (npr. simptom liči na stres, menopauzu, "to je od godina"); \
(b) ključ rješenja je u POVEZIVANJU činjenica (vremenski slijed uzimanja i simptoma, interakcija, \
maskirana nuspojava), ne u jednoj očiglednoj informaciji; \
(c) atipična prezentacija iz case reporta treba ostati atipična — bez pojednostavljivanja.

5. CRVENE ZASTAVICE: Jasno navedi šta farmaceut mora prepoznati, mehanizam (interakcija, \
kontraindikacija, nuspojava — imenuj enzime/mehanizme gdje je relevantno) i koja je ispravna \
akcija (prekid, odbijanje izdavanja, hitno upućivanje — kome i zašto).

6. SIGURNOSNA LEKCIJA: Scenarij mora imati nedvosmislenu ispravnu odluku i barem jednu FATALNU \
grešku (npr. izdati traženi lijek, preporučiti simptomatsku terapiju koja maskira problem) koja se \
u rubrici kažnjava sa 0/10 za Sigurnost.

7. RUBRIKA — strogo zadrži ovaj format, s punom dijakritikom:
Ocijeni po ovim kategorijama (svaka 0-10):

ANAMNEZA (tezina 0.4): <5 konkretnih kriterija vezanih za OVAJ slucaj, svaki (2)>
KAZNA: <2 pravila: bez kljucnog pitanja X max N/10; ...>

KOMUNIKACIJA (tezina 0.3): jezik laika(2), empatija bez osudjivanja(2), provjerio razumijevanje(2), strukturisan razgovor(2), jasna poruka(2)

SIGURNOST (tezina 0.3): <4 konkretna kriterija za OVAJ slucaj, bodovi u zbiru 10>
KAZNA: <fatalna greska> = 0/10 za Sigurnost; <druga ozbiljna greska> = max 3/10 za Sigurnost

8. POČETNA PORUKA: Prva replika pacijenta — prirodna, kratka, s banalnim zahtjevom; NE otkriva \
ključni problem.

IZLAZ: Vrati ISKLJUČIVO validan JSON (bez markdown ograda, bez teksta prije/poslije) sa poljima:
{"naziv": "Scenarij — <kratak naslov bez spojlera>",
 "ime": "<bosansko ime>",
 "godine": <broj>,
 "tegoba": "<razlog dolaska + kratka emocionalna nota, npr. 'djeluje umorno'>",
 "terapija": "<terapija koju pacijent priznaje odmah — nepotpuna slika>",
 "skriveni_detalji": "<sve skrivene činjenice, odvojene tačka-zarezom>",
 "crvene_zastavice": "<zastavice + mehanizam + ispravna akcija, odvojene tačka-zarezom>",
 "ocekivano": "<očekivani koraci savjetovanja, odvojeni tačka-zarezom>",
 "pocetna_poruka": "<prva replika pacijenta>",
 "rubrika": "<rubrika u formatu iz tačke 7>",
 "obrazlozenje": "<za admina: sažetak case reporta (dijagnoza, ishod), šta je pedagoški cilj, gdje je lažni trag i zašto je slučaj težak — 4-6 rečenica>"}

""" + JEZIK_PRAVILO


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


# ─── UI Komponente ────────────────────────────────────────────────────────────
def kartica(sadrzaj_html, padding="20px 24px"):
    st.markdown(f"""
    <div style="background:white;border-radius:16px;padding:{padding};
         box-shadow:0 2px 8px rgba(0,0,0,0.07);margin-bottom:12px">
        {sadrzaj_html}
    </div>""", unsafe_allow_html=True)


def prikazi_ocjenu(r):
    ukupno = float(r.get("ukupna_ocjena", 0))
    boja = "#22c55e" if ukupno >= 7 else ("#f59e0b" if ukupno >= 5 else "#ef4444")
    bg = "#f0fdf4" if ukupno >= 7 else ("#fffbeb" if ukupno >= 5 else "#fef2f2")
    st.markdown(f"""
    <div style="background:{bg};border-radius:20px;padding:28px;text-align:center;
         margin:20px 0;border:2px solid {boja}22">
        <div style="font-size:48px;font-weight:800;color:{boja};line-height:1;margin-top:8px">
            {ukupno:.1f}
            <span style="font-size:22px;color:#94a3b8;font-weight:400">/10</span>
        </div>
        <div style="color:#64748b;font-size:15px;font-weight:500;margin-top:8px">Ukupna ocjena savjetovanja</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("Anamneza ×0.4", f"{r.get('anamneza', 0)}/10")
    col2.metric("Komunikacija ×0.3", f"{r.get('komunikacija', 0)}/10")
    col3.metric("Sigurnost ×0.3", f"{r.get('sigurnost', 0)}/10")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if r.get("pohvale"):
        st.markdown("#### Šta ste uradili dobro")
        for p in r["pohvale"]:
            if isinstance(p, dict):
                st.success(p.get("tekst", ""))
                if p.get("citat"):
                    st.caption(f"iz razgovora: „{p['citat']}“")
            else:
                st.success(p)

    # Pitanja koja jesu postavljena, a pacijent ih je izbjegao. Ovo se NE
    # kažnjava — prikazuje se da polaznik vidi gdje ga je pacijent odveo.
    if r.get("pitano_ali_neodgovoreno"):
        st.markdown("#### Pitali ste, ali niste dobili odgovor")
        st.caption("Ovo nije propust — pacijent je uskratio odgovor. Vrijedi vidjeti kako je to izveo.")
        for p in r["pitano_ali_neodgovoreno"]:
            if not isinstance(p, dict):
                continue
            st.info(
                f"**{p.get('pitanje','')}**\n\n"
                f"Vi: „{p.get('citat_farmaceuta','')}“\n\n"
                f"Pacijent: {p.get('reakcija_pacijenta','')}"
            )

    nije = r.get("nije_pitano") or r.get("propustena_pitanja")
    if nije:
        st.markdown("#### Niste pitali")
        for p in nije:
            if isinstance(p, dict):
                zasto = p.get("zasto_vazno", "")
                st.warning(f"**{p.get('pitanje','')}**" + (f"\n\n{zasto}" if zasto else ""))
            else:
                st.warning(p)

    if r.get("smjernice"):
        st.markdown("#### Smjernice za poboljšanje")
        for s in r["smjernice"]:
            st.info(s)


def _leaderboard_red(i, red, ja, medalje, vrijednost, label_vr):
    """Renderuje jedan red leaderboarda."""
    medalja = medalje[i] if i < 3 else f"<span style='font-weight:700;color:#94a3b8'>{i+1}.</span>"
    je_ja = red["email"] == ja
    bg = "linear-gradient(135deg,#dbeafe,#eff6ff)" if je_ja else "white"
    border = "border:2px solid #1E3A8A;" if je_ja else ""
    avg_a = red.get('avg_anamneza', 0)
    avg_k = red.get('avg_komunikacija', 0)
    avg_s = red.get('avg_sigurnost', 0)
    st.markdown(f"""
    <div style="background:{bg};{border}border-radius:14px;padding:14px 20px;
         margin-bottom:8px;box-shadow:0 1px 4px rgba(0,0,0,0.07)">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
            <div style="font-size:24px;min-width:36px;text-align:center">{medalja}</div>
            <div style="flex:1;min-width:0">
                <div style="font-weight:700;color:#1e293b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                    {red['ime']}{' (vi)' if je_ja else ''}
                </div>
                <div style="font-size:13px;color:#64748b">{red['slucajeva']} slučaj/eva</div>
            </div>
            <div style="text-align:right;flex-shrink:0">
                <div style="font-size:26px;font-weight:800;color:#1E3A8A">{vrijednost}</div>
                <div style="font-size:12px;color:#94a3b8">{label_vr}</div>
            </div>
        </div>
        <div style="display:flex;gap:8px;margin-left:48px;flex-wrap:wrap">
            <span style="background:#e0f2fe;color:#0369a1;padding:3px 10px;border-radius:10px;
                  font-size:11px;font-weight:600">Anamneza {avg_a}</span>
            <span style="background:#fef3c7;color:#92400e;padding:3px 10px;border-radius:10px;
                  font-size:11px;font-weight:600">Komunikacija {avg_k}</span>
            <span style="background:#fce7f3;color:#9d174d;padding:3px 10px;border-radius:10px;
                  font-size:11px;font-weight:600">Sigurnost {avg_s}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _leaderboard_prazno():
    st.markdown("""
    <div style="text-align:center;padding:40px;color:#94a3b8">
        <div style="font-size:18px;font-weight:600;color:#94a3b8">—</div>
        <div style="margin-top:8px">Još nema rezultata za ovaj period.</div>
    </div>""", unsafe_allow_html=True)


def _mini_leaderboard(podaci, sort_key, naslov, boja_bg, boja_tekst, ja, medalje):
    """Renderuje mini ljestvicu za jednu kategoriju."""
    sortirani = sorted(podaci, key=lambda x: x.get(sort_key, 0), reverse=True)
    st.markdown(f"""
    <div style="background:{boja_bg};border-radius:14px;padding:16px 20px;margin-bottom:8px">
        <div style="font-weight:700;font-size:15px;color:{boja_tekst};margin-bottom:12px">{naslov}</div>
    </div>""", unsafe_allow_html=True)
    for i, red in enumerate(sortirani[:5]):
        je_ja = red["email"] == ja
        pozadina = "#f0f7ff" if je_ja else "white"
        bord = f"border-left:3px solid {boja_tekst};" if i == 0 else ""
        val = red.get(sort_key, 0)
        st.markdown(f"""
        <div style="background:{pozadina};{bord}border-radius:10px;padding:10px 16px;margin-bottom:5px;
             box-shadow:0 1px 3px rgba(0,0,0,0.05);display:flex;align-items:center;gap:10px">
            <span style="font-weight:700;color:#94a3b8;min-width:24px">{i+1}.</span>
            <span style="flex:1;font-weight:600;color:#1e293b;font-size:14px;overflow:hidden;
                  text-overflow:ellipsis;white-space:nowrap">{red['ime']}{' (vi)' if je_ja else ''}</span>
            <span style="font-weight:800;color:{boja_tekst};font-size:18px">{val}</span>
            <span style="font-size:11px;color:#94a3b8">/10</span>
        </div>""", unsafe_allow_html=True)


def prikazi_leaderboard():
    st.markdown("## Ljestvica rezultata")

    medalje = ["1.", "2.", "3."]
    periodi = {"Sedmično": "sedmicno", "Mjesečno": "mjesecno", "Godišnje": "godisnje", "Ukupno": "ukupno"}
    odabrani_period = st.selectbox("Period", list(periodi.keys()), index=3, label_visibility="collapsed")
    period = periodi[odabrani_period]
    podaci = db_leaderboard(period)

    if not podaci:
        _leaderboard_prazno()
        return

    ja = st.session_state.get("korisnik_email", "")

    # ── Glavni tabovi: Prosječna ocjena | Ukupni bodovi | Po kategorijama ──
    tab_prosjek, tab_ukupno, tab_kategorije = st.tabs(
        ["Prosječna ocjena", "Ukupni bodovi", "Po kategorijama"]
    )

    # ── TAB 1: Prosječna ocjena (najvažniji) ──
    with tab_prosjek:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#0D8A9E,#0A6B7C);border-radius:14px;
             padding:16px 20px;margin-bottom:16px;color:white">
            <div style="font-size:13px;opacity:0.8">Rangiranje po</div>
            <div style="font-size:18px;font-weight:700">Prosječnoj ocjeni po scenariju</div>
        </div>""", unsafe_allow_html=True)

        sortirani_prosjek = sorted(podaci, key=lambda x: x["prosjek"], reverse=True)
        for i, red in enumerate(sortirani_prosjek[:20]):
            _leaderboard_red(i, red, ja, medalje, f"{red['prosjek']:.1f}", "prosjek")

    # ── TAB 2: Ukupni bodovi ──
    with tab_ukupno:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#2C6FBE,#1E3A8A);border-radius:14px;
             padding:16px 20px;margin-bottom:16px;color:white">
            <div style="font-size:13px;opacity:0.8">Rangiranje po</div>
            <div style="font-size:18px;font-weight:700">Ukupnom zbiru bodova</div>
        </div>""", unsafe_allow_html=True)

        for i, red in enumerate(podaci[:20]):
            _leaderboard_red(i, red, ja, medalje, f"{red['ukupno']:.1f}", "bodova")

    # ── TAB 3: Po kategorijama ──
    with tab_kategorije:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#475569,#334155);border-radius:14px;
             padding:16px 20px;margin-bottom:16px;color:white">
            <div style="font-size:13px;opacity:0.8">Top 5 po</div>
            <div style="font-size:18px;font-weight:700">Anamnezi, Komunikaciji i Sigurnosti</div>
        </div>""", unsafe_allow_html=True)

        _mini_leaderboard(podaci, "avg_anamneza", "Najbolja anamneza",
                          "#e0f2fe", "#0369a1", ja, medalje)
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        _mini_leaderboard(podaci, "avg_komunikacija", "Najbolja komunikacija",
                          "#fef3c7", "#92400e", ja, medalje)
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        _mini_leaderboard(podaci, "avg_sigurnost", "Najbolja sigurnost",
                          "#fce7f3", "#9d174d", ja, medalje)


def prikazi_nadimak_postavku():
    """Nadimak je jedino što drugi vide na ljestvici — zato se mijenja ovdje."""
    email = st.session_state.get("korisnik_email", "")
    korisnik = st.session_state.get("korisnik", {}) or {}
    trenutni = (korisnik.get("nadimak") or "").strip()

    with st.expander("Nadimak na ljestvici" + ("" if trenutni else " — još nije postavljen"),
                     expanded=not trenutni):
        st.caption(
            "Na ljestvici se prikazuje isključivo nadimak. Ime, prezime i apoteka "
            "se ne prikazuju nikome. Ako želite da vas kolege prepoznaju, slobodno "
            "upišite svoje ime kao nadimak — to je vaš izbor."
        )
        if not trenutni:
            st.info(f"Trenutno ste na ljestvici prikazani kao **{nadimak_za(korisnik, email)}**.")

        with st.form("nadimak_form"):
            novi = st.text_input("Nadimak", value=trenutni, max_chars=24,
                                 placeholder="3 do 24 znaka")
            if st.form_submit_button("Sačuvaj nadimak", type="primary"):
                ok, poruka = db_postavi_nadimak(email, novi)
                if ok:
                    korisnik["nadimak"] = novi.strip()
                    st.session_state["korisnik"] = korisnik
                    st.success("Nadimak je sačuvan.")
                    st.rerun()
                else:
                    st.error(poruka)


def prikazi_moje_rezultate():
    st.markdown("## Moji rezultati")
    email = st.session_state.get("korisnik_email", "")
    prikazi_nadimak_postavku()
    rezultati = db_moji_rezultati(email)

    if not rezultati:
        st.markdown("""
        <div style="text-align:center;padding:48px;color:#94a3b8">
            <div style="margin-top:12px;font-size:16px">Još nemate završenih scenarija.</div>
        </div>""", unsafe_allow_html=True)
        return

    ukupno = sum(float(r["score"]) for r in rezultati)
    prosjek = ukupno / len(rezultati)

    col1, col2, col3 = st.columns(3)
    col1.metric("Ukupno bodova", f"{ukupno:.1f}")
    col2.metric("Završenih scenarija", len(rezultati))
    col3.metric("Prosječna ocjena", f"{prosjek:.1f}")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    for r in rezultati:
        naziv = next(
            (sc["naziv"] for k, sc in SCENARIJI.items() if k == r["scenario_id"]),
            r["scenario_id"]
        )
        ocjena = float(r["score"])
        boja = "#22c55e" if ocjena >= 7 else ("#f59e0b" if ocjena >= 5 else "#ef4444")
        bg_score = "#f0fdf4" if ocjena >= 7 else ("#fffbeb" if ocjena >= 5 else "#fef2f2")
        datum = r.get("completed_at", "")[:10] if r.get("completed_at") else ""
        st.markdown(f"""
        <div style="background:white;border-radius:14px;padding:16px 20px;margin-bottom:10px;
             box-shadow:0 1px 4px rgba(0,0,0,0.07);display:flex;align-items:center;gap:16px">
            <div style="flex:1">
                <div style="font-weight:600;color:#1e293b">{naziv}</div>
                <div style="font-size:13px;color:#94a3b8;margin-top:2px">{datum}</div>
                <div style="font-size:13px;color:#64748b;margin-top:4px">
                    Anamneza: {r.get('anamneza','?')}/10 ·
                    Komunikacija: {r.get('komunikacija','?')}/10 ·
                    Sigurnost: {r.get('sigurnost','?')}/10
                </div>
            </div>
            <div style="background:{bg_score};border-radius:12px;padding:10px 16px;text-align:center;flex-shrink:0">
                <div style="font-size:28px;font-weight:800;color:{boja}">{ocjena:.1f}</div>
                <div style="font-size:11px;color:#94a3b8">/10</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Žalba na ocjenu ──
        status_zalbe = r.get("appeal_status")
        if status_zalbe == "otvorena":
            st.info("Vaša žalba je poslana i čeka pregled administratora.")
        elif status_zalbe == "rijesena":
            st.success(
                "**Žalba riješena — ocjena je ispravljena.**"
                + (f" Odgovor: {r.get('appeal_response','')}" if r.get("appeal_response") else "")
            )
        elif status_zalbe == "odbijena":
            st.warning(
                "**Žalba pregledana — ocjena je zadržana.**"
                + (f" Odgovor: {r.get('appeal_response','')}" if r.get("appeal_response") else "")
            )
        elif r.get("id") is not None:
            with st.expander("Prijavi problem s ocjenom"):
                with st.form(f"zalba_forma_{r['id']}"):
                    tekst = st.text_area(
                        "Opišite šta smatrate netačnim u ocjeni",
                        placeholder="Npr. pitao/la sam za trudnoću, a evaluacija kaže da nisam...",
                    )
                    if st.form_submit_button("Pošalji žalbu", type="primary"):
                        if len(tekst.strip()) < 10:
                            st.error("Molimo opišite problem (najmanje 10 znakova).")
                        else:
                            ok, msg = db_posalji_zalbu(r["id"], tekst)
                            if ok:
                                st.success("Žalba poslana! Administrator će je pregledati.")
                                time.sleep(1.2)
                                st.rerun()
                            else:
                                st.error(msg)


def prikazi_gdpr_brisanje():
    """GDPR: korisnik može trajno obrisati svoj nalog i sve podatke."""
    email = st.session_state.get("korisnik_email", "")
    if not email or je_admin():
        return

    st.divider()
    with st.expander("Brisanje naloga i svih podataka (GDPR)"):
        st.warning(
            "**Trajno i nepovratno** briše vaš nalog, sve rezultate, transkripte "
            "razgovora i evidenciju korištenja. Nakon brisanja nema povratka podataka."
        )
        with st.form("gdpr_forma"):
            lozinka_g = st.text_input(
                "Vaša lozinka", type="password", autocomplete="off"
            )
            potvrda_g = st.text_input(
                "Za potvrdu upišite: OBRIŠI", placeholder="OBRIŠI"
            )
            submit_g = st.form_submit_button(
                "Trajno obriši moj nalog i sve podatke", use_container_width=True
            )
        if submit_g:
            if potvrda_g.strip() != "OBRIŠI":
                st.error("Za potvrdu morate tačno upisati: OBRIŠI")
            else:
                k, _ = db_login(email, lozinka_g)
                if not k:
                    st.error("Pogrešna lozinka.")
                elif db_obrisi_sve_podatke(email):
                    for kljuc_s in list(st.session_state.keys()):
                        del st.session_state[kljuc_s]
                    st.session_state["gdpr_flash"] = (
                        "Vaš nalog i svi podaci su trajno obrisani. Hvala što ste koristili platformu."
                    )
                    st.rerun()


def prikazi_admin():
    # Druga brava: navigacija već skriva Admin bez uloge, ali stranica se ne
    # smije osloniti na to da je jedini put do nje meni.
    if not je_admin():
        st.error("Nemate pristup administraciji.")
        st.stop()

    st.markdown("## Admin panel")

    # ── Obradi akciju iz session_state (ako postoji) ──
    akcija = st.session_state.pop("admin_akcija", None)
    if akcija:
        email_k = akcija.get("email", "")
        ime_k = akcija.get("ime", "")
        if akcija["tip"] == "bulk_odobri":
            uspjeh, greske = 0, []
            for kor in akcija["korisnici"]:
                if db_odobri_korisnika(kor["email"]):
                    uspjeh += 1
                    ok, msg = posalji_email_odobrenje(kor["email"], kor["ime"])
                    if not ok:
                        greske.append(f"{kor['email']}: odobren, ali email nije poslan ({msg})")
                else:
                    greske.append(f"{kor['email']}: greška pri odobravanju")
                time.sleep(0.6)  # Resend rate limit: 2 zahtjeva/s
            st.success(f"Masovno odobreno: **{uspjeh}** od {len(akcija['korisnici'])} korisnika.")
            for g in greske:
                st.warning(g)
        elif akcija["tip"] == "odobri":
            if db_odobri_korisnika(email_k):
                st.success(f"Odobren: **{ime_k}** ({email_k})")
                ok, msg = posalji_email_odobrenje(email_k, ime_k)
                if ok:
                    st.success("Email notifikacija poslana!")
                else:
                    st.warning(f"Email nije poslan: {msg}")
            else:
                st.error(f"Greška pri odobravanju korisnika {email_k}.")
        elif akcija["tip"] == "odbij":
            if db_odbij_korisnika(email_k):
                st.info(f"Korisnik **{ime_k}** odbijen i obrisan.")
            else:
                st.error(f"Greška pri brisanju korisnika {email_k}.")
        elif akcija["tip"] == "brisi":
            if db_obrisi_sve_podatke(email_k):
                st.info(f"Korisnik **{ime_k}** ({email_k}) je obrisan zajedno sa svim podacima (GDPR).")
            else:
                st.error(f"Greška pri brisanju korisnika {email_k}.")
        elif akcija["tip"] == "suspenduj":
            if db_postavi_suspenziju(email_k, True):
                st.warning(f"Korisnik **{ime_k}** je suspendovan — više se ne može prijaviti.")
        elif akcija["tip"] == "aktiviraj":
            if db_postavi_suspenziju(email_k, False):
                st.success(f"Korisnik **{ime_k}** je ponovo aktivan.")
        elif akcija["tip"] == "reset":
            privremena = db_resetuj_lozinku(email_k)
            if privremena:
                st.success(f"Privremena lozinka za **{ime_k}** ({email_k}):")
                st.code(privremena)
                st.caption("Pošaljite je korisniku — prikazuje se samo sada i ne može se ponovo vidjeti.")

    flash = st.session_state.pop("admin_flash", None)
    if flash:
        st.success(flash)

    zalbe = db_otvorene_zalbe()
    (tab_stat, tab_zahtjevi, tab_korisnici, tab_zalbe,
     tab_transkripti, tab_scenariji, tab_ai_gen, tab_objave, tab_email) = st.tabs([
        "Statistika", "Zahtjevi", "Korisnici",
        f"Žalbe ({len(zalbe)})" if zalbe else "Žalbe",
        "Transkripti", "Scenariji", "AI Generator", "Objave", "Email",
    ])

    # ══ TAB 1: Zahtjevi na čekanju ══
    with tab_zahtjevi:
        neodobreni = db_neodobreni_korisnici()

        if not neodobreni:
            st.markdown("""
            <div style="text-align:center;padding:40px;color:#94a3b8">
                <div style="font-size:16px;font-weight:600;color:#94a3b8">—</div>
                <div style="margin-top:8px">Nema zahtjeva na čekanju.</div>
            </div>""", unsafe_allow_html=True)
        else:
            st.info(f"**{len(neodobreni)}** korisnik/a čeka odobrenje.")
            odabrani_bulk = []
            for i, k in enumerate(neodobreni):
                st.markdown(f"""
                <div style="background:white;border-radius:14px;padding:18px 22px;margin-bottom:4px;
                     box-shadow:0 1px 4px rgba(0,0,0,0.07);border-left:4px solid #f59e0b">
                    <div style="font-weight:700;color:#1e293b">{k.get('full_name','—')}</div>
                    <div style="font-size:13px;color:#64748b;margin-top:3px">
                        {k['email']} · {k.get('institution','—')}
                    </div>
                    <div style="font-size:12px;color:#94a3b8;margin-top:2px">
                        Registrovan: {str(k.get('created_at',''))[:16]}
                    </div>
                </div>""", unsafe_allow_html=True)

                col_chk, col_a, col_b = st.columns([1, 1, 1])
                with col_chk:
                    if st.checkbox("Odaberi", key=f"chk_zahtjev_{k['email']}"):
                        odabrani_bulk.append({
                            "email": k["email"],
                            "ime": k.get("full_name", k["email"]),
                        })
                with col_a:
                    if st.button("Odobri", key=f"odobri_{i}", type="primary", use_container_width=True):
                        st.session_state["admin_akcija"] = {
                            "tip": "odobri", "email": k["email"],
                            "ime": k.get("full_name", k["email"]),
                        }
                        st.rerun()
                with col_b:
                    if st.button("Odbij", key=f"odbij_{i}", type="secondary", use_container_width=True):
                        st.session_state["admin_akcija"] = {
                            "tip": "odbij", "email": k["email"],
                            "ime": k.get("full_name", k["email"]),
                        }
                        st.rerun()

            # ── Masovno odobravanje ──
            st.divider()
            cb1, cb2 = st.columns(2)
            with cb1:
                if st.button(
                    f"Odobri odabrane ({len(odabrani_bulk)})",
                    type="primary", use_container_width=True,
                    disabled=not odabrani_bulk,
                ):
                    st.session_state["admin_akcija"] = {
                        "tip": "bulk_odobri", "korisnici": odabrani_bulk,
                    }
                    st.rerun()
            with cb2:
                if st.button(
                    f"Odobri sve ({len(neodobreni)})",
                    use_container_width=True,
                ):
                    st.session_state["admin_akcija"] = {
                        "tip": "bulk_odobri",
                        "korisnici": [
                            {"email": k["email"], "ime": k.get("full_name", k["email"])}
                            for k in neodobreni
                        ],
                    }
                    st.rerun()
            st.caption("Svaki odobreni korisnik automatski dobija email notifikaciju.")

    # ══ TAB 2: Korisnici — pretraga, reset lozinke, suspenzija, brisanje ══
    with tab_korisnici:
        odobreni = db_svi_korisnici()
        if not odobreni:
            st.caption("Nema odobrenih korisnika.")
        else:
            pretraga = st.text_input(
                "Pretraga korisnika", placeholder="Ime, email ili institucija...",
                label_visibility="collapsed",
            )
            if pretraga:
                p = pretraga.lower().strip()
                odobreni = [
                    k for k in odobreni
                    if p in f"{k.get('full_name','')} {k['email']} {k.get('institution','')}".lower()
                ]
            st.caption(f"Prikazano: **{len(odobreni)}** korisnik/a")

            for k in odobreni:
                susp = k.get("suspended", False)
                badge_bg, badge_boja, badge_txt = (
                    ("#fef2f2", "#dc2626", "Suspendovan") if susp
                    else ("#dcfce7", "#16a34a", "Aktivan")
                )
                st.markdown(f"""
                <div style="background:white;border-radius:12px;padding:14px 20px;margin-bottom:4px;
                     box-shadow:0 1px 3px rgba(0,0,0,0.05);display:flex;align-items:center;gap:12px">
                    <div style="flex:1">
                        <div style="font-weight:600;color:#1e293b">{k.get('full_name','—')}</div>
                        <div style="font-size:13px;color:#64748b">{k.get('institution','')} · {k['email']}</div>
                    </div>
                    <span style="background:{badge_bg};color:{badge_boja};padding:4px 12px;border-radius:16px;
                          font-size:12px;font-weight:600">{badge_txt}</span>
                </div>""", unsafe_allow_html=True)

                if not je_admin(k):
                    c1, c2, c3 = st.columns(3)
                    ime_k = k.get("full_name", k["email"])
                    with c1:
                        if st.button("Resetuj lozinku", key=f"reset_{k['email']}", use_container_width=True):
                            st.session_state["admin_akcija"] = {"tip": "reset", "email": k["email"], "ime": ime_k}
                            st.rerun()
                    with c2:
                        akcija_txt = "Aktiviraj" if susp else "Suspenduj"
                        akcija_tip = "aktiviraj" if susp else "suspenduj"
                        if st.button(akcija_txt, key=f"susp_{k['email']}", use_container_width=True):
                            st.session_state["admin_akcija"] = {"tip": akcija_tip, "email": k["email"], "ime": ime_k}
                            st.rerun()
                    with c3:
                        if st.button("Obriši", key=f"brisi_{k['email']}", use_container_width=True):
                            st.session_state["admin_akcija"] = {"tip": "brisi", "email": k["email"], "ime": ime_k}
                            st.rerun()

                    uloge = ["korisnik", "mentor", "admin"]
                    trenutna = k.get("role") or "korisnik"
                    u1, u2 = st.columns([3, 1])
                    nova = u1.selectbox(
                        "Uloga", uloge, index=uloge.index(trenutna) if trenutna in uloge else 0,
                        key=f"uloga_{k['email']}", label_visibility="collapsed")
                    if nova != trenutna:
                        if u2.button("Dodijeli", key=f"uloga_btn_{k['email']}", use_container_width=True):
                            ok, poruka = db_postavi_ulogu(k["email"], nova)
                            if ok:
                                st.success(f"{ime_k} je sada {nova}.")
                                st.rerun()
                            else:
                                st.error(poruka)

    # ══ TAB 3: Žalbe na ocjene ══
    with tab_zalbe:
        if not zalbe:
            st.markdown("""
            <div style="text-align:center;padding:40px;color:#94a3b8">
                <div style="margin-top:8px">Nema otvorenih žalbi.</div>
            </div>""", unsafe_allow_html=True)
        else:
            imena = {u["email"]: u.get("full_name", u["email"]) for u in db_svi_korisnici()}
            st.info(f"**{len(zalbe)}** otvorena/e žalba/e na ocjenu.")
            for z in zalbe:
                naziv_sc = SCENARIJI.get(z["scenario_id"], {}).get("naziv", z["scenario_id"])
                ime_z = imena.get(z["user_email"], z["user_email"])
                st.markdown(f"""
                <div style="background:white;border-radius:14px;padding:18px 22px;margin-bottom:4px;
                     box-shadow:0 1px 4px rgba(0,0,0,0.07);border-left:4px solid #dc2626">
                    <div style="font-weight:700;color:#1e293b">{ime_z} · {z['user_email']}</div>
                    <div style="font-size:13px;color:#64748b;margin-top:3px">{naziv_sc}</div>
                    <div style="font-size:13px;color:#64748b;margin-top:4px">
                        Trenutno: <b>{float(z.get('score',0)):.1f}/10</b> ·
                        A {z.get('anamneza','?')}/10 · K {z.get('komunikacija','?')}/10 · S {z.get('sigurnost','?')}/10
                    </div>
                </div>""", unsafe_allow_html=True)

                if z.get("appeal_text"):
                    st.info(f"**Žalba korisnika:** {z['appeal_text']}")
                if z.get("transcript"):
                    with st.expander("Transkript razgovora"):
                        st.text(z["transcript"])
                else:
                    st.caption("Transkript nije sačuvan za ovaj pokušaj.")

                with st.form(f"zalba_{z['id']}"):
                    c1, c2, c3 = st.columns(3)
                    a = c1.number_input("Anamneza", 0, 10, int(z.get("anamneza") or 0))
                    kk = c2.number_input("Komunikacija", 0, 10, int(z.get("komunikacija") or 0))
                    s = c3.number_input("Sigurnost", 0, 10, int(z.get("sigurnost") or 0))
                    st.caption(f"Nova ukupna ocjena: **{a*0.4 + kk*0.3 + s*0.3:.1f}/10** (0.4·A + 0.3·K + 0.3·S)")
                    odgovor = st.text_area("Odgovor korisniku (obavezno)", placeholder="Obrazloženje odluke...")
                    cb1, cb2 = st.columns(2)
                    ispravi = cb1.form_submit_button("Ispravi ocjenu i riješi", type="primary", use_container_width=True)
                    odbij = cb2.form_submit_button("Odbij žalbu (zadrži ocjenu)", use_container_width=True)

                if ispravi or odbij:
                    if not odgovor.strip():
                        st.error("Upišite odgovor korisniku prije zatvaranja žalbe.")
                    else:
                        if ispravi:
                            ok = db_rijesi_zalbu(z["id"], "rijesena", odgovor,
                                                 {"anamneza": a, "komunikacija": kk, "sigurnost": s})
                            poruka = f"Žalba korisnika {ime_z} riješena — ocjena ispravljena."
                        else:
                            ok = db_rijesi_zalbu(z["id"], "odbijena", odgovor)
                            poruka = f"Žalba korisnika {ime_z} odbijena — ocjena zadržana."
                        if ok:
                            st.session_state["admin_flash"] = poruka
                            st.rerun()
                st.divider()

    # ══ TAB 4: Transkripti razgovora ══
    with tab_transkripti:
        korisnici = db_svi_korisnici()
        if not korisnici:
            st.caption("Nema korisnika.")
        else:
            opcije = {f"{k.get('full_name','—')} ({k['email']})": k["email"] for k in korisnici}
            izbor = st.selectbox("Odaberite korisnika", list(opcije.keys()))
            pokusaji = db_pokusaji_korisnika(opcije[izbor])
            if not pokusaji:
                st.caption("Ovaj korisnik još nema završenih scenarija.")
            for pk in pokusaji:
                naziv_sc = SCENARIJI.get(pk["scenario_id"], {}).get("naziv", pk["scenario_id"])
                datum = str(pk.get("completed_at", ""))[:16].replace("T", " ")
                with st.expander(f"{naziv_sc} · {datum} · {float(pk.get('score',0)):.1f}/10"):
                    st.markdown(
                        f"**Anamneza:** {pk.get('anamneza','?')}/10 · "
                        f"**Komunikacija:** {pk.get('komunikacija','?')}/10 · "
                        f"**Sigurnost:** {pk.get('sigurnost','?')}/10"
                    )
                    if pk.get("appeal_status"):
                        st.caption(f"Žalba: {pk['appeal_status']}"
                                   + (f" · Odgovor: {pk.get('appeal_response','')}" if pk.get("appeal_response") else ""))
                    if pk.get("transcript"):
                        st.text(pk["transcript"])
                    else:
                        st.caption("Transkript nije sačuvan (pokušaj prije uvođenja ove funkcije).")

    # ══ TAB: Statistika ══
    with tab_stat:
        podaci = db_statistika()
        if not podaci:
            st.caption("Statistika nije dostupna.")
        else:
            pokusaji = podaci["pokusaji"]
            upotreba = podaci["upotreba"]
            sada = datetime.now(timezone.utc)
            danas_str = sada.date().isoformat()
            od7 = (sada - timedelta(days=7)).isoformat()
            od30 = (sada - timedelta(days=30)).isoformat()

            aktivni_danas = {u["user_email"] for u in upotreba
                             if str(u.get("created_at", "")) >= danas_str} - {"", None}
            aktivni_7d = {u["user_email"] for u in upotreba
                          if str(u.get("created_at", "")) >= od7} - {"", None}

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Korisnika", sum(1 for k in podaci["korisnici"] if k.get("approved")))
            c2.metric("Aktivni danas", len(aktivni_danas))
            c3.metric("Aktivni (7 d)", len(aktivni_7d))
            c4.metric("Pokušaja ukupno", len(pokusaji))

            # ── Po scenariju ──
            st.markdown("#### Po scenariju")
            po_sc = defaultdict(lambda: {"n": 0, "suma": 0.0})
            for p in pokusaji:
                po_sc[p["scenario_id"]]["n"] += 1
                po_sc[p["scenario_id"]]["suma"] += float(p.get("score") or 0)
            startovi = defaultdict(int)
            zavrseni30 = defaultdict(int)
            for u in upotreba:
                if u.get("event") == "start" and u.get("scenario_id"):
                    startovi[u["scenario_id"]] += 1
            for p in pokusaji:
                if str(p.get("completed_at", "")) >= od30:
                    zavrseni30[p["scenario_id"]] += 1

            if not po_sc:
                st.caption("Još nema odigranih scenarija.")
            else:
                redovi = ""
                for sid, d in sorted(po_sc.items()):
                    naziv_sc = SCENARIJI.get(sid, {}).get("naziv", sid)
                    prosjek = d["suma"] / d["n"] if d["n"] else 0
                    n_start = startovi.get(sid, 0)
                    zavrsenost = (
                        f"{min(100, round(100 * zavrseni30[sid] / n_start))}%"
                        if n_start else "—"
                    )
                    redovi += f"| {naziv_sc} | {d['n']} | {prosjek:.1f} | {zavrsenost} |\n"
                st.markdown(
                    "| Scenarij | Pokušaja | Prosjek | Završenost (30 d) |\n"
                    "|---|---|---|---|\n" + redovi
                )
                st.caption("Završenost = završeni / započeti u zadnjih 30 dana. Niska završenost = korisnici odustaju usred razgovora.")

            # ── API potrošnja ──
            st.markdown("#### API potrošnja (procjena)")

            def _trosak(redovi_u):
                t_in = sum(u.get("tokens_in") or 0 for u in redovi_u)
                t_out = sum(u.get("tokens_out") or 0 for u in redovi_u)
                return t_in + t_out, t_in * CIJENA_ULAZ_USD + t_out * CIJENA_IZLAZ_USD

            t_d, c_d = _trosak([u for u in upotreba if str(u.get("created_at", "")) >= danas_str])
            t_7, c_7 = _trosak([u for u in upotreba if str(u.get("created_at", "")) >= od7])
            t_30, c_30 = _trosak(upotreba)

            m1, m2, m3 = st.columns(3)
            m1.metric("Danas", f"${c_d:.2f}", f"{t_d:,} tokena", delta_color="off")
            m2.metric("7 dana", f"${c_7:.2f}", f"{t_7:,} tokena", delta_color="off")
            m3.metric("30 dana", f"${c_30:.2f}", f"{t_30:,} tokena", delta_color="off")

            po_korisniku = defaultdict(int)
            for u in upotreba:
                po_korisniku[u.get("user_email") or "?"] += (u.get("tokens_in") or 0) + (u.get("tokens_out") or 0)
            top = sorted(po_korisniku.items(), key=lambda x: -x[1])[:5]
            if top:
                st.markdown("**Top 5 korisnika po tokenima (30 d):**")
                for em, t in top:
                    st.caption(f"{em} — {t:,} tokena")

            # ── Export podataka (CSV) ──
            st.markdown("#### Export podataka (CSV)")
            danas_ime = sada.date().isoformat()
            svi_kor = db_svi_korisnici()
            imena_exp = {u["email"]: u for u in svi_kor}

            ex1, ex2 = st.columns(2)
            with ex1:
                pokusaji_exp = db_svi_pokusaji_export()
                redovi_r = [
                    [
                        imena_exp.get(p["user_email"], {}).get("full_name", ""),
                        p["user_email"],
                        imena_exp.get(p["user_email"], {}).get("institution", ""),
                        SCENARIJI.get(p["scenario_id"], {}).get("naziv", p["scenario_id"]),
                        p.get("score", ""),
                        p.get("anamneza", ""),
                        p.get("komunikacija", ""),
                        p.get("sigurnost", ""),
                        str(p.get("completed_at", ""))[:16].replace("T", " "),
                        p.get("appeal_status") or "",
                    ]
                    for p in pokusaji_exp
                ]
                st.download_button(
                    f"Rezultati ({len(redovi_r)})",
                    data=napravi_csv(
                        ["Ime", "Email", "Institucija", "Scenarij", "Ocjena",
                         "Anamneza", "Komunikacija", "Sigurnost", "Datum", "Žalba"],
                        redovi_r,
                    ),
                    file_name=f"rezultati_{danas_ime}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            with ex2:
                redovi_k = [
                    [
                        u.get("full_name", ""),
                        u["email"],
                        u.get("institution", ""),
                        "suspendovan" if u.get("suspended") else "aktivan",
                        str(u.get("created_at", ""))[:16].replace("T", " "),
                    ]
                    for u in svi_kor
                ]
                st.download_button(
                    f"Korisnici ({len(redovi_k)})",
                    data=napravi_csv(
                        ["Ime", "Email", "Institucija", "Status", "Registrovan"],
                        redovi_k,
                    ),
                    file_name=f"korisnici_{danas_ime}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            st.caption("CSV fajlovi su spremni za Excel (UTF-8, ';' separator).")

    # ══ TAB: Scenariji (CMS) ══
    with tab_scenariji:
        st.caption(
            "Scenariji iz baze se uređuju bez novog deploya. "
            "Ugrađene (u kodu) prvo kopirajte u bazu, pa uredite."
        )
        for sid, s in SCENARIJI.items():
            iz_baze = s.get("_iz_baze", False)
            aktivan = s.get("aktivan", True)
            if iz_baze:
                badge_bg, badge_boja, badge_txt = (
                    ("#dcfce7", "#16a34a", "Baza · aktivan") if aktivan
                    else ("#fef3c7", "#92400e", "Baza · draft")
                )
            else:
                badge_bg, badge_boja, badge_txt = "#dbeafe", "#2C6FBE", "Ugrađen u kod"
            st.markdown(f"""
            <div style="background:white;border-radius:12px;padding:14px 20px;margin-bottom:4px;
                 box-shadow:0 1px 3px rgba(0,0,0,0.05);display:flex;align-items:center;gap:12px">
                <div style="flex:1">
                    <div style="font-weight:600;color:#1e293b">{s.get('naziv', sid)}</div>
                    <div style="font-size:13px;color:#64748b">{sid} · {s.get('ime','')}, {s.get('godine','')} god.</div>
                </div>
                <span style="background:{badge_bg};color:{badge_boja};padding:4px 12px;border-radius:16px;
                      font-size:12px;font-weight:600">{badge_txt}</span>
            </div>""", unsafe_allow_html=True)

            if iz_baze:
                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.button("Uredi", key=f"sc_uredi_{sid}", use_container_width=True):
                        st.session_state["uredi_scenarij"] = sid
                        st.rerun()
                with c2:
                    lbl = "Deaktiviraj" if aktivan else "Aktiviraj"
                    if st.button(lbl, key=f"sc_akt_{sid}", use_container_width=True):
                        if db_scenarij_aktivan(sid, not aktivan):
                            st.session_state["admin_flash"] = f"Scenarij '{s.get('naziv', sid)}' — {'deaktiviran' if aktivan else 'aktiviran'}."
                            st.rerun()
                with c3:
                    if st.button("Obriši", key=f"sc_del_{sid}", use_container_width=True):
                        if db_scenarij_obrisi(sid):
                            st.session_state["admin_flash"] = f"Scenarij '{s.get('naziv', sid)}' obrisan iz baze."
                            st.rerun()
            else:
                if st.button("Kopiraj u bazu za uređivanje", key=f"sc_kopiraj_{sid}"):
                    ok = db_scenarij_spremi(sid, {
                        "naziv": s.get("naziv", ""), "ime": s.get("ime", ""),
                        "godine": int(s.get("godine") or 0), "tegoba": s.get("tegoba", ""),
                        "terapija": s.get("terapija", ""), "skriveni_detalji": s.get("skriveni_detalji", ""),
                        "crvene_zastavice": s.get("crvene_zastavice", ""), "ocekivano": s.get("ocekivano", ""),
                        "pocetna_poruka": s.get("pocetna_poruka", ""), "rubrika": s.get("rubrika", ""),
                        "active": True,
                    })
                    if ok:
                        st.session_state["admin_flash"] = f"Scenarij '{s.get('naziv', sid)}' kopiran u bazu — sada se može uređivati."
                        st.rerun()

        st.divider()

        # ── Forma: novi ili uredi postojeći ──
        uredi_sid = st.session_state.get("uredi_scenarij")
        izvor = SCENARIJI.get(uredi_sid, {}) if uredi_sid else {}
        st.markdown("#### " + (f"Uredi scenarij: {izvor.get('naziv', uredi_sid)}" if uredi_sid else "Novi scenarij"))

        with st.form(f"scenarij_forma_{uredi_sid or 'novi'}"):
            sid_in = st.text_input("ID (jedinstven, npr. scenarij_3)", value=uredi_sid or "")
            naziv_in = st.text_input("Naziv", value=izvor.get("naziv", ""),
                                     placeholder="Scenarij 3 — Glavobolja i ...")
            c1, c2 = st.columns(2)
            ime_in = c1.text_input("Ime pacijenta", value=izvor.get("ime", ""))
            godine_in = c2.number_input("Godine", 0, 120, int(izvor.get("godine") or 30))
            tegoba_in = st.text_area("Tegoba / razlog posjete", value=izvor.get("tegoba", ""), height=70)
            terapija_in = st.text_area("Postojeća terapija", value=izvor.get("terapija", ""), height=70)
            skriveni_in = st.text_area("Skriveni detalji (otkriva samo na direktno pitanje)",
                                       value=izvor.get("skriveni_detalji", ""), height=140)
            zastavice_in = st.text_area("Crvene zastavice", value=izvor.get("crvene_zastavice", ""), height=100)
            ocekivano_in = st.text_area("Očekivano savjetovanje", value=izvor.get("ocekivano", ""), height=100)
            pocetna_in = st.text_input("Početna poruka pacijenta", value=izvor.get("pocetna_poruka", ""))
            rubrika_in = st.text_area("Rubrika za ocjenjivanje", value=izvor.get("rubrika", ""), height=180)
            aktivan_in = st.checkbox("Aktivan (odmah vidljiv korisnicima)", value=bool(izvor.get("aktivan", False)))
            cf1, cf2 = st.columns(2)
            spremi = cf1.form_submit_button("Spremi scenarij", type="primary", use_container_width=True)
            otkazi = cf2.form_submit_button("Otkaži uređivanje", use_container_width=True)

        if otkazi:
            st.session_state.pop("uredi_scenarij", None)
            st.rerun()
        if spremi:
            if not sid_in.strip() or not naziv_in.strip() or not pocetna_in.strip() or not skriveni_in.strip():
                st.error("Obavezno: ID, naziv, početna poruka i skriveni detalji.")
            else:
                ok = db_scenarij_spremi(sid_in, {
                    "naziv": naziv_in.strip(), "ime": ime_in.strip(), "godine": int(godine_in),
                    "tegoba": tegoba_in.strip(), "terapija": terapija_in.strip(),
                    "skriveni_detalji": skriveni_in.strip(), "crvene_zastavice": zastavice_in.strip(),
                    "ocekivano": ocekivano_in.strip(), "pocetna_poruka": pocetna_in.strip(),
                    "rubrika": rubrika_in.strip(), "active": bool(aktivan_in),
                })
                if ok:
                    st.session_state.pop("uredi_scenarij", None)
                    st.session_state["admin_flash"] = (
                        f"Scenarij '{naziv_in.strip()}' spremljen"
                        + (" i aktivan." if aktivan_in else " kao draft (nije vidljiv korisnicima).")
                    )
                    st.rerun()

    # ══ TAB: AI Generator scenarija iz PDF case reporta ══
    with tab_ai_gen:
        st.caption(
            "Uploadujte case report (PDF, npr. sa PubMeda) — Claude će kreirati "
            "kompletan scenarij: pacijenta, skrivene detalje, crvene zastavice i "
            "rubriku za ocjenjivanje. Prije spremanja sve možete pregledati i urediti."
        )
        pdf_up = st.file_uploader("Case report (PDF)", type=["pdf"], key="ai_gen_pdf")
        c_t, c_s = st.columns([1, 2])
        tezina_in = c_t.radio("Težina", ["Teško", "Ekspertno"], key="ai_gen_tezina")
        smjernice_in = c_s.text_area(
            "Dodatne smjernice (opcionalno)", height=95, key="ai_gen_smjernice",
            placeholder="Npr. fokus na interakcije; pacijent neka bude stariji muškarac; "
                        "naglasak na OTC samoliječenje...",
        )
        if st.button("Generiši scenarij", type="primary", disabled=pdf_up is None,
                     key="ai_gen_dugme"):
            pdf_bytes = pdf_up.getvalue()
            if len(pdf_bytes) > 30 * 1024 * 1024:
                st.error("PDF je prevelik (max 30 MB).")
            else:
                with st.spinner("Claude analizira case report i gradi scenarij (30-60 s)..."):
                    try:
                        rezultat = generisi_scenarij_iz_pdfa(pdf_bytes, tezina_in, smjernice_in)
                    except Exception as e:
                        zabiljezi_gresku(e)
                        rezultat = None
                        st.error(f"Greška pri pozivu AI-ja: {e}")
                if rezultat and rezultat.get("pocetna_poruka"):
                    st.session_state["ai_gen_scenarij"] = rezultat
                    st.rerun()
                elif rezultat is not None:
                    st.error("AI nije vratio ispravan scenarij. Pokušajte ponovo.")

        gen = st.session_state.get("ai_gen_scenarij")
        if gen:
            st.success("Scenarij generisan — pregledajte, uredite po potrebi i spremite.")
            with st.expander("Obrazloženje AI-ja (sažetak case reporta i pedagoški cilj)",
                             expanded=True):
                st.write(gen.get("obrazlozenje", "—"))

            with st.form("ai_gen_forma"):
                sid_g = st.text_input("ID scenarija", value=sljedeci_scenarij_id())
                naziv_g = st.text_input("Naziv", value=gen.get("naziv", ""))
                c1, c2 = st.columns(2)
                ime_g = c1.text_input("Ime pacijenta", value=gen.get("ime", ""))
                godine_g = c2.number_input("Godine", 0, 120, int(gen.get("godine") or 40))
                tegoba_g = st.text_area("Tegoba / razlog posjete",
                                        value=gen.get("tegoba", ""), height=70)
                terapija_g = st.text_area("Postojeća terapija",
                                          value=gen.get("terapija", ""), height=70)
                skriveni_g = st.text_area("Skriveni detalji",
                                          value=gen.get("skriveni_detalji", ""), height=180)
                zastavice_g = st.text_area("Crvene zastavice",
                                           value=gen.get("crvene_zastavice", ""), height=130)
                ocekivano_g = st.text_area("Očekivano savjetovanje",
                                           value=gen.get("ocekivano", ""), height=130)
                pocetna_g = st.text_input("Početna poruka pacijenta",
                                          value=gen.get("pocetna_poruka", ""))
                rubrika_g = st.text_area("Rubrika za ocjenjivanje",
                                         value=gen.get("rubrika", ""), height=220)
                aktivan_g = st.checkbox("Aktivan (odmah vidljiv korisnicima)", value=False)
                cg1, cg2 = st.columns(2)
                spremi_g = cg1.form_submit_button("Spremi scenarij", type="primary",
                                                  use_container_width=True)
                odbaci_g = cg2.form_submit_button("Odbaci", use_container_width=True)

            if odbaci_g:
                st.session_state.pop("ai_gen_scenarij", None)
                st.rerun()
            if spremi_g:
                if not sid_g.strip() or not naziv_g.strip() or not pocetna_g.strip() \
                        or not skriveni_g.strip():
                    st.error("Obavezno: ID, naziv, početna poruka i skriveni detalji.")
                elif sid_g.strip() in SCENARIJI and not st.session_state.get("ai_gen_prepisi"):
                    st.session_state["ai_gen_prepisi"] = True
                    st.warning(f"ID '{sid_g.strip()}' već postoji — klik na 'Spremi scenarij' "
                               "još jednom će ga prepisati.")
                else:
                    ok = db_scenarij_spremi(sid_g, {
                        "naziv": naziv_g.strip(), "ime": ime_g.strip(),
                        "godine": int(godine_g), "tegoba": tegoba_g.strip(),
                        "terapija": terapija_g.strip(),
                        "skriveni_detalji": skriveni_g.strip(),
                        "crvene_zastavice": zastavice_g.strip(),
                        "ocekivano": ocekivano_g.strip(),
                        "pocetna_poruka": pocetna_g.strip(),
                        "rubrika": rubrika_g.strip(), "active": bool(aktivan_g),
                    })
                    if ok:
                        st.session_state.pop("ai_gen_scenarij", None)
                        st.session_state.pop("ai_gen_prepisi", None)
                        st.session_state["admin_flash"] = (
                            f"AI scenarij '{naziv_g.strip()}' spremljen"
                            + (" i aktivan." if aktivan_g
                               else " kao draft — aktivirajte ga u tabu Scenariji.")
                        )
                        st.rerun()

    # ══ TAB: Objave ══
    with tab_objave:
        with st.form("nova_objava"):
            tekst_o = st.text_area("Tekst objave",
                                   placeholder="Npr. Novi scenarij dostupan od ponedjeljka!")
            tip_o = st.selectbox("Tip", ["info", "warning"],
                                 format_func=lambda t: "Info (plavo)" if t == "info" else "Upozorenje (žuto)")
            if st.form_submit_button("Objavi", type="primary"):
                if len(tekst_o.strip()) < 3:
                    st.error("Upišite tekst objave.")
                elif db_objava_nova(tekst_o, tip_o):
                    st.session_state["admin_flash"] = "Objava postavljena — vidljiva svim korisnicima."
                    st.rerun()

        st.divider()
        objave = db_objave_sve()
        if not objave:
            st.caption("Nema objava.")
        for o in objave:
            o_aktivna = o.get("active", False)
            badge_bg, badge_boja, badge_txt = (
                ("#dcfce7", "#16a34a", "Aktivna") if o_aktivna else ("#e2e8f0", "#64748b", "Skrivena")
            )
            st.markdown(f"""
            <div style="background:white;border-radius:12px;padding:14px 20px;margin-bottom:4px;
                 box-shadow:0 1px 3px rgba(0,0,0,0.05);display:flex;align-items:center;gap:12px">
                <div style="flex:1">
                    <div style="color:#1e293b">{o.get('tekst','')}</div>
                    <div style="font-size:12px;color:#94a3b8;margin-top:3px">
                        {o.get('tip','info')} · {str(o.get('created_at',''))[:16].replace('T',' ')}
                    </div>
                </div>
                <span style="background:{badge_bg};color:{badge_boja};padding:4px 12px;border-radius:16px;
                      font-size:12px;font-weight:600">{badge_txt}</span>
            </div>""", unsafe_allow_html=True)
            co1, co2 = st.columns(2)
            with co1:
                lbl = "Sakrij" if o_aktivna else "Prikaži"
                if st.button(lbl, key=f"obj_akt_{o['id']}", use_container_width=True):
                    if db_objava_aktivna(o["id"], not o_aktivna):
                        st.rerun()
            with co2:
                if st.button("Obriši", key=f"obj_del_{o['id']}", use_container_width=True):
                    if db_objava_obrisi(o["id"]):
                        st.rerun()

    # ══ TAB: Masovni email (Resend) ══
    with tab_email:
        st.caption(
            "Pošaljite email svim ili odabranim korisnicima. "
            "Poruka se šalje u standardnom vizuelnom okviru platforme."
        )
        korisnici_email = db_svi_korisnici()
        if not korisnici_email:
            st.caption("Nema odobrenih korisnika.")
        else:
            opcije_k = {
                f"{k.get('full_name', '—')} ({k['email']})": k
                for k in korisnici_email
            }
            with st.form("bulk_email_forma"):
                mod_primaoci = st.radio(
                    "Primaoci",
                    ["Svi odobreni korisnici", "Odabrani korisnici"],
                    horizontal=True,
                )
                izbor_k = st.multiselect(
                    "Odaberite korisnike (samo za opciju 'Odabrani korisnici')",
                    list(opcije_k.keys()),
                )
                subject_in = st.text_input(
                    "Naslov emaila", placeholder="Npr. Novi scenarij dostupan!"
                )
                poruka_in = st.text_area(
                    "Poruka", height=160,
                    placeholder="Tekst poruke — svaki korisnik dobija personalizovan pozdrav.",
                )
                posalji_bulk = st.form_submit_button(
                    "Pošalji email", type="primary", use_container_width=True
                )

            if posalji_bulk:
                if mod_primaoci == "Odabrani korisnici":
                    primaoci = [opcije_k[o] for o in izbor_k]
                else:
                    primaoci = korisnici_email
                if not primaoci:
                    st.error("Odaberite barem jednog primaoca.")
                elif not subject_in.strip() or len(poruka_in.strip()) < 5:
                    st.error("Upišite naslov i tekst poruke.")
                else:
                    traka = st.progress(0.0, text="Slanje...")
                    uspjeh, greske = 0, []
                    for idx, kor in enumerate(primaoci):
                        ok, msg = posalji_email_masovni(
                            kor["email"], kor.get("full_name", ""),
                            subject_in.strip(), poruka_in,
                        )
                        if ok:
                            uspjeh += 1
                        else:
                            greske.append(f"{kor['email']}: {msg}")
                        traka.progress(
                            (idx + 1) / len(primaoci),
                            text=f"Slanje... {idx + 1}/{len(primaoci)}",
                        )
                        time.sleep(0.6)  # Resend rate limit: 2 zahtjeva/s
                    traka.empty()
                    st.success(f"Poslano: **{uspjeh}** od {len(primaoci)} emaila.")
                    for g in greske:
                        st.warning(g)


def prikazi_login():
    gdpr_flash = st.session_state.pop("gdpr_flash", None)
    if gdpr_flash:
        st.success(gdpr_flash)
    # Centrirani login
    col1, col2, col3 = st.columns([1, 10, 1])
    with col2:
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.image("logo.png", use_container_width=True)

        st.markdown("""
        <div style='text-align:center;margin:16px 0 28px'>
            <h2 style='color:#1E3A8A;margin-bottom:4px'>Clinical Case Simulator</h2>
            <p style='color:#64748b;margin:0'>Edu Pharma Community · Farmaceutski trening</p>
        </div>
        """, unsafe_allow_html=True)

        # ── Demo slučaj (bez registracije, bez API troška) ──
        st.markdown("""
        <div style='background:linear-gradient(135deg,#0D8A9E,#1E3A8A);border-radius:16px;
             padding:20px 24px;margin-bottom:12px;color:white'>
            <div style='font-size:12px;letter-spacing:1.2px;text-transform:uppercase;opacity:.85'>Bez registracije</div>
            <div style='font-size:19px;font-weight:700;margin-top:4px'>Isprobajte jedan slučaj</div>
            <div style='font-size:14px;opacity:.9;margin-top:6px'>
                Pravi klinički slučaj iz apoteke, pet odluka za pultom. Traje dvije minute.</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Otvori demo slučaj", use_container_width=True, key="otvori_demo"):
            st.session_state["prikazi_demo"] = True
            st.rerun()

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

        # ── Prijava sekcija ──
        st.markdown("""
        <div style='background:white;border-radius:16px;padding:24px;margin-bottom:20px;
             box-shadow:0 2px 8px rgba(0,0,0,0.06);border-top:4px solid #2FB7C6'>
            <div style='font-size:20px;font-weight:700;color:#1e293b;margin-bottom:4px'>Prijava</div>
            <div style='font-size:14px;color:#64748b'>Unesite podatke za pristup svom nalogu</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            email = st.text_input("Email adresa", placeholder="Upišite vaš email")
            lozinka = st.text_input("Lozinka", type="password", placeholder="Upišite vašu lozinku", autocomplete="off")
            submit = st.form_submit_button("Prijavi se", type="primary", use_container_width=True)

        if submit:
            if not email or not lozinka:
                st.error("Unesite email i lozinku.")
            else:
                k, poruka = db_login(email, lozinka)
                if k:
                    st.session_state.update({
                        "ulogovan": True,
                        "korisnik": k,
                        "korisnik_email": k["email"],
                        "korisnik_ime": k.get("full_name", email),
                    })
                    st.rerun()
                else:
                    st.error(poruka)

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

        # ── Registracija sekcija ──
        st.markdown("""
        <div style='background:white;border-radius:16px;padding:24px;margin-bottom:20px;
             box-shadow:0 2px 8px rgba(0,0,0,0.06);border-top:4px solid #64748b'>
            <div style='font-size:20px;font-weight:700;color:#1e293b;margin-bottom:4px'>Registracija</div>
            <div style='font-size:14px;color:#64748b'>Nemate nalog? Pošaljite zahtjev za pristup</div>
        </div>
        """, unsafe_allow_html=True)

        with st.form("reg_form"):
            ime = st.text_input("Ime i prezime", placeholder="Upišite vaše ime i prezime")
            email_r = st.text_input("Email adresa", placeholder="Upišite vaš email", key="er")
            institucija = st.text_input("Apoteka / Institucija", placeholder="Upišite naziv apoteke ili institucije")
            nadimak_r = st.text_input(
                "Nadimak za ljestvicu",
                placeholder="Npr. Farmaceut71 — može i vaše ime ako želite",
                help="Ovo je jedino što drugi vide na ljestvici. Ime, prezime i apoteka se nikad ne prikazuju.")
            loz1 = st.text_input("Lozinka", type="password", placeholder="Upišite lozinku (min. 6 znakova)", key="l1", autocomplete="new-password")
            loz2 = st.text_input("Ponovite lozinku", type="password", placeholder="Ponovite lozinku", key="l2", autocomplete="new-password")
            submit_r = st.form_submit_button("Pošalji zahtjev za registraciju", use_container_width=True)

        if submit_r:
            if not all([ime, email_r, loz1, loz2]):
                st.error("Popunite sva polja.")
            elif nadimak_r.strip() and not (3 <= len(nadimak_r.strip()) <= 24):
                st.error("Nadimak mora imati između 3 i 24 znaka.")
            elif nadimak_r.strip() and not nadimak_slobodan(nadimak_r, email_r):
                st.error("Taj nadimak je već zauzet. Izaberite drugi.")
            elif loz1 != loz2:
                st.error("Lozinke se ne podudaraju.")
            elif len(loz1) < 6:
                st.error("Lozinka mora imati min. 6 znakova.")
            else:
                ok, poruka = db_registruj(email_r, loz1, ime, institucija, nadimak_r)
                if ok:
                    st.success("Zahtjev primljen! Bit ćete obaviješteni kada admin odobri pristup.")
                    st.info(f"Pristup odobrava administrator ručno, samo članovima Edu Pharma Community. Kontakt: {KONTAKT_EMAIL}")
                else:
                    st.error(poruka)

        # ── Disable autocomplete putem JS ──
        st.markdown("""
        <script>
        const inputs = window.parent.document.querySelectorAll('input[type="password"]');
        inputs.forEach(el => {
            el.setAttribute('autocomplete', 'off');
            el.setAttribute('autocorrect', 'off');
            el.setAttribute('autocapitalize', 'off');
            el.setAttribute('spellcheck', 'false');
        });
        </script>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.warning("Alat je isključivo za **edukaciju i vježbu farmaceutskog savjetovanja**. Nije namijenjen kliničkom odlučivanju.")


# ─── MAIN ─────────────────────────────────────────────────────────────────────
if not st.session_state.get("ulogovan"):
    # Demo je otvoren svima i ne troši API — pravi simulator ostaje iza odobrenja admina.
    if st.session_state.get("prikazi_demo"):
        c1, c2, c3 = st.columns([1, 10, 1])
        with c2:
            if prikazi_demo():
                st.session_state["prikazi_demo"] = False
                st.rerun()
        st.stop()
    prikazi_login()
    st.stop()

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("logo.png", use_container_width=True)
    st.markdown(f"""
    <div style='margin:12px 0;padding:12px;background:rgba(255,255,255,0.12);border-radius:10px'>
        <div style='font-size:12px;opacity:0.7'>Prijavljeni kao</div>
        <div style='font-weight:600;font-size:14px'>{st.session_state.get('korisnik_ime','')}</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    nav_opcije = ["Scenariji", "Ljestvica", "Moji rezultati"]
    if je_admin():
        nav_opcije.append("Admin")
    stranica = st.radio(
        "Navigacija",
        nav_opcije,
        label_visibility="collapsed",
    )
    st.markdown("---")
    if st.button("Odjavi se", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ─── Objave / banner ─────────────────────────────────────────────────────────
for _obj in _ucitaj_objave():
    if _obj.get("tip") == "warning":
        st.warning(_obj["tekst"])
    else:
        st.info(_obj["tekst"])

# ─── Stranice ────────────────────────────────────────────────────────────────
if "Ljestvica" in stranica:
    prikazi_leaderboard()
    st.stop()

if "Moji rezultati" in stranica:
    prikazi_moje_rezultate()
    prikazi_gdpr_brisanje()
    st.stop()

if "Admin" in stranica:
    prikazi_admin()
    st.stop()

# ─── SCENARIJI ───────────────────────────────────────────────────────────────
st.warning("Alat je isključivo za **edukaciju i vježbu**. Nije podrška kliničkom odlučivanju.")

email = st.session_state.get("korisnik_email", "")
odabrani_id = st.session_state.get("odabrani_scenarij", None)

# ─── Ako nema odabranog scenarija → prikaži kartice ──────────────────────────
if odabrani_id is None:
    st.markdown("## Klinički slučajevi")

    # Sortiraj: nezavršeni prvi, završeni ispod
    svi = [(sid, s) for sid, s in SCENARIJI.items() if s.get("aktivan", True)]
    zavrseni_ids = db_zavrseni_scenariji(email)
    nezavrseni = [(sid, sc) for sid, sc in svi if sid not in zavrseni_ids]
    zavrseni = [(sid, sc) for sid, sc in svi if sid in zavrseni_ids]

    def prikazi_karticu(sc_id, sc, uradjen):
        status_bg = "#dcfce7" if uradjen else "#dbeafe"
        status_boja = "#16a34a" if uradjen else "#2C6FBE"
        status_tekst = "Završeno" if uradjen else "Dostupno"
        border_top = f"border-top: 4px solid {status_boja};"

        st.markdown(f"""
        <div style="background:white;border-radius:16px;padding:24px 28px;margin-bottom:16px;
             box-shadow:0 2px 10px rgba(0,0,0,0.08);{border_top}">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
                <span style="background:{status_bg};color:{status_boja};padding:4px 14px;border-radius:20px;
                      font-size:12px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase">{status_tekst}</span>
            </div>
            <div style="font-weight:700;font-size:18px;color:#1e293b;margin-bottom:8px">{sc['naziv']}</div>
            <div style="font-size:14px;color:#475569;line-height:1.5;margin-bottom:6px">
                <strong>Pacijent:</strong> {sc['ime']}, {sc['godine']} god.
            </div>
            <div style="font-size:14px;color:#475569;line-height:1.5;margin-bottom:6px">
                <strong>Razlog posjete:</strong> {sc['tegoba']}
            </div>
            <div style="font-size:14px;color:#475569;line-height:1.5">
                <strong>Terapija:</strong> {sc['terapija']}
            </div>
        </div>""", unsafe_allow_html=True)

        btn_label = "Pogledaj rezultat" if uradjen else "Započni scenarij"
        btn_type = "secondary" if uradjen else "primary"
        if st.button(btn_label, key=f"btn_{sc_id}", type=btn_type, use_container_width=True):
            st.session_state["odabrani_scenarij"] = sc_id
            st.rerun()

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if nezavrseni:
        st.markdown(f"### Nezavršeni scenariji ({len(nezavrseni)})")
        for sc_id, sc in nezavrseni:
            prikazi_karticu(sc_id, sc, False)

    if zavrseni:
        st.markdown(f"### Završeni scenariji ({len(zavrseni)})")
        for sc_id, sc in zavrseni:
            prikazi_karticu(sc_id, sc, True)

    st.stop()

# ─── Odabrani scenarij — prikaz ──────────────────────────────────────────────
sc = SCENARIJI.get(odabrani_id)
if not sc:
    st.session_state["odabrani_scenarij"] = None
    st.rerun()
vec_uradjen = db_vec_uradio(email, odabrani_id)

if st.button("Nazad na listu scenarija", type="secondary"):
    st.session_state["odabrani_scenarij"] = None
    st.rerun()

st.markdown(f"## {sc['naziv']}")

st.markdown(f"""
<div style="background:white;border-radius:14px;padding:18px 22px;margin:12px 0;
     box-shadow:0 1px 4px rgba(0,0,0,0.07)">
    <div style="font-size:14px;color:#475569;line-height:1.7">
        <strong>Pacijent:</strong> {sc['ime']}, {sc['godine']} god.<br>
        <strong>Terapija:</strong> {sc['terapija']}<br>
        <strong>Razlog posjete:</strong> {sc['tegoba']}
    </div>
</div>""", unsafe_allow_html=True)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ─── Session state ────────────────────────────────────────────────────────────
kljuc = f"chat_{odabrani_id}"
if kljuc not in st.session_state:
    st.session_state[kljuc] = {
        "poruke_api": [], "poruke_prikaz": [],
        "ocjena": None, "zavrseno": False, "broj_poteza": 0,
        "zadnji_potez_vrijeme": time.time(),
    }
    if not vec_uradjen:
        db_log_upotrebu("start", odabrani_id)
stanje = st.session_state[kljuc]

# ─── Završeni scenarij ────────────────────────────────────────────────────────
if vec_uradjen:
    st.info("Ovaj scenarij ste već završili. Rezultati su trajno sačuvani.")

    with st.expander("Transkript razgovora"):
        for p in stanje["poruke_prikaz"]:
            with st.chat_message(p["role"]):
                st.markdown(p["content"])

    ocjena_data = stanje.get("ocjena") or db_dohvati_ocjenu(email, odabrani_id)
    if ocjena_data:
        prikazi_ocjenu(ocjena_data)
    else:
        st.success("Scenarij uspješno završen. Ocjena nije dostupna.")
    st.stop()

# ─── Aktivni razgovor ─────────────────────────────────────────────────────────
for p in stanje["poruke_prikaz"]:
    with st.chat_message(p["role"]):
        st.markdown(p["content"])

if not stanje["poruke_prikaz"]:
    prva = sc["pocetna_poruka"]
    stanje["poruke_prikaz"].append({"role": "assistant", "content": prva})
    stanje["poruke_api"].append({"role": "assistant", "content": prva})
    with st.chat_message("assistant"):
        st.markdown(prva)

if not stanje["zavrseno"]:
    # ── Dnevni limit AI poruka (kontrola troškova) ──
    if db_poruka_danas(email) >= DNEVNI_LIMIT_PORUKA:
        if stanje["broj_poteza"] > 0:
            st.warning("Dostigli ste dnevni limit poruka — savjetovanje se završava i ocjenjuje.")
            pokreni_evaluaciju(stanje, sc, odabrani_id)
            st.rerun()
        else:
            st.error(
                f"Dostigli ste dnevni limit od {DNEVNI_LIMIT_PORUKA} AI poruka. "
                "Limit se resetuje u ponoć (UTC) — nastavite sutra."
            )
            st.stop()

    preostalo = MAX_POTEZA - stanje["broj_poteza"]

    # ── Tajmer: 120s po odgovoru; istek NE briše razgovor, samo troši pokušaj ──
    # Kazna se obračunava lijeno (pri sljedećoj interakciji) — poruka koju korisnik
    # pošalje nakon isteka se normalno obrađuje, bez rerun-a koji bi je progutao.
    TAJMER_SEKUNDI = 120
    sad = time.time()
    if "zadnji_potez_vrijeme" not in stanje:
        stanje["zadnji_potez_vrijeme"] = sad

    proteklo = sad - stanje["zadnji_potez_vrijeme"]
    propusteni = int(proteklo // TAJMER_SEKUNDI)

    if propusteni > 0 and preostalo > 0:
        izgubljeno = min(propusteni, preostalo)
        stanje["broj_poteza"] += izgubljeno
        stanje["izgubljeno_ukupno"] = stanje.get("izgubljeno_ukupno", 0) + izgubljeno
        stanje["zadnji_potez_vrijeme"] = sad
        proteklo = 0
        preostalo = MAX_POTEZA - stanje["broj_poteza"]
        if preostalo <= 0:
            st.warning("Vrijeme je isteklo za sve pokušaje. Savjetovanje se završava i ocjenjuje.")
            pokreni_evaluaciju(stanje, sc, odabrani_id)
            st.rerun()

    if stanje.get("izgubljeno_ukupno"):
        st.warning(
            f"Zbog isteka vremena do sada ste izgubili {stanje['izgubljeno_ukupno']} pokušaj(a). "
            "Razgovor i vaše poruke ostaju sačuvani."
        )

    preostalo_s = int(TAJMER_SEKUNDI - (proteklo % TAJMER_SEKUNDI))

    st.caption(f"Preostalo unosa: **{preostalo} / {MAX_POTEZA}**")

    # Countdown tajmer — mora ići kroz components.html jer se <script> u
    # st.markdown ne izvršava (zato je stari tajmer stajao zamrznut na 59s)
    timer_html = """
<div style="font-family:Inter,Arial,sans-serif">
  <div style="display:flex;justify-content:space-between;align-items:baseline;font-size:13px;color:#51637A;margin-bottom:4px">
    <span>Vrijeme za odgovor</span>
    <span id="tNum" style="font-weight:700;font-size:17px;color:#1E3A8A;font-variant-numeric:tabular-nums">--:--</span>
  </div>
  <div style="background:#e2e8f0;border-radius:8px;height:8px;overflow:hidden">
    <div id="tFill" style="background:linear-gradient(90deg,#2FB7C6,#2C6FBE);height:100%;width:100%;transition:width 1s linear"></div>
  </div>
  <div id="tMsg" style="display:none;font-size:12.5px;color:#b91c1c;font-weight:600;margin-top:5px">
    Vrijeme je isteklo — jedan pokušaj se oduzima, ali razgovor i vaš tekst ostaju. Odbrojavanje ide ispočetka.
  </div>
</div>
<script>
var remaining = __PREOSTALO__;
var total = __TOTAL__;
var tNum = document.getElementById('tNum');
var tFill = document.getElementById('tFill');
var tMsg = document.getElementById('tMsg');
function fmt(s) { var m = Math.floor(s/60), ss = s%60; return m + ':' + (ss<10?'0':'') + ss; }
function boja(s) {
  if (s <= 15) return 'linear-gradient(90deg,#ef4444,#dc2626)';
  if (s <= 30) return 'linear-gradient(90deg,#f59e0b,#d97706)';
  return 'linear-gradient(90deg,#2FB7C6,#2C6FBE)';
}
function draw() {
  tNum.textContent = fmt(remaining);
  tFill.style.width = (remaining/total*100) + '%';
  tFill.style.background = boja(remaining);
  tNum.style.color = remaining <= 15 ? '#b91c1c' : '#1E3A8A';
}
draw();
setInterval(function() {
  remaining--;
  if (remaining < 0) { tMsg.style.display = 'block'; remaining = total - 1; }
  draw();
}, 1000);
</script>
""".replace("__PREOSTALO__", str(preostalo_s)).replace("__TOTAL__", str(TAJMER_SEKUNDI))
    components.html(timer_html, height=84)

    st.markdown("""
    <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:10px 14px;
         margin-bottom:10px;font-size:13px;color:#0c4a6e;line-height:1.5">
        <strong>Savjet:</strong> Pitajte kao za pultom — jedno do dva pitanja, pa slušajte.
        Na tri i više pitanja odjednom pacijent odgovara samo na prva dva, kao i u stvarnosti.
    </div>
    """, unsafe_allow_html=True)

    unos = st.chat_input("Vaš odgovor kao farmaceut...")
    if unos:
        stanje["poruke_prikaz"].append({"role": "user", "content": unos})
        stanje["poruke_api"].append({"role": "user", "content": unos})
        stanje["broj_poteza"] += 1
        stanje["zadnji_potez_vrijeme"] = time.time()
        with st.chat_message("user"):
            st.markdown(unos)

        if stanje["broj_poteza"] < MAX_POTEZA:
            with st.chat_message("assistant"):
                with st.spinner(""):
                    odg = pozovi_pacijenta(stanje["poruke_api"], sc)
                st.markdown(odg)
                stanje["poruke_prikaz"].append({"role": "assistant", "content": odg})
                stanje["poruke_api"].append({"role": "assistant", "content": odg})
            st.rerun()
        else:
            st.info(f"Dostigli ste maksimalan broj unosa ({MAX_POTEZA}). Savjetovanje se završava.")
            pokreni_evaluaciju(stanje, sc, odabrani_id)
            st.rerun()

st.divider()
if not stanje["zavrseno"] and stanje["broj_poteza"] >= 2:
    if st.button("Završi savjetovanje i dobij ocjenu", type="primary", use_container_width=True):
        pokreni_evaluaciju(stanje, sc, odabrani_id)
        st.rerun()

if stanje["zavrseno"] and stanje["ocjena"]:
    prikazi_ocjenu(stanje["ocjena"])
