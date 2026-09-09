"""Admin panel: korisnici, zalbe, statistika, CMS scenarija, objave."""
import io
import json
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import streamlit as st

from baza import (db_neodobreni_korisnici, db_objava_aktivna, db_objava_nova,
                  db_objava_obrisi, db_objave_sve, db_obrisi_sve_podatke,
                  db_odbij_korisnika, db_odobri_korisnika, db_otvorene_zalbe,
                  db_pokusaji_korisnika, db_postavi_suspenziju,
                  db_postavi_ulogu, db_resetuj_lozinku, db_rijesi_zalbu,
                  db_scenarij_aktivan, db_scenarij_obrisi, db_scenarij_spremi,
                  db_statistika, db_svi_korisnici, db_svi_pokusaji_export,
                  je_admin, napravi_csv)
from konfig import (zabiljezi_gresku, ADMIN_EMAIL, CIJENA_IZLAZ_USD, CIJENA_ULAZ_USD,
                    DNEVNI_LIMIT_PORUKA, MAX_POTEZA, SENTRY_AKTIVAN)
import rubrika
from motor import generisi_epilog, generisi_scenarij_iz_pdfa, sljedeci_scenarij_id
from posta import posalji_email_masovni, posalji_email_odobrenje
from scenariji import SCENARIJI
from ui.komponente import prikazi_ocjenu

def _kriteriji_zalbe(z):
    """Vadi presude po kriterijima iz sačuvane ocjene; None za stare zapise."""
    sirovo = z.get("result_json")
    if not sirovo:
        return None
    try:
        rez = json.loads(sirovo) if isinstance(sirovo, str) else sirovo
    except (ValueError, TypeError):
        return None
    return rez.get("kriteriji") or None


def _preokreni_kriterije(z, kriteriji):
    """Administrator preokreće sporni kriterij, ocjena se preračuna sama.

    Žalba je do sada tražila da administrator pogodi tri nova broja. Sada vidi
    tačno koji je kriterij sporan, promijeni njegov status, a bodove ponovo
    izračuna ista funkcija koja ih je i dodijelila — pa ispravljena ocjena ne
    može ispasti iz rubrike.
    """
    sc = SCENARIJI.get(z["scenario_id"], {})
    rub = rubrika.za_scenarij(sc, z["scenario_id"]) if sc else None
    if not rub:
        st.caption("Rubrika ovog scenarija više nije dostupna — ocjena se unosi ručno.")
        return (float(z.get("anamneza") or 0), float(z.get("komunikacija") or 0),
                float(z.get("sigurnost") or 0), None)

    izmijenjeni = {}
    with st.expander("Kriteriji — preokrenite sporni", expanded=True):
        for kat in rub["kategorije"]:
            st.markdown(f"**{kat['naziv']}**")
            for kr in kat["kriteriji"]:
                stari = dict(kriteriji.get(kr["id"]) or {"status": "NE"})
                c1, c2 = st.columns([3, 1])
                c1.markdown(
                    f"<div style='font-size:13px;color:#334155;padding-top:6px'>{kr['tekst']}</div>"
                    + (f"<div style='font-size:12px;color:#64748b'>„{stari.get('citat')}“</div>"
                       if stari.get("citat") else ""),
                    unsafe_allow_html=True)
                izbor = c2.selectbox(
                    kr["id"], list(rubrika.STATUSI),
                    index=list(rubrika.STATUSI).index(stari.get("status", "NE"))
                    if stari.get("status") in rubrika.STATUSI else 2,
                    key=f"kr_{z['id']}_{kr['id']}", label_visibility="collapsed")
                stari["status"] = izbor
                izmijenjeni[kr["id"]] = stari

    radnje = [r.get("id") for r in (json.loads(z["result_json"]).get("radnje") or [])
              if isinstance(r, dict)] if isinstance(z.get("result_json"), str) else []
    bodovi = rubrika.izracunaj(rub, izmijenjeni, radnje)
    return (bodovi.get("anamneza", 0), bodovi.get("komunikacija", 0),
            bodovi.get("sigurnost", 0), izmijenjeni)


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

                kriteriji = _kriteriji_zalbe(z)
                novi_kriteriji = None

                if kriteriji:
                    a, kk, s, novi_kriteriji = _preokreni_kriterije(z, kriteriji)
                    st.caption(f"Nova ukupna ocjena: **{a*0.4 + kk*0.3 + s*0.3:.1f}/10** "
                               f"— A {a:g} · K {kk:g} · S {s:g}, preračunato iz kriterija")

                with st.form(f"zalba_{z['id']}"):
                    if not kriteriji:
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
                                                 {"anamneza": a, "komunikacija": kk, "sigurnost": s},
                                                 novi_kriteriji)
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
            # Statistika mjeri ispite. Vjezbe se broje odvojeno — inace bi
            # prosjek po scenariju pao samim tim sto neko puno vjezba.
            svi_pokusaji = podaci["pokusaji"]
            pokusaji = [p for p in svi_pokusaji if (p.get("mode") or "ispit") == "ispit"]
            broj_vjezbi = len(svi_pokusaji) - len(pokusaji)
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
            c4.metric("Ispita ukupno", len(pokusaji),
                      help=f"Uz to i {broj_vjezbi} vježbi, koje se ne broje u statistiku.")

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
                # Epilog i uzoran razgovor se prave jednom po scenariju i
                # spremaju uz njega — polaznika zato ne kostaju nista.
                ima_epilog = bool(s.get("epilog") and s.get("uzoran_razgovor"))
                oznaka = "Epilog: napravljen" if ima_epilog else "Epilog: nedostaje"
                ce1, ce2 = st.columns([2, 1])
                ce1.caption(oznaka)
                if ce2.button("Generiši epilog" if not ima_epilog else "Napravi ponovo",
                              key=f"sc_epi_{sid}", use_container_width=True):
                    with st.spinner("Piše epilog i uzoran razgovor..."):
                        epilog, uzoran = generisi_epilog({**s, "id": sid})
                    if epilog and uzoran:
                        if db_scenarij_spremi(sid, {"epilog": epilog,
                                                    "uzoran_razgovor": uzoran}):
                            st.session_state["admin_flash"] = (
                                f"Epilog i uzoran razgovor spremljeni za '{s.get('naziv', sid)}'.")
                            st.rerun()
                    else:
                        st.error("Model nije vratio ispravan tekst. Pokušajte ponovo.")

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
                        "persona": s.get("persona") or {}, "cinjenice": s.get("cinjenice"),
                        "otpor": s.get("otpor"),
                        "vidljivi_znakovi": s.get("vidljivi_znakovi", ""),
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
            skriveni_in = st.text_area(
                "Skriveni detalji — stari tekstualni oblik",
                value=izvor.get("skriveni_detalji", ""), height=120,
                help="Koristi se samo ako lista činjenica ispod nije popunjena.")

            st.markdown("**Persona** — mijenja kako pacijent govori, ne šta zna.")
            _per = izvor.get("persona") or {}
            p1, p2, p3 = st.columns(3)
            pricljivost_in = p1.selectbox(
                "Pričljivost", [1, 2, 3, 4, 5],
                index=[1, 2, 3, 4, 5].index(int(_per.get("pricljivost") or 3)))
            _obr = ["osnovno", "srednje", "visoko"]
            obrazovanje_in = p2.selectbox(
                "Obrazovanje", _obr,
                index=_obr.index(_per.get("obrazovanje")) if _per.get("obrazovanje") in _obr else 1)
            _rasp = ["uplasen", "nervozan", "umoran", "vedar", "ljut", "neutralan"]
            raspolozenje_in = p3.selectbox(
                "Raspoloženje", _rasp,
                index=_rasp.index(_per.get("raspolozenje")) if _per.get("raspolozenje") in _rasp else 5)
            p4, p5 = st.columns(2)
            zanimanje_in = p4.text_input("Zanimanje", value=_per.get("zanimanje", ""))
            porodica_in = p5.text_input("Porodica i okolnosti", value=_per.get("porodica", ""))
            odnos_in = st.text_input("Odnos prema lijekovima", value=_per.get("odnos_prema_lijekovima", ""),
                                     placeholder="npr. vjeruje komšinici više nego ljekaru")
            zurba_in = st.checkbox("Žuri mu se", value=bool(_per.get("zurba")))

            cinjenice_in = st.text_area(
                "Činjenice (JSON lista)", height=220,
                value=json.dumps(izvor.get("cinjenice") or [], ensure_ascii=False, indent=2),
                help='Svaka: {"id", "cinjenica", "okidac", "osjetljivo"}. Okidač je pitanje '
                     'koje činjenicu otključava. Osjetljive pacijent daje tek na drugo pitanje '
                     'ili nakon empatije. Prazna lista = koristi se stari tekst iznad.')

            znakovi_in = st.text_area(
                "Vidljivi znakovi", height=80,
                value=izvor.get("vidljivi_znakovi", ""),
                help="Šta farmaceut može primijetiti bez pitanja. Pacijent ih ubacuje kao "
                     "didaskalije u uglastim zagradama.")
            otpor_in = st.text_area(
                "Prigovori (JSON lista)", height=220,
                value=json.dumps(izvor.get("otpor") or [], ensure_ascii=False, indent=2),
                help='Svaki: {"id", "replika", "redoslijed", "uslov_popustanja", '
                     '"prag_povjerenja", "kriterij"}. Prigovor s "fatalno_ako_izda": true i '
                     '"uslov_popustanja": null se ne popušta nikad.')
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
            cinjenice_val, otpor_val, greska_json = None, None, ""
            try:
                cinjenice_val = json.loads(cinjenice_in) if cinjenice_in.strip() else []
                if not isinstance(cinjenice_val, list):
                    greska_json = "Činjenice moraju biti JSON lista."
                else:
                    for c in cinjenice_val:
                        if not isinstance(c, dict) or not c.get("cinjenica") or not c.get("okidac"):
                            greska_json = "Svaka činjenica treba polja 'cinjenica' i 'okidac'."
                            break
            except json.JSONDecodeError as e:
                greska_json = f"Činjenice nisu validan JSON: {e}"
            try:
                otpor_val = json.loads(otpor_in) if otpor_in.strip() else []
                if not isinstance(otpor_val, list):
                    greska_json = greska_json or "Prigovori moraju biti JSON lista."
            except json.JSONDecodeError as e:
                greska_json = greska_json or f"Prigovori nisu validan JSON: {e}"

            if greska_json:
                st.error(greska_json)
            elif not sid_in.strip() or not naziv_in.strip() or not pocetna_in.strip():
                st.error("Obavezno: ID, naziv i početna poruka.")
            elif not cinjenice_val and not skriveni_in.strip():
                st.error("Popunite ili listu činjenica ili stare skrivene detalje.")
            else:
                ok = db_scenarij_spremi(sid_in, {
                    "persona": {
                        "pricljivost": int(pricljivost_in),
                        "obrazovanje": obrazovanje_in,
                        "raspolozenje": raspolozenje_in,
                        "zurba": bool(zurba_in),
                        "zanimanje": zanimanje_in.strip(),
                        "porodica": porodica_in.strip(),
                        "odnos_prema_lijekovima": odnos_in.strip(),
                    },
                    "cinjenice": cinjenice_val or None,
                    "otpor": otpor_val or None,
                    "vidljivi_znakovi": znakovi_in.strip(),
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
                skriveni_g = st.text_area("Skriveni detalji — stari tekstualni oblik",
                                          value=gen.get("skriveni_detalji", ""), height=120)
                cinjenice_g = st.text_area(
                    "Činjenice (JSON lista)", height=260,
                    value=json.dumps(gen.get("cinjenice") or [], ensure_ascii=False, indent=2),
                    help="Provjerite okidače i oznake osjetljivosti prije spremanja — od njih "
                         "zavisi da li se slučaj uopšte može riješiti.")
                persona_g = st.text_area(
                    "Persona (JSON)", height=140,
                    value=json.dumps(gen.get("persona") or {}, ensure_ascii=False, indent=2))
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
                cinjenice_gv, persona_gv, greska_g = None, {}, ""
                try:
                    cinjenice_gv = json.loads(cinjenice_g) if cinjenice_g.strip() else []
                    persona_gv = json.loads(persona_g) if persona_g.strip() else {}
                    if not isinstance(cinjenice_gv, list) or not isinstance(persona_gv, dict):
                        greska_g = "Činjenice moraju biti lista, a persona objekat."
                except json.JSONDecodeError as e:
                    greska_g = f"JSON nije validan: {e}"

                if greska_g:
                    st.error(greska_g)
                elif not sid_g.strip() or not naziv_g.strip() or not pocetna_g.strip() \
                        or not (cinjenice_gv or skriveni_g.strip()):
                    st.error("Obavezno: ID, naziv, početna poruka i činjenice "
                             "(ili stari skriveni detalji).")
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
                        "cinjenice": cinjenice_gv or None,
                        "persona": persona_gv,
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
