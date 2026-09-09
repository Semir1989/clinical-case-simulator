"""
Clinical Case Simulator — Edu Pharma Community

Ulazna tacka: podesava stranicu, ucitava stil i vodi navigaciju. Sve ostalo
zivi u modulima — konfig, baza, posta, promptovi, motor, ocjena, scenariji, ui.
"""
import streamlit as st

# set_page_config mora biti prva Streamlit komanda, pa ide prije ostalih uvoza.
st.set_page_config(
    page_title="Clinical Case Simulator · Edu Pharma",
    layout="centered",
    initial_sidebar_state="expanded",
)

import time  # noqa: E402

import streamlit.components.v1 as components  # noqa: E402

import stil  # noqa: E402
from baza import (ISPIT, VJEZBA, _ucitaj_objave, db_broj_vjezbi,  # noqa: E402
                  db_dohvati_ocjenu, db_dohvati_transkript, db_log_upotrebu,
                  db_obrisi_napredak,
                  db_poruka_danas, db_spremi_napredak, db_ucitaj_napredak,
                  db_vec_uradio, db_zavrseni_scenariji, je_admin)
from demo import prikazi_demo  # noqa: E402
from konfig import (DNEVNI_LIMIT_PORUKA, MAX_POTEZA,  # noqa: E402
                    VJEZBA_OMOGUCENA)
from motor import (pokreni_evaluaciju, pozovi_pacijenta_stream,  # noqa: E402
                   zatvori_razgovor)
from scenariji import SCENARIJI  # noqa: E402
from ui.admin import prikazi_admin  # noqa: E402
from ui.komponente import (PODRUCJA, TEZINE, filter_scenarija,  # noqa: E402
                           je_novo, prikazi_epilog, prikazi_ocjenu,
                           prikazi_pravila, prikazi_repliku)
from ui.ljestvica import prikazi_leaderboard  # noqa: E402
from ui.prijava import prikazi_login  # noqa: E402
from ui.rezultati import prikazi_gdpr_brisanje, prikazi_moje_rezultate  # noqa: E402

stil.primijeni()

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
mod = st.session_state.get("odabrani_mod", ISPIT)


def otvori_scenarij(sc_id, novi_mod):
    st.session_state["odabrani_scenarij"] = sc_id
    st.session_state["odabrani_mod"] = novi_mod
    st.rerun()


# ─── Ako nema odabranog scenarija → prikaži kartice ──────────────────────────
if odabrani_id is None:
    st.markdown("## Klinički slučajevi")
    if VJEZBA_OMOGUCENA:
        st.caption("**Ispit** se igra jednom i ide na ljestvicu. **Vježba** je neograničena, "
                   "bez tajmera, i ne ulazi u rezultat.")
    else:
        st.caption("Svaki scenarij se igra **jednom**. Vježba je privremeno isključena.")

    # Sortiraj: nezavršeni prvi, završeni ispod
    svi = [(sid, s) for sid, s in SCENARIJI.items() if s.get("aktivan", True)]
    svi = filter_scenarija(svi)
    zavrseni_ids = db_zavrseni_scenariji(email)
    vjezbi = db_broj_vjezbi(email)
    nezavrseni = [(sid, sc) for sid, sc in svi if sid not in zavrseni_ids]
    zavrseni = [(sid, sc) for sid, sc in svi if sid in zavrseni_ids]

    def prikazi_karticu(sc_id, sc, uradjen):
        status_bg = "#dcfce7" if uradjen else "#dbeafe"
        status_boja = "#16a34a" if uradjen else "#2C6FBE"
        status_tekst = "Završeno" if uradjen else "Dostupno"
        border_top = f"border-top: 4px solid {status_boja};"

        # Oznake podrucja i tezine stoje uz status, da se lista moze pregledati
        # okom prije nego se posegne za filterom.
        znacke = ""
        if sc.get("podrucje"):
            znacke += (f'<span style="background:#f1f5f9;color:#475569;padding:4px 12px;'
                       f'border-radius:20px;font-size:12px;font-weight:600;margin-left:6px">'
                       f'{PODRUCJA.get(sc["podrucje"], sc["podrucje"])}</span>')
        if sc.get("tezina"):
            znacke += (f'<span style="background:#fef3c7;color:#92400e;padding:4px 12px;'
                       f'border-radius:20px;font-size:12px;font-weight:600;margin-left:6px">'
                       f'{TEZINE.get(sc["tezina"], sc["tezina"])}</span>')
        if je_novo(sc):
            znacke += ('<span style="background:#dcfce7;color:#166534;padding:4px 12px;'
                       'border-radius:20px;font-size:12px;font-weight:700;margin-left:6px">'
                       'NOVO OVE SEDMICE</span>')

        st.markdown(f"""
        <div style="background:white;border-radius:16px;padding:24px 28px;margin-bottom:16px;
             box-shadow:0 2px 10px rgba(0,0,0,0.08);{border_top}">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
                <span style="background:{status_bg};color:{status_boja};padding:4px 14px;border-radius:20px;
                      font-size:12px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase">{status_tekst}</span>
                <div>{znacke}</div>
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

        # Ispit se igra jednom; vjezba koliko god puta. Zato dva dugmeta, a ne
        # jedno — polaznik bira prije nego potrosi jedini ispitni pokusaj.
        c1, c2 = st.columns(2)
        if uradjen:
            if c1.button("Pogledaj rezultat", key=f"rez_{sc_id}", use_container_width=True):
                otvori_scenarij(sc_id, ISPIT)
        else:
            if c1.button("Ispit", key=f"ispit_{sc_id}", type="primary", use_container_width=True):
                otvori_scenarij(sc_id, ISPIT)

        oznaka_vjezbe = "Vježba"
        if vjezbi.get(sc_id):
            oznaka_vjezbe += f" ({vjezbi[sc_id]})"
        if c2.button(oznaka_vjezbe, key=f"vjezba_{sc_id}", use_container_width=True,
                     disabled=not VJEZBA_OMOGUCENA,
                     help=None if VJEZBA_OMOGUCENA else "Vježba je privremeno isključena."):
            otvori_scenarij(sc_id, VJEZBA)

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
if mod == VJEZBA and not VJEZBA_OMOGUCENA:
    # Druga brava: dugme je onemoguceno, ali stanje sesije moze prezivjeti
    # gasenje prekidaca, pa se rezim provjerava i ovdje.
    st.session_state["odabrani_mod"] = ISPIT
    st.rerun()

# Ispit se gleda kao zavrsen; vjezba se uvijek moze ponoviti.
vec_uradjen = mod == ISPIT and db_vec_uradio(email, odabrani_id)

if st.button("Nazad na listu scenarija", type="secondary"):
    st.session_state["odabrani_scenarij"] = None
    st.rerun()

st.markdown(f"## {sc['naziv']}")
if mod == VJEZBA:
    st.caption("**Vježba** — bez tajmera, ne ide na ljestvicu, možete je ponoviti koliko želite.")

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

def zavrsi_i_ocijeni(stanje, sc, sc_id):
    """Prije ocjene traži završnu repliku pacijenta, da se vidi ishod razgovora.

    Ranije je razgovor jednostavno prestajao i polaznik nikad nije saznao je li
    pacijent poslušao savjet. Jedan dodatni poziv, oko 0,003 USD.
    """
    if stanje["poruke_prikaz"] and not stanje.get("zatvoren"):
        with st.spinner("Pacijent se oprašta..."):
            zavrsna, novo_stanje, sirovi = zatvori_razgovor(
                stanje["poruke_api"], sc, stanje.get("zadnje_stanje"))
        stanje["zatvoren"] = True
        if zavrsna:
            stanje["poruke_prikaz"].append({"role": "assistant", "content": zavrsna})
            stanje["poruke_api"].append({"role": "assistant", "content": sirovi or zavrsna})
            if novo_stanje:
                stanje["stanja"].append(novo_stanje)
                stanje["zadnje_stanje"] = novo_stanje
    pokreni_evaluaciju(stanje, sc, sc_id, mod)
    # Ocjena je upisana — sacuvan razgovor vise nema svrhu.
    db_obrisi_napredak(email, sc_id, mod)


def zapamti_potez(stanje):
    """Upisuje razgovor poslije svakog poteza, da ga osvježavanje ne obriše."""
    db_spremi_napredak(email, odabrani_id, stanje, mod)


# ─── Session state ────────────────────────────────────────────────────────────
# Kljuc nosi i rezim: ista osoba moze imati zapocetu vjezbu i zapocet ispit
# istog scenarija, i to su dva odvojena razgovora.
kljuc = f"chat_{mod}_{odabrani_id}"
if kljuc not in st.session_state:
    st.session_state[kljuc] = {
        "poruke_api": [], "poruke_prikaz": [],
        "ocjena": None, "zavrseno": False, "broj_poteza": 0,
        "stanja": [], "zadnje_stanje": None,
        "zapoceto": False, "vraceno": False,
        "zadnji_potez_vrijeme": time.time(),
    }
    # Prekinut razgovor se vraca iz baze — do sada je nestajao na osvjezavanje
    # stranice, a tajmer je nastavljao trositi poteze.
    if not vec_uradjen:
        sacuvano = db_ucitaj_napredak(email, odabrani_id, mod)
        if sacuvano and sacuvano.get("poruke_prikaz"):
            st.session_state[kljuc].update({
                k: v for k, v in sacuvano.items() if k != "zadnji_potez_vrijeme"})
            st.session_state[kljuc]["zapoceto"] = True
            st.session_state[kljuc]["vraceno"] = True
            # Tajmer krece iznova: vrijeme provedeno van aplikacije se ne racuna.
            st.session_state[kljuc]["zadnji_potez_vrijeme"] = time.time()
        else:
            db_log_upotrebu("start", odabrani_id)
stanje = st.session_state[kljuc]

# ─── Završeni scenarij ────────────────────────────────────────────────────────
if vec_uradjen:
    st.info("Ovaj scenarij ste već završili. Rezultati su trajno sačuvani.")

    with st.expander("Transkript razgovora"):
        if stanje["poruke_prikaz"]:
            for p in stanje["poruke_prikaz"]:
                with st.chat_message(p["role"]):
                    prikazi_repliku(p["content"], p["role"])
        else:
            # Poslije odjave sesija je prazna — transkript se cita iz baze.
            sacuvan = db_dohvati_transkript(email, odabrani_id)
            if sacuvan:
                st.text(sacuvan)
            else:
                st.caption("Transkript nije sačuvan za ovaj pokušaj.")

    ocjena_data = stanje.get("ocjena") or db_dohvati_ocjenu(email, odabrani_id)
    if ocjena_data:
        prikazi_ocjenu(ocjena_data, stanje.get("stanja"))
    else:
        st.success("Scenarij uspješno završen. Ocjena nije dostupna.")
    prikazi_epilog(sc)
    st.stop()

# ─── Pravila prije početka ───────────────────────────────────────────────────
# Tajmer je ranije kretao onog trenutka kad se stranica otvori, pa je polaznik
# gubio poteze dok je jos citao ko mu je pacijent. Sada krece tek na "Pocni".
if not stanje["zapoceto"]:
    if prikazi_pravila(mod == ISPIT, MAX_POTEZA):
        stanje["zapoceto"] = True
        stanje["zadnji_potez_vrijeme"] = time.time()
        prva = sc["pocetna_poruka"]
        stanje["poruke_prikaz"].append({"role": "assistant", "content": prva})
        stanje["poruke_api"].append({"role": "assistant", "content": prva})
        zapamti_potez(stanje)
        st.rerun()
    st.stop()

# ─── Aktivni razgovor ─────────────────────────────────────────────────────────
if stanje.pop("vraceno", False):
    st.info("Nastavljate razgovor koji ste ranije započeli. Odbrojavanje kreće iznova.")

for p in stanje["poruke_prikaz"]:
    with st.chat_message(p["role"]):
        prikazi_repliku(p["content"], p["role"])

if not stanje["zavrseno"]:
    # ── Dnevni limit AI poruka (kontrola troškova) ──
    if db_poruka_danas(email) >= DNEVNI_LIMIT_PORUKA:
        if stanje["broj_poteza"] > 0:
            st.warning("Dostigli ste dnevni limit poruka — savjetovanje se završava i ocjenjuje.")
            pokreni_evaluaciju(stanje, sc, odabrani_id, mod)
            db_obrisi_napredak(email, odabrani_id, mod)
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
    # Vjezba nema tajmer: svrha joj je da se moze stati i razmisliti.
    TAJMER_SEKUNDI = 120
    tajmer_radi = mod == ISPIT
    proteklo = 0

    if tajmer_radi:
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
            zapamti_potez(stanje)
            if preostalo <= 0:
                st.warning("Vrijeme je isteklo za sve pokušaje. Savjetovanje se završava i ocjenjuje.")
                zavrsi_i_ocijeni(stanje, sc, odabrani_id)
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
    if tajmer_radi:
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
                # Replika stize rijec po rijec; blok stanja ostaje skriven jer
                # se prikazuje samo tekst do prvog "<".
                mjesto = st.empty()
                mjesto.markdown("_piše..._")

                def _ispisi(dio):
                    mjesto.markdown((dio or "") + " ▌")

                odg, novo_stanje, sirovi = pozovi_pacijenta_stream(
                    stanje["poruke_api"], sc, stanje.get("zadnje_stanje"), _ispisi)
                mjesto.empty()
                prikazi_repliku(odg, "assistant")
                stanje["poruke_prikaz"].append({"role": "assistant", "content": odg})
                # U historiju ide SIROVI odgovor, s blokom stanja — tako pacijent
                # u sljedecem potezu vidi svoje prethodno povjerenje.
                stanje["poruke_api"].append({"role": "assistant", "content": sirovi or odg})
                if novo_stanje:
                    stanje["stanja"].append(novo_stanje)
                    stanje["zadnje_stanje"] = novo_stanje
            zapamti_potez(stanje)
            st.rerun()
        else:
            st.info(f"Dostigli ste maksimalan broj unosa ({MAX_POTEZA}). Savjetovanje se završava.")
            zavrsi_i_ocijeni(stanje, sc, odabrani_id)
            st.rerun()

st.divider()
if not stanje["zavrseno"] and stanje["broj_poteza"] >= 2:
    if st.button("Završi savjetovanje i dobij ocjenu", type="primary", use_container_width=True):
        zavrsi_i_ocijeni(stanje, sc, odabrani_id)
        st.rerun()

if stanje["zavrseno"] and stanje["ocjena"]:
    prikazi_ocjenu(stanje["ocjena"], stanje.get("stanja"))
    prikazi_epilog(sc)
