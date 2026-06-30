"""
Clinical Case Simulator — Edu Pharma Community
Supabase backend · Leaderboard · Cross-device persistence · Beautiful UI
"""

import json
import os
import hashlib
from datetime import datetime, timedelta, timezone
from collections import defaultdict

import streamlit as st
from anthropic import Anthropic
from dotenv import load_dotenv

# ─── Page config (mora biti prva Streamlit komanda) ───────────────────────────
st.set_page_config(
    page_title="Clinical Case Simulator · Edu Pharma",
    page_icon="💊",
    layout="centered",
    initial_sidebar_state="expanded",
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
# Tirkizna paleta · Mobile-first · Forsiran light mode
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Globalno ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif !important;
    color-scheme: light !important;
}
#MainMenu, footer { visibility: hidden; }

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

/* ── Dugmad ── */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    padding: 10px 20px !important;
    transition: all 0.2s ease !important;
    color: white !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 18px rgba(28,181,197,0.35) !important;
}
[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #1CB5C5, #0D8A9E) !important;
    border: none !important;
    color: white !important;
}
[data-testid="baseButton-secondary"] {
    background: white !important;
    border: 2px solid #1CB5C5 !important;
    color: #0D8A9E !important;
}

/* ── Input polja — bijela pozadina, vidljiv tekst ── */
.stTextInput > div > div > input,
.stTextInput > div > div > input::placeholder {
    background-color: #FFFFFF !important;
    color: #1A2E3B !important;
    border-radius: 12px !important;
    border: 1.5px solid #B2DDE4 !important;
    font-size: 15px !important;
    padding: 11px 14px !important;
}
.stTextInput > div > div > input::placeholder { color: #8BAAB2 !important; }
.stTextInput > div > div > input:focus {
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

/* ── Mobile optimizacija ── */
@media (max-width: 768px) {
    [data-testid="block-container"] { padding: 12px !important; }
    .stButton > button { font-size: 14px !important; padding: 10px 16px !important; }
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

        r = db.table("attempts").select("user_email, score").gte("completed_at", od).execute()
        if not r.data:
            return []

        skupovi = defaultdict(list)
        for row in r.data:
            skupovi[row["user_email"]].append(float(row["score"]))

        emailovi = list(skupovi.keys())
        im = db.table("users").select("email, full_name, institution").in_("email", emailovi).execute()
        info = {u["email"]: u for u in im.data}

        lista = []
        for email, scores in skupovi.items():
            k = info.get(email, {})
            lista.append({
                "email": email,
                "ime": k.get("full_name", email),
                "institucija": k.get("institution", ""),
                "ukupno": round(sum(scores), 2),
                "slucajeva": len(scores),
                "prosjek": round(sum(scores) / len(scores), 2),
            })

        lista.sort(key=lambda x: x["ukupno"], reverse=True)
        return lista
    except Exception:
        return []


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
    },
}

RUBRIKA = """
Ocijeni po ovim kategorijama (svaka 0-10):

ANAMNEZA (tezina 0.4): pitao trajanje tegobe(2), sta koristi i koliko dugo(2), trudnocu/stanja(2), alergije(2), prepoznao zastavice(2)
KAZNA: bez pitanja o trudnoci max 4/10; bez pitanja sta koristi max 6/10

KOMUNIKACIJA (tezina 0.3): jezik laika(2), empatija bez osudjivanja(2), provjerio razumijevanje(2), strukturisan razgovor(2), jasna poruka(2)

SIGURNOST (tezina 0.3): odbio Clobetasol bez recepta(3), savjetovao prekid oba preparata(3), nije predlozio zamjensku terapiju(2), uputio ljekaru(2)
KAZNA: dao kortikosteroid trudnici = 0/10 za Sigurnost
"""

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
{RUBRIKA}
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
    emoji = "🟢" if ukupno >= 7 else ("🟡" if ukupno >= 5 else "🔴")

    st.markdown(f"""
    <div style="background:{bg};border-radius:20px;padding:28px;text-align:center;
         margin:20px 0;border:2px solid {boja}22">
        <div style="font-size:52px;margin-bottom:4px">{emoji}</div>
        <div style="font-size:48px;font-weight:800;color:{boja};line-height:1">
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
        st.markdown("#### ✅ Šta ste uradili dobro")
        for p in r["pohvale"]:
            st.success(p)

    if r.get("propustena_pitanja"):
        st.markdown("#### ❓ Propuštena pitanja")
        for p in r["propustena_pitanja"]:
            st.warning(p)

    if r.get("smjernice"):
        st.markdown("#### 💡 Smjernice za poboljšanje")
        for s in r["smjernice"]:
            st.info(s)


def prikazi_leaderboard():
    st.markdown("## 🏆 Ljestvica rezultata")

    medalje = ["🥇", "🥈", "🥉"]
    periodi = {"Sedmično": "sedmicno", "Mjesečno": "mjesecno", "Godišnje": "godisnje", "Ukupno": "ukupno"}
    tabovi = st.tabs(list(periodi.keys()))

    for tab, (naziv, period) in zip(tabovi, periodi.items()):
        with tab:
            podaci = db_leaderboard(period)
            if not podaci:
                st.markdown("""
                <div style="text-align:center;padding:40px;color:#94a3b8">
                    <div style="font-size:40px">🏅</div>
                    <div style="margin-top:8px">Još nema rezultata za ovaj period.</div>
                </div>""", unsafe_allow_html=True)
                continue

            ja = st.session_state.get("korisnik_email", "")
            for i, red in enumerate(podaci[:20]):
                medalja = medalje[i] if i < 3 else f"<span style='font-weight:700;color:#94a3b8'>{i+1}.</span>"
                je_ja = red["email"] == ja
                bg = "linear-gradient(135deg,#dbeafe,#eff6ff)" if je_ja else "white"
                border = "border:2px solid #1a3a8f;" if je_ja else ""
                st.markdown(f"""
                <div style="background:{bg};{border}border-radius:14px;padding:14px 20px;
                     margin-bottom:8px;box-shadow:0 1px 4px rgba(0,0,0,0.07);
                     display:flex;align-items:center;gap:12px">
                    <div style="font-size:24px;min-width:36px;text-align:center">{medalja}</div>
                    <div style="flex:1;min-width:0">
                        <div style="font-weight:700;color:#1e293b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">
                            {red['ime']}{' 👤' if je_ja else ''}
                        </div>
                        <div style="font-size:13px;color:#64748b">{red['institucija']} · {red['slucajeva']} slučaj/eva</div>
                    </div>
                    <div style="text-align:right;flex-shrink:0">
                        <div style="font-size:26px;font-weight:800;color:#1a3a8f">{red['ukupno']:.1f}</div>
                        <div style="font-size:12px;color:#94a3b8">bodova</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)


def prikazi_moje_rezultate():
    st.markdown("## 📊 Moji rezultati")
    email = st.session_state.get("korisnik_email", "")
    rezultati = db_moji_rezultati(email)

    if not rezultati:
        st.markdown("""
        <div style="text-align:center;padding:48px;color:#94a3b8">
            <div style="font-size:48px">📋</div>
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

        tab_l, tab_r = st.tabs(["🔑  Prijava", "📝  Registracija"])

        with tab_l:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            with st.form("login_form"):
                email = st.text_input("Email adresa", placeholder="vas@email.com")
                lozinka = st.text_input("Lozinka", type="password", placeholder="••••••••")
                submit = st.form_submit_button("Prijavi se →", type="primary", use_container_width=True)

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

        with tab_r:
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            with st.form("reg_form"):
                ime = st.text_input("Ime i prezime", placeholder="Amira Hodžić")
                email_r = st.text_input("Email", placeholder="amira@apoteka.ba", key="er")
                institucija = st.text_input("Apoteka / Institucija", placeholder="Apoteka Centar, Sarajevo")
                loz1 = st.text_input("Lozinka", type="password", key="l1")
                loz2 = st.text_input("Ponovi lozinku", type="password", key="l2")
                submit_r = st.form_submit_button("Pošalji zahtjev", use_container_width=True)

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
                        st.info("Kontakt za ubrzanje odobravanja: semir.mehovic1989@gmail.com", icon="📧")
                    else:
                        st.error(poruka)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        st.warning("Alat je isključivo za **edukaciju i vježbu farmaceutskog savjetovanja**. Nije namijenjen kliničkom odlučivanju.", icon="⚠️")


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
    stranica = st.radio(
        "Navigacija",
        ["💊  Scenariji", "🏆  Ljestvica", "📊  Moji rezultati"],
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

# ─── SCENARIJI ───────────────────────────────────────────────────────────────
st.warning("Alat je isključivo za **edukaciju i vježbu**. Nije podrška kliničkom odlučivanju.", icon="⚠️")
st.markdown("## 💊 Klinički slučajevi")

email = st.session_state.get("korisnik_email", "")

# Kartice scenarija
for sc_id, sc in SCENARIJI.items():
    uradjen = db_vec_uradio(email, sc_id)
    if uradjen:
        st.markdown(f"""
        <div style="background:white;border-radius:14px;padding:18px 22px;margin-bottom:10px;
             box-shadow:0 1px 4px rgba(0,0,0,0.07);display:flex;align-items:center;gap:16px">
            <div style="flex:1">
                <div style="font-weight:700;color:#1e293b">{sc['naziv']}</div>
                <div style="font-size:13px;color:#64748b;margin-top:3px">{sc['ime']}, {sc['godine']} god.</div>
            </div>
            <span style="background:#dcfce7;color:#16a34a;padding:5px 14px;border-radius:20px;
                  font-size:13px;font-weight:600;flex-shrink:0">✅ Završeno</span>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:white;border-radius:14px;padding:18px 22px;margin-bottom:10px;
             box-shadow:0 1px 4px rgba(0,0,0,0.07);display:flex;align-items:center;gap:16px;
             border-left:4px solid #1a3a8f">
            <div style="flex:1">
                <div style="font-weight:700;color:#1e293b">{sc['naziv']}</div>
                <div style="font-size:13px;color:#64748b;margin-top:3px">{sc['ime']}, {sc['godine']} god.</div>
            </div>
            <span style="background:#dbeafe;color:#1a3a8f;padding:5px 14px;border-radius:20px;
                  font-size:13px;font-weight:600;flex-shrink:0">▶ Dostupno</span>
        </div>""", unsafe_allow_html=True)

st.divider()

odabrani_id = st.selectbox(
    "Odaberi scenarij za rad:",
    list(SCENARIJI.keys()),
    format_func=lambda k: SCENARIJI[k]["naziv"],
)
sc = SCENARIJI[odabrani_id]
vec_uradjen = db_vec_uradio(email, odabrani_id)

with st.expander("ℹ️ Podaci o pacijentu", expanded=not vec_uradjen):
    col1, col2 = st.columns(2)
    col1.markdown(f"**Pacijent:** {sc['ime']}, {sc['godine']} god.")
    col2.markdown(f"**Terapija:** {sc['terapija']}")
    st.markdown(f"**Razlog posjete:** {sc['tegoba']}")

st.divider()

# ─── Session state ────────────────────────────────────────────────────────────
kljuc = f"chat_{odabrani_id}"
if kljuc not in st.session_state:
    st.session_state[kljuc] = {
        "poruke_api": [], "poruke_prikaz": [],
        "ocjena": None, "zavrseno": False, "broj_poteza": 0,
    }
stanje = st.session_state[kljuc]

# ─── Završeni scenarij ────────────────────────────────────────────────────────
if vec_uradjen:
    st.info("Ovaj scenarij ste već završili. Rezultati su trajno sačuvani.", icon="📋")

    with st.expander("Transkript razgovora"):
        for p in stanje["poruke_prikaz"]:
            with st.chat_message(p["role"], avatar="🧑‍⚕️" if p["role"] == "user" else "🙍"):
                st.markdown(p["content"])

    ocjena_data = stanje.get("ocjena") or db_dohvati_ocjenu(email, odabrani_id)
    if ocjena_data:
        prikazi_ocjenu(ocjena_data)
    else:
        st.success("Scenarij uspješno završen. Ocjena nije dostupna.")
    st.stop()

# ─── Aktivni razgovor ─────────────────────────────────────────────────────────
for p in stanje["poruke_prikaz"]:
    with st.chat_message(p["role"], avatar="🧑‍⚕️" if p["role"] == "user" else "🙍"):
        st.markdown(p["content"])

if not stanje["poruke_prikaz"]:
    prva = sc["pocetna_poruka"]
    stanje["poruke_prikaz"].append({"role": "assistant", "content": prva})
    stanje["poruke_api"].append({"role": "assistant", "content": prva})
    with st.chat_message("assistant", avatar="🙍"):
        st.markdown(prva)

if not stanje["zavrseno"]:
    preostalo = MAX_POTEZA - stanje["broj_poteza"]
    st.caption(f"Preostalo unosa: **{preostalo} / {MAX_POTEZA}**")

    unos = st.chat_input("Vaš odgovor kao farmaceut...")
    if unos:
        stanje["poruke_prikaz"].append({"role": "user", "content": unos})
        stanje["poruke_api"].append({"role": "user", "content": unos})
        stanje["broj_poteza"] += 1
        with st.chat_message("user", avatar="🧑‍⚕️"):
            st.markdown(unos)

        if stanje["broj_poteza"] < MAX_POTEZA:
            with st.chat_message("assistant", avatar="🙍"):
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
    if st.button("✅ Završi savjetovanje i dobij ocjenu", type="primary", use_container_width=True):
        pokreni_evaluaciju(stanje, sc, odabrani_id)
        st.rerun()

if stanje["zavrseno"] and stanje["ocjena"]:
    prikazi_ocjenu(stanje["ocjena"])
