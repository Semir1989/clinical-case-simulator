"""
Clinical Case Simulator — Edu Pharma Community
Supabase backend · Leaderboard · Cross-device persistence · Beautiful UI
"""

import json
import os
import hashlib
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from collections import defaultdict

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

ADMIN_EMAIL = "info@farmaceutupraksi.ba"

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
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&display=swap');

/* ── Forsiran light mode — blokira dark prefers ── */
:root {
    color-scheme: light only !important;
}
html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif !important;
    color-scheme: light !important;
}
@media (prefers-color-scheme: dark) {
    html, body { background-color: #EEF6F8 !important; color: #1A2E3B !important; }
}
#MainMenu, footer { visibility: hidden; }

/* ── Sidebar collapse control — sakrij Streamlit default ── */
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {
    display: none !important;
}

/* ── Pozadina ── */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
[data-testid="block-container"] {
    background-color: #EEF6F8 !important;
}

/* ── Sidebar — tirkizni gradijent ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0D8A9E 0%, #0A6B7C 100%) !important;
}
[data-testid="stSidebar"] * { color: #FFFFFF !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.25) !important; }
[data-testid="stSidebar"] button {
    background: rgba(255,255,255,0.18) !important;
    color: white !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
    border-radius: 10px !important;
}
[data-testid="stSidebar"] button:hover {
    background: rgba(255,255,255,0.3) !important;
}

/* ── Dugmad — višestruki selektori za Streamlit 1.5x ── */
.stButton > button,
.stFormSubmitButton > button,
[data-testid="stFormSubmitButton"] button,
[data-testid="baseButton-primary"],
[data-testid="baseButton-secondary"] {
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    padding: 10px 20px !important;
    transition: all 0.2s ease !important;
}
/* Primary dugme */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"],
[data-testid="baseButton-primary"],
[data-testid="stFormSubmitButton"] button,
.stButton > button:first-of-type {
    background: linear-gradient(135deg, #1CB5C5, #0D8A9E) !important;
    border: none !important;
    color: white !important;
    -webkit-text-fill-color: white !important;
}
.stButton > button:hover,
.stFormSubmitButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 18px rgba(28,181,197,0.35) !important;
}
/* Secondary dugme */
.stButton > button[kind="secondary"],
[data-testid="baseButton-secondary"] {
    background: white !important;
    border: 2px solid #1CB5C5 !important;
    color: #0D8A9E !important;
    -webkit-text-fill-color: #0D8A9E !important;
}

/* ── Input polja — bijela pozadina, vidljiv tekst ── */
.stTextInput > div > div > input,
[data-testid="stTextInputRootElement"] input,
[data-baseweb="input"] input,
[data-baseweb="base-input"] input {
    background-color: #FFFFFF !important;
    color: #1A2E3B !important;
    -webkit-text-fill-color: #1A2E3B !important;
    border-radius: 12px !important;
    border: 1.5px solid #B2DDE4 !important;
    font-size: 15px !important;
    padding: 11px 14px !important;
}
[data-baseweb="input"],
[data-baseweb="base-input"],
[data-baseweb="input"] > div,
[data-testid="stTextInputRootElement"] > div {
    background-color: #FFFFFF !important;
}
.stTextInput > div > div > input::placeholder,
[data-baseweb="input"] input::placeholder { color: #8BAAB2 !important; -webkit-text-fill-color: #8BAAB2 !important; }
.stTextInput > div > div > input:focus,
[data-baseweb="input"]:focus-within {
    border-color: #1CB5C5 !important;
    box-shadow: 0 0 0 3px rgba(28,181,197,0.15) !important;
    outline: none !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    background: white !important;
    border-radius: 12px !important;
    border: 1.5px solid #B2DDE4 !important;
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
    font-weight: 500 !important;
    color: #5A8A96 !important;
    font-size: 14px !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #1CB5C5, #0D8A9E) !important;
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
    border: 2px solid #B2DDE4 !important;
    background: white !important;
}
[data-testid="stChatInput"] > div:focus-within {
    border-color: #1CB5C5 !important;
    box-shadow: 0 0 0 3px rgba(28,181,197,0.12) !important;
}

/* ── Metric kartice ── */
[data-testid="metric-container"] {
    background: white !important;
    border-radius: 14px !important;
    padding: 18px !important;
    box-shadow: 0 1px 6px rgba(0,0,0,0.07) !important;
    border-top: 3px solid #1CB5C5 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #0D8A9E !important;
    font-weight: 800 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: white !important;
    border-radius: 14px !important;
    border: 1.5px solid #D4EEF2 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
}

/* ── Divider ── */
hr { border-color: #D4EEF2 !important; }

/* ── Form ── */
[data-testid="stForm"] {
    background: white !important;
    border-radius: 16px !important;
    padding: 20px !important;
    border: 1.5px solid #D4EEF2 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
}

/* ── Login/Registracija — veći font u formi ── */
[data-testid="stForm"] label {
    font-size: 15px !important;
    font-weight: 600 !important;
    color: #1e293b !important;
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
</style>
""", unsafe_allow_html=True)

# ─── Floating meni dugme (custom HTML/JS) ────────────────────────────────────
st.markdown("""
<div id="menuBtn" onclick="
    var sb = window.parent.document.querySelector('[data-testid=stSidebar]');
    var ctrl = window.parent.document.querySelector('[data-testid=stSidebarCollapsedControl] button')
             || window.parent.document.querySelector('[data-testid=collapsedControl] button');
    if (sb && sb.getAttribute('aria-expanded') === 'true') {
        var closeBtn = sb.querySelector('button[kind=header]')
                     || sb.querySelector('[data-testid=stSidebarNavButton]');
        if (closeBtn) closeBtn.click();
    } else if (ctrl) {
        ctrl.click();
    } else if (sb) {
        sb.setAttribute('aria-expanded', 'true');
        sb.style.display = 'block';
        sb.style.transform = 'none';
    }
" style="
    position: fixed;
    top: 14px;
    left: 14px;
    z-index: 999999;
    width: 48px;
    height: 48px;
    background: linear-gradient(135deg, #1CB5C5, #0D8A9E);
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 4px 16px rgba(13,138,158,0.5);
    border: 2px solid rgba(255,255,255,0.7);
    transition: all 0.2s ease;
    user-select: none;
" onmouseover="this.style.transform='scale(1.1)';this.style.boxShadow='0 6px 22px rgba(13,138,158,0.65)'"
  onmouseout="this.style.transform='scale(1)';this.style.boxShadow='0 4px 16px rgba(13,138,158,0.5)'"
>
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5"
         stroke-linecap="round" stroke-linejoin="round">
        <line x1="3" y1="6" x2="21" y2="6"></line>
        <line x1="3" y1="12" x2="21" y2="12"></line>
        <line x1="3" y1="18" x2="21" y2="18"></line>
    </svg>
</div>
<style>
    #menuBtn { animation: menuPulse 2s ease-in-out 3; }
    @keyframes menuPulse {
        0%, 100% { box-shadow: 0 4px 16px rgba(13,138,158,0.5); }
        50% { box-shadow: 0 4px 28px rgba(13,138,158,0.85), 0 0 0 8px rgba(28,181,197,0.2); }
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

MAX_POTEZA = 7

# ─── DB funkcije ──────────────────────────────────────────────────────────────
def hash_loz(lozinka: str) -> str:
    return hashlib.sha256(lozinka.encode()).hexdigest()


def db_registruj(email, lozinka, ime, institucija):
    if not db:
        return False, "Baza podataka nije dostupna."
    try:
        r = db.table("users").select("email").eq("email", email.lower().strip()).execute()
        if r.data:
            return False, "Email je već registrovan."
        db.table("users").insert({
            "email": email.lower().strip(),
            "password_hash": hash_loz(lozinka),
            "full_name": ime.strip(),
            "institution": institucija.strip(),
            "approved": False,
        }).execute()
        return True, "ok"
    except Exception as e:
        return False, f"Greška: {e}"


def db_login(email, lozinka):
    if not db:
        return None, "Baza podataka nije dostupna."
    try:
        r = db.table("users").select("*").eq("email", email.lower().strip()).execute()
        if not r.data:
            return None, "Korisnik nije pronađen."
        k = r.data[0]
        if k["password_hash"] != hash_loz(lozinka):
            return None, "Pogrešna lozinka."
        if not k.get("approved", False):
            return None, "Vaš nalog čeka odobrenje. Kontaktirajte semir.mehovic1989@gmail.com"
        return k, "ok"
    except Exception as e:
        return None, f"Greška: {e}"


def db_vec_uradio(email, scenario_id):
    if not db:
        return False
    try:
        r = db.table("attempts").select("id").eq("user_email", email).eq("scenario_id", scenario_id).execute()
        return len(r.data) > 0
    except Exception:
        return False


def db_spremi(email, scenario_id, rezultat):
    if not db:
        return
    try:
        db.table("attempts").insert({
            "user_email": email,
            "scenario_id": scenario_id,
            "score": float(rezultat.get("ukupna_ocjena", 0)),
            "anamneza": int(rezultat.get("anamneza", 0)),
            "komunikacija": int(rezultat.get("komunikacija", 0)),
            "sigurnost": int(rezultat.get("sigurnost", 0)),
            "result_json": json.dumps(rezultat, ensure_ascii=False),
        }).execute()
    except Exception:
        pass


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
        im = db.table("users").select("email, full_name, institution").in_("email", emailovi).execute()
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
                "ime": k.get("full_name", em),
                "institucija": k.get("institution", ""),
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


# ─── Email notifikacija (Resend) ─────────────────────────────────────────────
def posalji_email_odobrenje(korisnik_email, korisnik_ime):
    try:
        api_key = st.secrets.get("RESEND_API_KEY", "")
        from_email = st.secrets.get("RESEND_FROM", "onboarding@resend.dev")

        if not api_key:
            return False, "RESEND_API_KEY nije konfigurisan u secrets."

        html = f"""
        <div style="font-family:Inter,sans-serif;max-width:520px;margin:0 auto;padding:32px">
            <div style="text-align:center;margin-bottom:24px">
                <h2 style="color:#0D8A9E;margin:0">Clinical Case Simulator</h2>
                <p style="color:#64748b;margin:4px 0 0">Edu Pharma Community</p>
            </div>
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
            <p style="color:#64748b;font-size:13px;margin-top:24px;border-top:1px solid #e2e8f0;padding-top:16px">
                Edu Pharma Community · Farmaceutski trening
            </p>
        </div>
        """

        payload = json.dumps({
            "from": from_email,
            "to": [korisnik_email],
            "subject": "Vaš nalog je odobren — Clinical Case Simulator",
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
        return False, f"Resend HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


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
def napravi_system_prompt(sc):
    staticki = (
        "Ti si pacijent koji je upravo usao u apoteku. Pravila:\n"
        "1. Govori u prvom licu kao obican pacijent, jezik laika.\n"
        "2. Max 2 recenice po replici.\n"
        "3. Ne otkrivaj simptome bez pitanja.\n"
        "4. Budi blago skeptican.\n"
        "5. Bez informacija ako te ne pitaju direktno.\n"
        "6. Ostani u ulozi, nikad ne izlazi.\n"
        "7. Govori na bosanskom jeziku."
    )
    dinamicki = (
        f"\nGlumaš: {sc['ime']}, {sc['godine']} god.\n"
        f"Tegoba: {sc['tegoba']}\n"
        f"Terapija: {sc['terapija']}\n"
        f"Skriveni detalji (SAMO na pravo pitanje): {sc['skriveni_detalji']}"
    )
    return [
        {"type": "text", "text": staticki, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": dinamicki},
    ]


def pozovi_pacijenta(poruke, sc):
    r = ai.messages.create(
        model="claude-sonnet-4-6", max_tokens=300,
        system=napravi_system_prompt(sc), messages=poruke,
    )
    return r.content[0].text


def pozovi_evaluatora(transkript, sc):
    prompt = f"""Ocijeni savjetovanje farmaceuta u apoteci.
Scenarij: {sc['ime']}, {sc['godine']} god. — {sc['tegoba']}
Crvene zastavice: {sc['crvene_zastavice']}
Ocekivano savjetovanje: {sc['ocekivano']}
{sc.get('rubrika', '')}
Transkript:\n{transkript}

Vrati ISKLJUCIVO validan JSON bez ikakvog teksta prije ili poslije:
{{"anamneza":<0-10>,"komunikacija":<0-10>,"sigurnost":<0-10>,"ukupna_ocjena":<0.0-10.0>,"propustena_pitanja":["..."],"pohvale":["..."],"smjernice":["..."]}}"""
    r = ai.messages.create(
        model="claude-sonnet-4-6", max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return r.content[0].text


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
        json_tekst = pozovi_evaluatora(transkript, sc)

    rezultat = izvuci_json(json_tekst)
    if rezultat:
        stanje["ocjena"] = rezultat
        stanje["zavrseno"] = True
        db_spremi(st.session_state.get("korisnik_email", ""), sc_id, rezultat)
    else:
        st.error("Greška pri analizi ocjene. Pokušaj ponovo.")
        stanje["zavrseno"] = False


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
            st.success(p)

    if r.get("propustena_pitanja"):
        st.markdown("#### Propuštena pitanja")
        for p in r["propustena_pitanja"]:
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
    border = "border:2px solid #1a3a8f;" if je_ja else ""
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
                <div style="font-size:13px;color:#64748b">{red['institucija']} · {red['slucajeva']} slučaj/eva</div>
            </div>
            <div style="text-align:right;flex-shrink:0">
                <div style="font-size:26px;font-weight:800;color:#1a3a8f">{vrijednost}</div>
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
        <div style="background:linear-gradient(135deg,#1a3a8f,#0f2560);border-radius:14px;
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


def prikazi_moje_rezultate():
    st.markdown("## Moji rezultati")
    email = st.session_state.get("korisnik_email", "")
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


def prikazi_admin():
    st.markdown("## Admin panel")

    # ── Obradi akciju iz session_state (ako postoji) ──
    akcija = st.session_state.pop("admin_akcija", None)
    if akcija:
        email_k = akcija["email"]
        ime_k = akcija["ime"]
        if akcija["tip"] == "odobri":
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
            if db_odbij_korisnika(email_k):
                st.info(f"Korisnik **{ime_k}** ({email_k}) je obrisan.")
            else:
                st.error(f"Greška pri brisanju korisnika {email_k}.")

    # ── Zahtjevi na čekanju ──
    st.markdown("### Zahtjevi na čekanju")
    neodobreni = db_neodobreni_korisnici()

    if not neodobreni:
        st.markdown("""
        <div style="text-align:center;padding:40px;color:#94a3b8">
            <div style="font-size:16px;font-weight:600;color:#94a3b8">—</div>
            <div style="margin-top:8px">Nema zahtjeva na čekanju.</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.info(f"**{len(neodobreni)}** korisnik/a čeka odobrenje.")
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

            col_a, col_b = st.columns(2)
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

    st.divider()

    # ── Lista odobrenih korisnika ──
    st.markdown("### Odobreni korisnici")
    odobreni = db_svi_korisnici()
    if not odobreni:
        st.caption("Nema odobrenih korisnika.")
    else:
        st.caption(f"Ukupno: **{len(odobreni)}** korisnik/a")
        for i, k in enumerate(odobreni):
            st.markdown(f"""
            <div style="background:white;border-radius:12px;padding:14px 20px;margin-bottom:4px;
                 box-shadow:0 1px 3px rgba(0,0,0,0.05);display:flex;align-items:center;gap:12px">
                <div style="flex:1">
                    <div style="font-weight:600;color:#1e293b">{k.get('full_name','—')}</div>
                    <div style="font-size:13px;color:#64748b">{k.get('institution','')} · {k['email']}</div>
                </div>
                <span style="background:#dcfce7;color:#16a34a;padding:4px 12px;border-radius:16px;
                      font-size:12px;font-weight:600">Aktivan</span>
            </div>""", unsafe_allow_html=True)
            if k["email"] != ADMIN_EMAIL:
                if st.button("Obriši", key=f"brisi_{i}", use_container_width=False):
                    st.session_state["admin_akcija"] = {
                        "tip": "brisi", "email": k["email"],
                        "ime": k.get("full_name", k["email"]),
                    }
                    st.rerun()


def prikazi_login():
    # Centrirani login
    col1, col2, col3 = st.columns([1, 10, 1])
    with col2:
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.image("logo.png", use_container_width=True)

        st.markdown("""
        <div style='text-align:center;margin:16px 0 28px'>
            <h2 style='color:#1a3a8f;margin-bottom:4px'>Clinical Case Simulator</h2>
            <p style='color:#64748b;margin:0'>Edu Pharma Community · Farmaceutski trening</p>
        </div>
        """, unsafe_allow_html=True)

        # ── Prijava sekcija ──
        st.markdown("""
        <div style='background:white;border-radius:16px;padding:24px;margin-bottom:20px;
             box-shadow:0 2px 8px rgba(0,0,0,0.06);border-top:4px solid #0D8A9E'>
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
            loz1 = st.text_input("Lozinka", type="password", placeholder="Upišite lozinku (min. 6 znakova)", key="l1", autocomplete="new-password")
            loz2 = st.text_input("Ponovite lozinku", type="password", placeholder="Ponovite lozinku", key="l2", autocomplete="new-password")
            submit_r = st.form_submit_button("Pošalji zahtjev za registraciju", use_container_width=True)

        if submit_r:
            if not all([ime, email_r, loz1, loz2]):
                st.error("Popunite sva polja.")
            elif loz1 != loz2:
                st.error("Lozinke se ne podudaraju.")
            elif len(loz1) < 6:
                st.error("Lozinka mora imati min. 6 znakova.")
            else:
                ok, poruka = db_registruj(email_r, loz1, ime, institucija)
                if ok:
                    st.success("Zahtjev primljen! Bit ćete obaviješteni kada admin odobri pristup.")
                    st.info("Kontakt za ubrzanje odobravanja: semir.mehovic1989@gmail.com")
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
    if st.session_state.get("korisnik_email", "") == ADMIN_EMAIL:
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

# ─── Stranice ────────────────────────────────────────────────────────────────
if "Ljestvica" in stranica:
    prikazi_leaderboard()
    st.stop()

if "Moji rezultati" in stranica:
    prikazi_moje_rezultate()
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
    svi = list(SCENARIJI.items())
    nezavrseni = [(sid, sc) for sid, sc in svi if not db_vec_uradio(email, sid)]
    zavrseni = [(sid, sc) for sid, sc in svi if db_vec_uradio(email, sid)]

    def prikazi_karticu(sc_id, sc, uradjen):
        status_bg = "#dcfce7" if uradjen else "#dbeafe"
        status_boja = "#16a34a" if uradjen else "#0D8A9E"
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
sc = SCENARIJI[odabrani_id]
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
    preostalo = MAX_POTEZA - stanje["broj_poteza"]

    # ── Tajmer: provjeri da li je isteklo 60s od zadnjeg poteza ──
    TAJMER_SEKUNDI = 60
    sad = time.time()
    if "zadnji_potez_vrijeme" not in stanje:
        stanje["zadnji_potez_vrijeme"] = sad

    proteklo = sad - stanje["zadnji_potez_vrijeme"]
    propusteni = int(proteklo // TAJMER_SEKUNDI)

    if propusteni > 0 and preostalo > 0:
        stanje["broj_poteza"] += min(propusteni, preostalo)
        stanje["zadnji_potez_vrijeme"] = sad
        preostalo = MAX_POTEZA - stanje["broj_poteza"]
        if preostalo <= 0:
            st.warning("Vrijeme je isteklo za sve pokušaje. Savjetovanje se završava.")
            pokreni_evaluaciju(stanje, sc, odabrani_id)
            st.rerun()
        else:
            st.warning(f"Izgubili ste {min(propusteni, preostalo + propusteni)} pokušaj/a jer niste odgovorili na vrijeme.")
            st.rerun()

    preostalo_s = int(TAJMER_SEKUNDI - (proteklo % TAJMER_SEKUNDI))

    # Prikaz preostalih pokušaja + tajmer
    t_col1, t_col2 = st.columns([1, 1])
    with t_col1:
        st.caption(f"Preostalo unosa: **{preostalo} / {MAX_POTEZA}**")
    with t_col2:
        st.caption(f"Vrijeme za odgovor: **{preostalo_s}s**")

    # JavaScript countdown tajmer
    st.markdown(f"""
    <div id="timerBar" style="background:#e2e8f0;border-radius:8px;height:6px;margin:-8px 0 16px;overflow:hidden">
        <div id="timerFill" style="background:linear-gradient(90deg,#1CB5C5,#0D8A9E);height:100%;
             width:{(preostalo_s/TAJMER_SEKUNDI)*100}%;border-radius:8px;transition:width 1s linear"></div>
    </div>
    <script>
    (function() {{
        var remaining = {preostalo_s};
        var total = {TAJMER_SEKUNDI};
        var fill = window.parent.document.getElementById('timerFill');
        if (!fill) return;
        var interval = setInterval(function() {{
            remaining--;
            if (remaining <= 0) {{
                clearInterval(interval);
                // Streamlit rerun — simuliraj klik na hidden element
                window.parent.location.reload();
                return;
            }}
            var pct = (remaining / total) * 100;
            fill.style.width = pct + '%';
            if (remaining <= 10) {{
                fill.style.background = 'linear-gradient(90deg, #ef4444, #dc2626)';
            }} else if (remaining <= 20) {{
                fill.style.background = 'linear-gradient(90deg, #f59e0b, #d97706)';
            }}
        }}, 1000);
    }})();
    </script>
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
