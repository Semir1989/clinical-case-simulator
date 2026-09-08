"""Ljestvica rezultata. Prikazuje iskljucivo nadimke."""
import streamlit as st

from baza import db_leaderboard

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
