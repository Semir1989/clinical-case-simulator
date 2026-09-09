"""Pozivi prema modelu: pacijent, ocjenjivac, generator scenarija."""
import base64
import json

import streamlit as st

from konfig import (JEZIK_PRAVILO, MAX_POTEZA, zabiljezi_gresku, MODEL_EVALUATOR, MODEL_GENERATOR, MODEL_PACIJENT,
                    ai)
from baza import ISPIT, db_log_upotrebu, db_spremi
from ocjena import izvuci_json, provjeri_kriterije, provjeri_ocjenu
from rubrika import shema_alata, za_scenarij as rubrika_za_scenarij
from stanje import izdvoji_stanje, sazetak_za_evaluatora
from scenariji import SCENARIJI
from promptovi import (EPILOG_SHEMA, EPILOG_SISTEM, EVALUATOR_SHEMA,
                       EVALUATOR_SISTEM, EVALUATOR_SISTEM_V2, GENERATOR_SISTEM,
                       PACIJENT_PRIRUCNIK)

PERSONA_OPISI = {
    "pricljivost": "Pričljivost: {v} od 5",
    "obrazovanje": "Obrazovanje: {v}",
    "raspolozenje": "Raspoloženje: {v}",
    "zanimanje": "Zanimanje: {v}",
    "porodica": "Porodica i okolnosti: {v}",
    "odnos_prema_lijekovima": "Odnos prema lijekovima: {v}",
}


def zabiljezi_potrosnju(dogadjaj, usage, scenarij=None):
    """Upisuje potrošnju u usage_log, uključujući keš.

    Do sada se bilježio samo `input_tokens`, koji NE uključuje keširane tokene.
    Upis keša se naplaćuje 1,25x, čitanje 0,1x — pa je procjena troška u admin
    panelu bila osjetno niža od stvarne. Oba se svode na "ekvivalent punih
    ulaznih tokena" da stara kolona ostane uporediva sa starim zapisima.
    """
    upis = getattr(usage, "cache_creation_input_tokens", 0) or 0
    citanje = getattr(usage, "cache_read_input_tokens", 0) or 0
    ulaz_ekvivalent = round((usage.input_tokens or 0) + upis * 1.25 + citanje * 0.10)
    if scenarij is None:
        scenarij = st.session_state.get("odabrani_scenarij", "")
    db_log_upotrebu(dogadjaj, scenarij, ulaz_ekvivalent, usage.output_tokens)


def opisi_personu(persona):
    if not persona:
        return ""
    redovi = [PERSONA_OPISI[k].format(v=persona[k])
              for k in PERSONA_OPISI if persona.get(k) not in (None, "")]
    if persona.get("zurba"):
        redovi.append("Žuri ti se — više puta to spomeneš.")
    return "\nTVOJA PERSONA (mijenja kako govoriš, ne šta znaš):\n- " + "\n- ".join(redovi) if redovi else ""


def opisi_cinjenice(sc):
    """Lista činjenica s okidačima; ako je nema, vraća stari tekstualni opis.

    Fallback postoji dok se svi scenariji ne konvertuju — scenarij bez liste
    mora i dalje raditi, samo bez okidača.
    """
    cinjenice = sc.get("cinjenice")
    if not cinjenice:
        return ("\nTVOJE SKRIVENE ČINJENICE — daješ ih po pravilu „KADA OTKRIVAŠ, A KADA ŠUTIŠ“, "
                f"a ništa izvan ovoga ne postoji:\n{sc.get('skriveni_detalji', '')}")

    redovi = []
    for c in cinjenice:
        oznaka = " [OSJETLJIVO — prešućuješ iz stida ili straha]" if c.get("osjetljivo") else ""
        redovi.append(
            f"- ({c.get('id', '?')}) {c.get('cinjenica', '')}\n"
            f"  otključava je: {c.get('okidac', 'bilo koje direktno pitanje o ovome')}{oznaka}"
        )
    return ("\nTVOJE ČINJENICE. Ovo je sve što o sebi znaš — ništa izvan ove liste ne postoji.\n"
            "Uz svaku piše njena oznaka u zagradi i pitanje koje je otključava. Kad neku "
            "otkriješ, u blok stanja upisuješ TAČNO tu oznaku iz zagrade, nikad izmišljenu.\n"
            + "\n".join(redovi))


def opisi_otpor(otpor):
    """Prigovori s uslovima popuštanja, redom kojim se iznose."""
    if not otpor:
        return ""
    redovi = []
    for o in sorted(otpor, key=lambda x: x.get("redoslijed", 99)):
        r = ['- "' + o.get("replika", "") + '"']
        if o.get("fatalno_ako_izda"):
            r.append("  OVAJ PRIGOVOR NE POPUŠTAŠ NIKAD, ma šta farmaceut rekao.")
        else:
            r.append("  popuštaš kad farmaceut " + o.get("uslov_popustanja", "objasni razlog")
                     + ", uz povjerenje najmanje " + str(o.get("prag_povjerenja", 5)))
        redovi.append("\n".join(r))
    return ("\nTVOJI PRIGOVORI, redom kojim ih iznosiš — jedan po replici, ne svi odjednom:\n"
            + "\n".join(redovi))


def opisi_znakove(znakovi):
    if not znakovi:
        return ""
    return ("\nŠTA SE NA TEBI VIDI (koristi kao didaskalije u uglastim zagradama, štedljivo):\n"
            + znakovi)


def napravi_system_prompt(sc):
    """Sistemski prompt pacijenta — oba bloka keširana.

    Statički priručnik (~3.300 tokena) isti je za sve scenarije. Dinamički blok
    (~1.600 tokena: činjenice, persona, otpor) isti je za svakog korisnika i
    svaki potez ISTOG scenarija — a plaćao se punom cijenom svaki potez, deset
    puta po partiji. Drugi prekid keša to zaustavlja.

    Keš se veže na prefiks, pa drugi prekid pokriva oba bloka zajedno; time je i
    minimalna dužina za keširanje ispunjena bez obzira na model.
    """
    staticki = PACIJENT_PRIRUCNIK + "\n\n" + JEZIK_PRAVILO
    dinamicki = (
        f"\nGlumaš: {sc['ime']}, {sc['godine']} god.\n"
        f"Tegoba: {sc['tegoba']}\n"
        f"Terapija koju odmah priznaješ: {sc['terapija']}\n"
        + opisi_personu(sc.get("persona"))
        + "\n" + opisi_cinjenice(sc)
        + "\n" + opisi_otpor(sc.get("otpor"))
        + "\n" + opisi_znakove(sc.get("vidljivi_znakovi"))
    )
    return [
        {"type": "text", "text": staticki, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": dinamicki, "cache_control": {"type": "ephemeral"}},
    ]


def sa_kesom(poruke):
    """Vraća kopiju historije s prekidom keša na posljednjoj poruci.

    Bez ovoga se cijeli dosadašnji razgovor u svakom potezu plaća iznova, a on
    raste sa svakim potezom. Kopija je namjerna: historija u sesiji i u bazi
    mora ostati obični tekst, jer se sprema i prikazuje.
    """
    if not poruke:
        return poruke
    kopija = list(poruke)
    zadnja = dict(kopija[-1])
    sadrzaj = zadnja.get("content")
    if isinstance(sadrzaj, str):
        zadnja["content"] = [{"type": "text", "text": sadrzaj,
                              "cache_control": {"type": "ephemeral"}}]
        kopija[-1] = zadnja
    return kopija


def pozovi_pacijenta(poruke, sc, prethodno_stanje=None, dodatna_uputa=""):
    """Vraća (replika bez bloka stanja, stanje, sirovi odgovor).

    Sirovi odgovor ide natrag u historiju SA blokom stanja — tako pacijent u
    sljedećem potezu vidi svoje prethodno povjerenje i ne počinje iznova.
    """
    sistem = napravi_system_prompt(sc)
    if dodatna_uputa:
        sistem = sistem + [{"type": "text", "text": dodatna_uputa}]
    r = ai.messages.create(
        model=MODEL_PACIJENT, max_tokens=500,
        system=sistem, messages=sa_kesom(poruke),
    )
    zabiljezi_potrosnju("poruka", r.usage)
    sirovi = r.content[0].text
    cist, novo = izdvoji_stanje(sirovi, prethodno_stanje)
    return cist, novo, sirovi


def pozovi_pacijenta_stream(poruke, sc, prethodno_stanje=None, na_dio=None):
    """Isto što i pozovi_pacijenta, ali replika stiže riječ po riječ.

    Blok stanja se ne smije vidjeti ni na trenutak, a stiže na kraju replike.
    Zato se prikazuje samo tekst do prvog "<": ako model još nije počeo blok,
    ništa se ne zadržava, a čim počne, sve iza njega ostaje skriveno. Blok se
    razlaže tek kad stigne cijeli tekst.

    Pri grešci se pada natrag na obični poziv — streaming je udobnost, replika
    je ono što se ne smije izgubiti.
    """
    sistem = napravi_system_prompt(sc)
    sirovi = ""
    try:
        with ai.messages.stream(model=MODEL_PACIJENT, max_tokens=500,
                                system=sistem, messages=sa_kesom(poruke)) as tok:
            for dio in tok.text_stream:
                sirovi += dio
                if na_dio:
                    na_dio(sirovi.split("<")[0])
            poruka = tok.get_final_message()
    except Exception as e:
        zabiljezi_gresku(e)
        return pozovi_pacijenta(poruke, sc, prethodno_stanje)

    zabiljezi_potrosnju("poruka", poruka.usage)
    cist, novo = izdvoji_stanje(sirovi, prethodno_stanje)
    return cist, novo, sirovi


UPUTA_ZATVARANJE = (
    "[UPUTA, nije replika farmaceuta] Razgovor se završava i farmaceut se oprostio. "
    "Daj SAMO svoju posljednju repliku — kratku, u prvom licu — iz koje se jasno vidi šta ćeš "
    "uraditi kad izađeš iz apoteke. U bloku stanja obavezno upiši fazu zatvaranje i ishod: "
    "prihvatio, prihvatio_nevoljko, odbio ili otisao_s_lijekom."
)


def zatvori_razgovor(poruke, sc, prethodno_stanje=None):
    """Traži završnu repliku prije ocjenjivanja, da polaznik vidi ishod svog rada.

    Uputa ide kao posljednji potez korisnika, ne samo u sistemski prompt: historija
    završava replikom pacijenta, pa bi model bez toga nastavljao tu istu repliku
    umjesto da počne novu — i vraćao prazno.
    """
    try:
        poruke = list(poruke) + [{"role": "user", "content": UPUTA_ZATVARANJE}]
        return pozovi_pacijenta(poruke, sc, prethodno_stanje, UPUTA_ZATVARANJE)
    except Exception as e:
        zabiljezi_gresku(e)
        return "", prethodno_stanje, ""


def pozovi_evaluatora(transkript, sc, broj_poteza=MAX_POTEZA, stanja=None):
    sazetak = sazetak_za_evaluatora(stanja, sc.get("cinjenice"))
    prompt = f"""Ocijeni savjetovanje farmaceuta u apoteci.

Scenarij: {sc['ime']}, {sc['godine']} god. — {sc['tegoba']}
Crvene zastavice: {sc['crvene_zastavice']}
Očekivano savjetovanje: {sc['ocekivano']}

RUBRIKA:
{sc.get('rubrika', '')}

OGRANIČENJE RAZGOVORA: farmaceut je imao najviše {broj_poteza} poteza (poruka). Vidi pravilo 3.

TRANSKRIPT:
{transkript}

{sazetak}

Vrati ISKLJUČIVO validan JSON bez ikakvog teksta prije ili poslije, tačno ovog oblika:
{EVALUATOR_SHEMA}"""
    r = ai.messages.create(
        model=MODEL_EVALUATOR, max_tokens=3000, temperature=0,
        system=EVALUATOR_SISTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    zabiljezi_potrosnju("evaluacija", r.usage)
    return r.content[0].text


def pozovi_evaluatora_v2(transkript, sc, rub, broj_poteza=MAX_POTEZA, stanja=None):
    """Ocjenjivač v2 — presuda po kriteriju kroz tool use.

    Shema alata nabraja svaki kriterij poimenično, pa model ne može preskočiti
    kriterij, izmisliti novi ni vratiti pokvaren JSON. Bodove ne traži uopšte —
    računa ih rubrika.izracunaj() u Pythonu.
    """
    sazetak = sazetak_za_evaluatora(stanja, sc.get("cinjenice"))
    prompt = f"""Ocijeni savjetovanje farmaceuta u apoteci.

Scenarij: {sc['ime']}, {sc['godine']} god. — {sc['tegoba']}
Crvene zastavice: {sc['crvene_zastavice']}
Očekivano savjetovanje: {sc['ocekivano']}

OGRANIČENJE RAZGOVORA: farmaceut je imao najviše {broj_poteza} poteza (poruka). Vidi pravilo 3.

TRANSKRIPT:
{transkript}

{sazetak}

Presudi svaki kriterij alatom "ocijeni". Svaki DA i DJELIMICNO nosi doslovan citat."""

    alat = {
        "name": "ocijeni",
        "description": "Presuda po svakom kriteriju rubrike, s dokazom iz transkripta.",
        "input_schema": shema_alata(rub),
    }
    # Alati i sistemski prompt su isti za svaki pokusaj istog scenarija, a
    # kesiranje pokriva prefiks (alati -> sistem -> poruke), pa jedan prekid na
    # sistemu kesira i shemu alata. Mijenja se samo transkript.
    r = ai.messages.create(
        model=MODEL_EVALUATOR, max_tokens=4000, temperature=0,
        system=[{"type": "text", "text": EVALUATOR_SISTEM_V2,
                 "cache_control": {"type": "ephemeral"}}],
        tools=[alat],
        tool_choice={"type": "tool", "name": "ocijeni"},
        messages=[{"role": "user", "content": prompt}],
    )
    zabiljezi_potrosnju("evaluacija", r.usage)
    for blok in r.content:
        if blok.type == "tool_use":
            return blok.input
    return None


def pokreni_evaluaciju(stanje, sc, sc_id, mode=ISPIT):
    transkript = "\n".join(
        f"{'Farmaceut' if p['role'] == 'user' else 'Pacijent'}: {p['content']}"
        for p in stanje["poruke_prikaz"]
    )
    stanja = stanje.get("stanja") or []
    rub = rubrika_za_scenarij(sc, sc_id)

    with st.spinner("Analizira savjetovanje..."):
        if rub:
            sirovo = pozovi_evaluatora_v2(transkript, sc, rub, MAX_POTEZA, stanja)
            rezultat = provjeri_kriterije(sirovo, transkript, rub) if sirovo else None
        else:
            # Scenarij bez rubrike koju umijemo raščlaniti — stari put.
            rezultat = izvuci_json(pozovi_evaluatora(transkript, sc, MAX_POTEZA, stanja))
            if rezultat:
                rezultat = provjeri_ocjenu(rezultat, transkript)

    if rezultat:
        stanje["ocjena"] = rezultat
        stanje["zavrseno"] = True
        db_spremi(st.session_state.get("korisnik_email", ""), sc_id, rezultat, transkript,
                  stanja, mode)
    else:
        st.error("Greška pri analizi ocjene. Pokušaj ponovo.")
        stanje["zavrseno"] = False


def generisi_epilog(sc):
    """Epilog i uzoran razgovor za scenarij — jedan poziv, jednom po scenariju.

    Generiše ih administrator i spremaju se uz scenarij, pa polaznika ne
    koštaju ništa: tekst je isti za sve i nema razloga da se pravi iznova.
    Vraća (epilog, uzoran_razgovor) ili (None, None).
    """
    prompt = f"""Scenarij: {sc.get('naziv', '')}
Pacijent: {sc.get('ime', '')}, {sc.get('godine', '')} god.
Razlog posjete: {sc.get('tegoba', '')}
Terapija: {sc.get('terapija', '')}
Šta pacijent prešućuje: {sc.get('skriveni_detalji', '')}
Crvene zastavice: {sc.get('crvene_zastavice', '')}
Očekivano savjetovanje: {sc.get('ocekivano', '')}
Klinička pozadina: {sc.get('obrazlozenje', '')}

Vrati ISKLJUČIVO validan JSON bez teksta prije ili poslije, tačno ovog oblika:
{EPILOG_SHEMA}"""
    try:
        r = ai.messages.create(
            model=MODEL_GENERATOR, max_tokens=2000, temperature=0.4,
            system=EPILOG_SISTEM,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        zabiljezi_gresku(e)
        return None, None

    zabiljezi_potrosnju("epilog", r.usage, sc.get("id", ""))
    podaci = izvuci_json(r.content[0].text) or {}
    return podaci.get("epilog"), podaci.get("uzoran_razgovor")


def generisi_scenarij_iz_pdfa(pdf_bytes, tezina, smjernice):
    """Šalje PDF case report Claudeu i vraća generisani scenarij (dict) ili None."""
    upute = (
        f"Nivo težine: {tezina}.\n"
        + ("Ekspertni nivo: dodaj i drugi sloj problema (npr. interakcija koja se vidi tek "
           "kad se otkrije kompletna terapija) i pojačaj lažni trag.\n"
           if tezina == "Ekspertno" else "")
        + (f"Dodatne smjernice admina: {smjernice.strip()}\n" if smjernice.strip() else "")
        + "Analiziraj priloženi case report i kreiraj scenarij prema uputama."
    )
    r = ai.messages.create(
        model=MODEL_GENERATOR, max_tokens=8000,
        system=GENERATOR_SISTEM,
        messages=[{
            "role": "user",
            "content": [
                {"type": "document", "source": {
                    "type": "base64", "media_type": "application/pdf",
                    "data": base64.standard_b64encode(pdf_bytes).decode(),
                }},
                {"type": "text", "text": upute},
            ],
        }],
    )
    db_log_upotrebu("generisanje_scenarija", "",
                    r.usage.input_tokens, r.usage.output_tokens)
    return izvuci_json(r.content[0].text)


def sljedeci_scenarij_id():
    """Prvi slobodan ID oblika scenarij_N."""
    n = 1
    while f"scenarij_{n}" in SCENARIJI:
        n += 1
    return f"scenarij_{n}"
