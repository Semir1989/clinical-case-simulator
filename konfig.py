"""Podesavanja, klijenti i konstante — sve na jednom mjestu.

Ovaj modul se uvozi prvi i nijedan drugi modul projekta ne uvozi. Time je
redoslijed uvoza uvijek jednosmjeran: konfig -> baza/posta -> promptovi ->
motor/ocjena -> scenariji -> ui -> app.
"""
import os
from contextvars import ContextVar

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

ADMIN_EMAIL = "info@farmaceutupraksi.ba"
KONTAKT_EMAIL = "info@farmaceutupraksi.ba"

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


# ─── Ko je trenutno aktivan ──────────────────────────────────────────────────
# Streamlit drzi korisnika u st.session_state, a API (Komunikator) nema sesiju —
# svaki zahtjev postavlja svoj kontekst. Bez ovoga bi usage_log iz API-ja
# upisivao prazan email, a dnevni limit poruka bi brojao nulu.
_AKTIVNI = ContextVar("aktivni", default=None)


def postavi_aktivnog(email, scenarij=""):
    """API poziva ovo na pocetku zahtjeva. Vraca token za ponistavanje."""
    return _AKTIVNI.set({"email": email or "", "scenarij": scenarij or ""})


def aktivni_email():
    a = _AKTIVNI.get()
    if a is not None:
        return a["email"]
    try:
        return st.session_state.get("korisnik_email", "")
    except Exception:      # van Streamlita (API, skripte) sesije nema
        return ""


def aktivni_scenarij():
    a = _AKTIVNI.get()
    if a is not None:
        return a["scenarij"]
    try:
        return st.session_state.get("odabrani_scenarij", "")
    except Exception:
        return ""


# Broj poteza je i pedagoska i troskovna odluka: svaki potez nosi cijelu
# dosadasnju historiju, pa su zadnji potezi najskuplji. Spusteno s 10 na 7
# 9. 9. 2026. — kalibracioni transkripti su igrani na 10 i to se racuna iz
# samog transkripta (vidi kalibracija/izmjeri.py), ne iz ove konstante.
MAX_POTEZA = 7

# Vjezba je izgradjena i radi, ali je zakljucana dok se ne rijesi troskovna
# strana: vjezba trosi API tacno koliko i ispit, a neogranicena je. Sa 100
# aktivnih ljudi i zatecenim dnevnim limitom to je do ~1.350 USD mjesecno.
# Prekidac se vraca na True kad kvota po korisniku bude uvedena. NE brisati kod
# — sve ostalo (mode, napredak, krivulja) radi i ceka samo ovu zastavicu.
VJEZBA_OMOGUCENA = False
DNEVNI_LIMIT_PORUKA = 60  # max AI poruka po korisniku dnevno (kontrola troškova)

# Modeli — na jednom mjestu da se mogu mijenjati bez traženja po fajlu
# Pacijent ostaje na Sonnetu. Mjereno 9. 9. 2026. na skupu iz
# skripte/test_ponasanja.py: Haiku 4.5 je stedio samo ~32% (verboznost mu pojede
# prednost u cijeni), ali je izmisljao poricanja ("mokraca? pa normalna je" iako
# je u cinjenicama tamna) i sam iznosio skrivene cinjenice bez pitanja. To rusi
# cijelu mehaniku okidaca, pa usteda ne dolazi u obzir.
#
# Prelazak na Sonnet 5.5 mjeren 14. 10. 2026. (test_ponasanja + izmjeri.py,
# 4.6 protiv 5.5): pacijent bez razmišljanja jednako realan, 2-4 s umjesto
# 3-9 s; evaluator na medium odstupa 0,45 od reference (4.6: 0,65) i ocjenjuje
# za ~14 s umjesto ~41 s. Na 5.5 temperature se ne smije slati (400), a ni
# prisilni tool_choice — zato evaluator ide s "auto" i provjerom poziva alata.
MODEL_PACIJENT = "claude-sonnet-5-5"
MODEL_EVALUATOR = "claude-sonnet-5-5"
MODEL_GENERATOR = "claude-sonnet-5-5"

# Razmišljanje po ulozi. Pacijent ga ne treba: s adaptive/low bio je skuplji i
# sporiji, a ne bolji. "between_tools" je najniža postavka na 5.5 ("disabled"
# vraća 400) i radi samo do effort high.
THINKING_PACIJENT = {"type": "between_tools"}
EFFORT_EVALUATOR = "medium"   # low je bio malo tačniji, ali manje stabilan između ponavljanja
EFFORT_GENERATOR = "high"     # nije mjereno — ostaje zadana vrijednost modela

# Procjena troška — Sonnet 5.5 cijene po tokenu (USD). Novi tokenizer daje ~30%
# više tokena za isti tekst, pa je stvarna ušteda manja od razlike u cijeni.
CIJENA_ULAZ_USD = 2.00 / 1_000_000
CIJENA_IZLAZ_USD = 10.00 / 1_000_000

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
