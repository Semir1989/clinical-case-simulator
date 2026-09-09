"""Ekran \"Moji rezultati\": nadimak, historija pokusaja, brisanje naloga."""
import time
from collections import defaultdict

import streamlit as st

from baza import (ISPIT, VJEZBA, db_login, db_moji_rezultati, db_obrisi_sve_podatke,
                  db_posalji_zalbu, db_postavi_nadimak, je_admin, nadimak_za)
from scenariji import SCENARIJI

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


def prikazi_krivulju_vjezbi(vjezbe):
    """Krivulja napretka kroz vježbe, po scenariju.

    Ispit pokazuje gdje ste danas; vježbe pokazuju krećete li se. Zato se
    crtaju odvojeno i tek kad ima bar dvije vježbe istog scenarija — jedna
    tačka nije krivulja.
    """
    if not vjezbe:
        return

    po_scenariju = defaultdict(list)
    for v in sorted(vjezbe, key=lambda x: x.get("completed_at") or ""):
        po_scenariju[v["scenario_id"]].append(float(v["score"]))

    crtljivi = {sid: ocjene for sid, ocjene in po_scenariju.items() if len(ocjene) >= 2}
    if not crtljivi:
        st.caption(f"Odvježbali ste {len(vjezbe)} put(a). Krivulja napretka se crta "
                   "kad isti scenarij odvježbate bar dvaput.")
        return

    with st.expander(f"Napredak kroz vježbe ({len(vjezbe)} vježbi)", expanded=False):
        for sid, ocjene in crtljivi.items():
            naziv = SCENARIJI.get(sid, {}).get("naziv", sid)
            promjena = ocjene[-1] - ocjene[0]
            znak = "+" if promjena >= 0 else ""
            st.markdown(f"**{naziv}** — {len(ocjene)} vježbi, "
                        f"{ocjene[0]:.1f} → {ocjene[-1]:.1f} ({znak}{promjena:.1f})")
            st.line_chart(ocjene, height=140)


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

    # Ispiti i vjezbe se broje odvojeno — vjezba ne ulazi u rezultat.
    ispiti = [r for r in rezultati if (r.get("mode") or ISPIT) == ISPIT]
    vjezbe = [r for r in rezultati if (r.get("mode") or ISPIT) == VJEZBA]

    ukupno = sum(float(r["score"]) for r in ispiti)
    prosjek = ukupno / len(ispiti) if ispiti else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Ukupno bodova", f"{ukupno:.1f}")
    col2.metric("Položenih ispita", len(ispiti))
    col3.metric("Prosječna ocjena", f"{prosjek:.1f}")

    prikazi_krivulju_vjezbi(vjezbe)

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
        # Vjezba se mora razlikovati od ispita na prvi pogled — inace historija
        # izgleda kao da je scenarij igran vise puta ispitno.
        znacka = ("" if (r.get("mode") or ISPIT) == ISPIT else
                  '<span style="background:#e0e7ff;color:#4338ca;font-size:11px;font-weight:700;'
                  'padding:2px 8px;border-radius:6px;margin-left:8px">VJEŽBA</span>')
        st.markdown(f"""
        <div style="background:white;border-radius:14px;padding:16px 20px;margin-bottom:10px;
             box-shadow:0 1px 4px rgba(0,0,0,0.07);display:flex;align-items:center;gap:16px">
            <div style="flex:1">
                <div style="font-weight:600;color:#1e293b">{naziv}{znacka}</div>
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
