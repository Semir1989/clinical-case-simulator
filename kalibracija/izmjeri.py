"""Mjeri koliko evaluator odstupa od Semirovih referentnih ocjena.

    python kalibracija/izmjeri.py

Pokreće se iz korijena projekta, poslije svake izmjene prompta evaluatora.
Troši API — jedan poziv po potvrđenom transkriptu (oko 0,02 USD po pozivu).

Uz odstupanje po kategorijama provjerava i regresiju iz nalaza N2: da li je
evaluator neku temu prijavio kao „nije pitao“ iako ju je farmaceut pitao. Tema
se prijavljuje samo ako je farmaceut o njoj pitao, evaluator je stavio u
„nije_pitano“, a NIJE je priznao u „pitano_ali_neodgovoreno“. Taj treći uslov je
bitan: kad evaluator prizna da je pitanje postavljeno a pacijent uskratio
odgovor, to nije lažna optužba nego upravo ispravno ponašanje.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.getcwd())
import rubrika                                          # noqa: E402
from konfig import MAX_POTEZA, MODEL_EVALUATOR          # noqa: E402
from ocjena import _normalizuj, provjeri_kriterije, provjeri_ocjenu  # noqa: E402
from promptovi import (EVALUATOR_SHEMA, EVALUATOR_SISTEM,  # noqa: E402
                       EVALUATOR_SISTEM_V2)

# Teme koje se u ocjenama najčešće pogrešno prijave kao "nije pitao".
# Izrazi su namjerno uski — "preparat" ili "dodat" hvataju i sasvim legitimne
# zamjerke ("nije pitao za naziv preparata"), pa bi širi popis prijavljivao
# lažne uzbune umjesto stvarne regresije.
OKIDACI = {
    "biljni preparati i suplementi": ["biljn", "suplement", "dodatak prehrani", "dodatke prehrani",
                                      "dodataka prehrani", "dodaci prehrani"],
    "ostali lijekovi": ["jos nesto od lijekova", "jos neke lijekove", "koje lijekove uzimate"],
    "posjeta ljekaru": ["bili kod ljekara", "bili kod doktora", "jeste li kod ljekara"],
}


def ucitaj():
    put = os.path.join("kalibracija", "referenca.json")
    if not os.path.exists(put):
        sys.exit("Nema kalibracija/referenca.json — pokreni prvo izvuci_referencu.py")
    with io.open(put, encoding="utf-8") as f:
        return json.load(f)


def scenarij(sid):
    """Dohvata scenarij iz baze; ugrađeni scenariji se čitaju iz app.py."""
    from dotenv import load_dotenv
    from supabase import create_client
    load_dotenv(".env")
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    r = db.table("scenarios").select("*").eq("id", sid).execute()
    if r.data:
        return r.data[0]
    sys.exit(f"Scenarij {sid} nije u bazi — ugrađeni scenariji se moraju prvo uvesti.")


def sumnjive_optuzbe(rezultat, transkript):
    """Vraća teme koje su prijavljene kao 'nije pitano' iako su u transkriptu pitane."""
    pitanja = _normalizuj(" ".join(
        r.strip() for r in transkript.split("\n") if r.startswith("Farmaceut:")))
    nije = _normalizuj(" ".join(
        n.get("pitanje", "") if isinstance(n, dict) else str(n)
        for n in (rezultat.get("nije_pitano") or rezultat.get("propustena_pitanja") or [])))
    # Ono što je evaluator priznao kao postavljeno pitanje nije lažna optužba.
    # v1 to drži u "pitano_ali_neodgovoreno", v2 u kriterijima koji nisu NE.
    priznato = _normalizuj(" ".join(
        [(p.get("pitanje", "") + " " + p.get("citat_farmaceuta", ""))
         for p in (rezultat.get("pitano_ali_neodgovoreno") or []) if isinstance(p, dict)]
        + [(k.get("tekst", "") + " " + k.get("citat", ""))
           for k in (rezultat.get("kriteriji") or {}).values()
           if isinstance(k, dict) and k.get("status") != "NE"]))
    return [tema for tema, izrazi in OKIDACI.items()
            if any(i in pitanja for i in izrazi)
            and any(i in nije for i in izrazi)
            and not any(i in priznato for i in izrazi)]


# Granica poteza koja je vazila kad su referentni transkripti odigrani.
# MAX_POTEZA je 9. 9. 2026. spusten na 7, ali referenca je snimljena na 10 i to
# se ne smije mijenjati naknadno: evaluatoru se govori koliko je poteza farmaceut
# IMAO NA RASPOLAGANJU, ne koliko ih je potrosio. Manji broj bi ga branio od
# zasluzenih zamjerki, veci bi ga kaznjavao za ono sto nije stigao.
GRANICA_REFERENCE = 10


def granica_poteza(stavka):
    return int(stavka.get("max_poteza") or GRANICA_REFERENCE)


def ocijeni_v2(ai, sc, s, rub):
    """Poziva ocjenjivač v2 — presuda po kriteriju kroz tool use."""
    poruka = (f"Ocijeni savjetovanje farmaceuta u apoteci.\n\n"
              f"Scenarij: {sc['ime']}, {sc['godine']} god. — {sc['tegoba']}\n"
              f"Crvene zastavice: {sc['crvene_zastavice']}\n"
              f"Očekivano savjetovanje: {sc['ocekivano']}\n\n"
              f"OGRANIČENJE RAZGOVORA: farmaceut je imao najviše "
              f"{granica_poteza(s)} poteza "
              f"(poruka). Vidi pravilo 3.\n\nTRANSKRIPT:\n{s['transkript']}\n\n"
              f"Presudi svaki kriterij alatom \"ocijeni\". Svaki DA i DJELIMICNO nosi "
              f"doslovan citat.")
    r = ai.messages.create(
        model=MODEL_EVALUATOR, max_tokens=4000, temperature=0,
        system=EVALUATOR_SISTEM_V2,
        tools=[{"name": "ocijeni",
                "description": "Presuda po svakom kriteriju rubrike, s dokazom iz transkripta.",
                "input_schema": rubrika.shema_alata(rub)}],
        tool_choice={"type": "tool", "name": "ocijeni"},
        messages=[{"role": "user", "content": poruka}],
    )
    for blok in r.content:
        if blok.type == "tool_use":
            return provjeri_kriterije(blok.input, s["transkript"], rub)
    sys.exit("Model nije pozvao alat — provjeri shemu.")


def _ispisi(s, rez):
    ref = s["referenca"]
    print(f"\n{s['scenarij']} ({s['datum']})")
    print(f"  {'kategorija':<14} {'referenca':>10} {'evaluator':>10} {'razlika':>9}")
    for k in ("anamneza", "komunikacija", "sigurnost", "ukupno"):
        dobio = rez.get("ukupna_ocjena") if k == "ukupno" else rez.get(k, 0)
        print(f"  {k:<14} {ref[k]:>10} {dobio:>10} {abs(float(dobio) - float(ref[k])):>9.1f}")

    odbaceno = len(rez.get("odbaceno", []))
    if odbaceno:
        print(f"  odbačeno tvrdnji bez dokaza: {odbaceno}")
    for kz in rez.get("kazne_primijenjene") or []:
        print(f"  kazna: {kz['opis']} -> {kz['kategorija']} max {kz['max']:g}")


def _zbroji(zbir, rez, ref):
    for k in ("anamneza", "komunikacija", "sigurnost", "ukupno"):
        dobio = rez.get("ukupna_ocjena") if k == "ukupno" else rez.get(k, 0)
        zbir[k] += abs(float(dobio) - float(ref[k]))


def main():
    from anthropic import Anthropic
    from dotenv import load_dotenv
    load_dotenv(".env")
    ai = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    podaci = ucitaj()
    stavke = [s for s in podaci["stavke"] if s.get("potvrdio_semir")]
    if not stavke:
        sys.exit("Nijedna stavka nema potvrdio_semir=true. Ispravi ocjene u referenca.json "
                 "pa pokreni ponovo.")

    zbir = {"anamneza": 0.0, "komunikacija": 0.0, "sigurnost": 0.0, "ukupno": 0.0}
    sve_sumnje = []

    v1 = "--v1" in sys.argv
    print("Ocjenjivač: " + ("v1 (slobodan JSON)" if v1 else "v2 (kriteriji kroz tool use)"))

    for s in stavke:
        sc = scenarij(s["scenarij"])
        rub = None if v1 else rubrika.za_scenarij(sc, s["scenarij"])
        if rub:
            rez = ocijeni_v2(ai, sc, s, rub)
            _ispisi(s, rez)
            _zbroji(zbir, rez, s["referenca"])
            sumnje = sumnjive_optuzbe(rez, s["transkript"])
            if sumnje:
                sve_sumnje.append((s["scenarij"], sumnje))
                for tema in sumnje:
                    print(f"  SUMNJIVO: '{tema}' prijavljeno kao nepitano, a jeste pitano")
            continue

        poruka = (f"Ocijeni savjetovanje farmaceuta u apoteci.\n\n"
                  f"Scenarij: {sc['ime']}, {sc['godine']} god. — {sc['tegoba']}\n"
                  f"Crvene zastavice: {sc['crvene_zastavice']}\n"
                  f"Očekivano savjetovanje: {sc['ocekivano']}\n\n"
                  f"RUBRIKA:\n{sc.get('rubrika','')}\n\n"
                  f"OGRANIČENJE RAZGOVORA: farmaceut je imao najviše "
              f"{granica_poteza(s)} poteza "
                  f"(poruka). Vidi pravilo 3.\n\nTRANSKRIPT:\n{s['transkript']}\n\n"
                  f"Vrati ISKLJUČIVO validan JSON bez ikakvog teksta prije ili poslije, "
                  f"tačno ovog oblika:\n{EVALUATOR_SHEMA}")

        r = ai.messages.create(model=MODEL_EVALUATOR, max_tokens=3000, temperature=0,
                               system=EVALUATOR_SISTEM,
                               messages=[{"role": "user", "content": poruka}])
        tekst = r.content[0].text
        rez = json.loads(tekst[tekst.find("{"):tekst.rfind("}") + 1])
        rez = provjeri_ocjenu(rez, s["transkript"])

        _ispisi(s, rez)
        _zbroji(zbir, rez, s["referenca"])
        sumnje = sumnjive_optuzbe(rez, s["transkript"])
        if sumnje:
            sve_sumnje.append((s["scenarij"], sumnje))
            for tema in sumnje:
                print(f"  SUMNJIVO: '{tema}' prijavljeno kao nepitano, a jeste pitano")

    n = len(stavke)
    print(f"\nProsječno odstupanje po {n} transkripta:")
    for k, v in zbir.items():
        print(f"  {k:<14} {v / n:>5.2f} bodova")

    if sve_sumnje:
        print("\nREGRESIJA N2 — evaluator i dalje optužuje za pitanja koja jesu postavljena:")
        for sid, teme in sve_sumnje:
            print(f"  {sid}: {', '.join(teme)}")
        sys.exit(1)
    print("\nNijedna lažna optužba nije nađena.")


if __name__ == "__main__":
    main()
