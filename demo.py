"""Demo slučaj — besplatan teaser, bez ijednog API poziva.

Cijeli razgovor je unaprijed napisan: posjetilac na svakom koraku bira jednu od
tri replike, a pacijentov odgovor i završna ocjena su fiksni tekstovi. Nema
poziva prema Anthropicu, nema upisa u bazu i nema troška — demo se može ostaviti
otvorenim za sve, dok pravi simulator ostaje zaključan za članove.

Slučaj je stvarni scenarij 2 (Amra, kantarion i palpitacije), skraćen na pet
odluka koje nose cijelu pouku.
"""

import streamlit as st

DEMO = {
    "naziv": "Palpitacije i biljni dodatak prehrani",
    "pacijent": "Amra, 33 godine",
    "terapija": "kvetiapin 100 mg i sertralin 50 mg, na recept, već tri mjeseca",
    "uvod": (
        "Petak popodne, gužva za pultom. Pred vama je žena od tridesetak godina. "
        "Djeluje nervozno i žuri joj se."
    ),
    "pocetna": "Dobar dan. Imate li nešto za smirenje? Srce mi lupa već danima, ne znam šta da radim.",
    "koraci": [
        {
            "naslov": "1. korak — otvaranje",
            "opcije": [
                {
                    "tekst": "Imamo matičnjak i valerijanu, oboje su blage. Da vam dam kapi?",
                    "odgovor": "Može, dajte to. Samo da mi prestane ovo lupanje.",
                    "bod": 0,
                    "komentar": "Zahtjev je uslužen prije nego što se saznalo išta. Lupanje srca "
                                "koje traje danima nije tegoba za koju se izdaje preparat bez pitanja.",
                },
                {
                    "tekst": "Kada se javlja to lupanje — u mirovanju ili pri naporu? I koliko dugo traje?",
                    "odgovor": "Javlja se i kad sjedim i kad se krećem. Od prošle sedmice je, "
                               "dešava se više puta na dan, traje kratko pa prestane samo.",
                    "bod": 2,
                    "komentar": "Otvoreno pitanje o simptomu, prije bilo kakve preporuke. Dobili ste "
                                "vremenski slijed — on će kasnije biti ključ.",
                },
                {
                    "tekst": "To vam je vjerovatno od stresa. Imate li puno obaveza u zadnje vrijeme?",
                    "odgovor": "Pa imam, imam... nije mi baš lako sad kod kuće. Valjda je od toga.",
                    "bod": 1,
                    "komentar": "Stres je ovdje lažni trag i pacijentica ga rado prihvata. Ponudili "
                                "ste joj objašnjenje umjesto da ga tražite.",
                },
            ],
        },
        {
            "naslov": "2. korak — terapija",
            "opcije": [
                {
                    "tekst": "Vidim da uzimate kvetiapin i sertralin. Jesu li vam doze nedavno mijenjane?",
                    "odgovor": "Ne, doze su iste, to uzimam već tri mjeseca. Psihijatar mi je propisao.",
                    "bod": 2,
                    "komentar": "Tačno pitanje — promjena doze je razuman uzrok koji treba isključiti. "
                                "Isključili ste ga i suzili prostor.",
                },
                {
                    "tekst": "Pijete li puno kafe? Pušite li?",
                    "odgovor": "Ne pušim i ne pretjerujem s kafom, ne bi to bilo.",
                    "bod": 1,
                    "komentar": "Uredno pitanje, ali ono provjerava najbezazleniji uzrok dok ozbiljniji "
                                "stoji neispitan.",
                },
                {
                    "tekst": "Jeste li išli kod ljekara zbog ovoga?",
                    "odgovor": "Jesam, sinoć. Mjerili su mi puls, bio je preko 150, uradili EKG i "
                               "ultrazvuk srca. Rekli su da je srce zdravo i da nešto prekinem, "
                               "ali ja ne znam baš šta je mislio.",
                    "bod": 2,
                    "komentar": "Veliki dobitak: nalaz je uredan, a ljekar je nešto rekao da prekine. "
                                "To „nešto“ je sada najvažnija stvar u razgovoru.",
                },
            ],
        },
        {
            "naslov": "3. korak — ključno pitanje",
            "opcije": [
                {
                    "tekst": "Uzimate li još nešto osim tih tableta — vitamine, čajeve, kapsule, bilo šta?",
                    "odgovor": "Pa... uzimam nešto, ali to je samo jedna biljka, prirodno je. "
                               "Prijateljica mi je preporučila. Mislite da je to bitno?",
                    "bod": 3,
                    "komentar": "Ovo je pitanje zbog kojeg cijeli slučaj postoji. Primijetite da je "
                                "odgovor oklijevajući i umanjujući — „samo jedna biljka, prirodno je“.",
                },
                {
                    "tekst": "Uzimate li još neke lijekove?",
                    "odgovor": "Ne, samo ove što mi je psihijatar dao.",
                    "bod": 1,
                    "komentar": "Za pacijenta biljni preparat nije lijek. Riječ „lijekovi“ zatvara "
                                "vrata koja riječi „dodaci, čajevi, kapsule“ otvaraju.",
                },
                {
                    "tekst": "Dobro. Onda ću vam dati magnezij, to smiruje srce.",
                    "odgovor": "Hvala vam, uzeću to.",
                    "bod": 0,
                    "komentar": "Preporuka bez kompletne slike terapije. Pacijentica odlazi s "
                                "preparatom, a uzrok ostaje kod kuće u kutiji.",
                },
            ],
        },
        {
            "naslov": "4. korak — prepoznavanje",
            "opcije": [
                {
                    "tekst": "Koja je to biljka i u kojem obliku? Imate li kutiju kod sebe?",
                    "odgovor": "Kapsule su. Nisam baš pogledala, na kutiji piše neka biljka sa žutim "
                               "cvijetom. Uzimam ih nekih tri sedmice.",
                    "bod": 3,
                    "komentar": "Opis laika plus trajanje. Tri sedmice uzimanja, a simptomi od prošle "
                                "sedmice — vremenski slijed se upravo zatvorio.",
                },
                {
                    "tekst": "Prirodno ne znači bezopasno. Prestanite s tim odmah.",
                    "odgovor": "Dobro... ali zašto? Prijateljica ga pije godinama i njoj ništa nije.",
                    "bod": 1,
                    "komentar": "Zaključak je tačan, ali bez podatka o kojoj se biljci radi ne možete "
                                "ni objasniti zašto, ni znati koliko je hitno.",
                },
                {
                    "tekst": "Je li vam prijateljica ljekar?",
                    "odgovor": "Nije... ali ona se razumije u to, čita puno o prirodnim stvarima.",
                    "bod": 0,
                    "komentar": "Osuđujući ton. Pacijentica se brani umjesto da priča, a vi i dalje "
                                "ne znate šta uzima.",
                },
            ],
        },
        {
            "naslov": "5. korak — postupak",
            "opcije": [
                {
                    "tekst": "To je najvjerovatnije kantarion. On ubrzava razgradnju vaših lijekova i "
                             "uz sertralin može izazvati ozbiljnu reakciju — vjerovatno je to ono što "
                             "vam je ljekar rekao da prekinete. Prestanite s kapsulama danas i javite "
                             "se ljekaru da to zna. Terapiju koju vam je propisao ne dirajte.",
                    "odgovor": "Ajoj, pa ja to nisam ni pomislila... Nisam ni ljekaru rekla šta pijem, "
                               "bilo mi je glupo. Hvala vam, prestajem odmah.",
                    "bod": 3,
                    "komentar": "Imenovali ste preparat, objasnili mehanizam laičkim jezikom, povezali "
                                "ga s onim što je ljekar rekao i jasno razdvojili šta se prekida a šta "
                                "ne. Pacijentica je i priznala zašto je prešutjela.",
                },
                {
                    "tekst": "Prekinite i kantarion i sertralin dok ne odete kod ljekara.",
                    "odgovor": "Dobro, prekinuću oboje.",
                    "bod": 0,
                    "komentar": "Nagli prekid propisane terapije je nova opasnost. Farmaceut ne ukida "
                                "ono što je ljekar propisao.",
                },
                {
                    "tekst": "Prestanite s kapsulama i javite se ljekaru ako se ne popravi.",
                    "odgovor": "Dobro, hvala.",
                    "bod": 2,
                    "komentar": "Ispravna akcija, ali bez objašnjenja. Pacijentica koja ne razumije "
                                "zašto nešto prekida često se toj navici vrati za dvije sedmice.",
                },
            ],
        },
    ],
    "maks": 13,
    "rasplet": (
        "**Šta je bilo u kutiji.** Kantarion (*Hypericum perforatum*), 300 mg dnevno. Biljka sa "
        "žutim cvijetom koja se u BiH prodaje slobodno, kao „prirodno za raspoloženje“.\n\n"
        "**Zašto je to opasno.** Kantarion je snažan induktor CYP3A4 i djeluje serotonergički. "
        "Uz sertralin nosi rizik od serotoninskog sindroma, a uz kvetiapin snižava njegovu "
        "koncentraciju. Amrina supraventrikularna tahikardija javila se tri sedmice nakon što je "
        "počela uzimati kapsule — i sve ostale pretrage bile su uredne.\n\n"
        "**Zašto ju je ljekar propustio.** Pitao ju je šta uzima, a ona je navela samo ono što "
        "smatra lijekovima. Kapsule iz zdrave hrane nije spomenula jer joj je bilo neugodno. "
        "Za pult apoteke to nije rijedak slučaj — to je pravilo."
    ),
}


def _ocjena_tekst(bodovi, maks):
    p = bodovi / maks if maks else 0
    if p >= 0.85:
        return "#16a34a", "Odlično vođen razgovor", (
            "Došli ste do kantariona kroz pitanja, a ne kroz sreću, i objasnili ste zašto. "
            "Ovako izgleda savjetovanje koje spriječi štetu.")
    if p >= 0.6:
        return "#0D8A9E", "Dobar razgovor s prostorom za više", (
            "Otkrili ste ono što je bitno, ali ste negdje ponudili zaključak umjesto pitanja "
            "ili preskočili objašnjenje. To je razlika između tačnog savjeta i savjeta koji se "
            "poštuje.")
    if p >= 0.35:
        return "#f59e0b", "Ključni podatak vam je izmakao", (
            "Dio slike ste dobili, ali kantarion je ostao neotkriven ili neobjašnjen. "
            "U apoteci bi Amra otišla kući s istim kapsulama.")
    return "#ef4444", "Pacijentica je otišla s uzrokom u torbi", (
        "Preporuka je data prije nego što je slika bila kompletna. Ovo je najčešći način na koji "
        "se propuste interakcije s biljnim preparatima.")


def prikazi_demo():
    """Cijeli demo tok. Vraća True ako korisnik traži izlaz iz demoa."""
    s = st.session_state.setdefault("demo_stanje", {"korak": 0, "izbori": [], "gotov": False})

    st.markdown(
        """
        <div style="background:linear-gradient(135deg,#0D8A9E,#1E3A8A);border-radius:16px;
             padding:20px 24px;color:white;margin-bottom:18px">
            <div style="font-size:12px;letter-spacing:1.2px;text-transform:uppercase;opacity:.85">
                Besplatan demo slučaj</div>
            <div style="font-size:22px;font-weight:700;margin-top:4px">Palpitacije i biljni dodatak prehrani</div>
            <div style="font-size:14px;opacity:.9;margin-top:6px">
                Pet odluka za pultom. U pravom simulatoru razgovor vodite svojim riječima —
                ovdje birate između ponuđenih replika.</div>
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"**Pacijent:** {DEMO['pacijent']} · **Terapija:** {DEMO['terapija']}\n\n*{DEMO['uvod']}*"
    )
    st.markdown("---")

    with st.chat_message("assistant"):
        st.markdown(DEMO["pocetna"])

    # Odigrani koraci
    for i, izbor in enumerate(s["izbori"]):
        korak = DEMO["koraci"][i]
        opcija = korak["opcije"][izbor]
        with st.chat_message("user"):
            st.markdown(opcija["tekst"])
        with st.chat_message("assistant"):
            st.markdown(opcija["odgovor"])
        st.caption(f"**{korak['naslov']}** · {opcija['komentar']}")

    # Sljedeći korak
    if s["korak"] < len(DEMO["koraci"]):
        korak = DEMO["koraci"][s["korak"]]
        st.markdown(f"##### {korak['naslov']} — šta kažete?")
        for j, opcija in enumerate(korak["opcije"]):
            if st.button(opcija["tekst"], key=f"demo_{s['korak']}_{j}", use_container_width=True):
                s["izbori"].append(j)
                s["korak"] += 1
                st.rerun()
        return False

    # Rezultat
    bodovi = sum(DEMO["koraci"][i]["opcije"][j]["bod"] for i, j in enumerate(s["izbori"]))
    maks = DEMO["maks"]
    ocjena = round(bodovi / maks * 10, 1)
    boja, naslov, tekst = _ocjena_tekst(bodovi, maks)

    st.markdown("---")
    st.markdown(
        f"""
        <div style="background:{boja}12;border:2px solid {boja}44;border-radius:18px;
             padding:24px;text-align:center;margin:12px 0">
            <div style="font-size:44px;font-weight:800;color:{boja};line-height:1">
                {ocjena:.1f}<span style="font-size:20px;color:#94a3b8;font-weight:400">/10</span></div>
            <div style="font-weight:700;color:{boja};margin-top:8px;font-size:17px">{naslov}</div>
            <div style="color:#475569;font-size:14px;margin-top:6px;max-width:52ch;
                 margin-left:auto;margin-right:auto">{tekst}</div>
        </div>""",
        unsafe_allow_html=True,
    )

    st.markdown("#### Rasplet slučaja")
    st.markdown(DEMO["rasplet"])

    st.markdown("---")
    st.info(
        "**Ovo je bio demo s ponuđenim odgovorima.** U simulatoru pišete svojim riječima, "
        "pacijent reaguje na način na koji ga pitate, a ocjenu dobijate po rubrici s citatima "
        "iz vlastitog razgovora. Pristup je otvoren članovima Edu Pharma Community."
    )

    c1, c2 = st.columns(2)
    if c1.button("Odigraj demo ponovo", use_container_width=True):
        st.session_state["demo_stanje"] = {"korak": 0, "izbori": [], "gotov": False}
        st.rerun()
    return c2.button("Nazad na prijavu", type="primary", use_container_width=True)
