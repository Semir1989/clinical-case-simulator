"""Ekran za prijavu i registraciju, s besplatnim demo slucajem."""
import streamlit as st

from baza import db_login, db_registruj, nadimak_slobodan
from konfig import KONTAKT_EMAIL

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
