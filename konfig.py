"""Podesavanja, klijenti i konstante — sve na jednom mjestu.

Ovaj modul se uvozi prvi i nijedan drugi modul projekta ne uvozi. Time je
redoslijed uvoza uvijek jednosmjeran: konfig -> baza/posta -> promptovi ->
motor/ocjena -> scenariji -> ui -> app.
"""
import os

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
