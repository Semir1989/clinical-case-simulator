"""Prevodi postojeće scenarije iz teksta u personu + listu činjenica (F3).

    python skripte/konvertuj_cinjenice.py --pregled     # samo ispiše šta bi upisao
    python skripte/konvertuj_cinjenice.py --upisi       # upisuje u bazu

Sadržaj je prepisan ručno iz kolone skriveni_detalji svakog scenarija — ništa
nije izmišljeno i ništa nije izostavljeno. Stara kolona ostaje netaknuta kao
zaštita: scenarij bez liste činjenica i dalje radi po starom.

Okidač je pitanje koje otključava činjenicu. Piše se onako kako bi ga farmaceut
stvarno postavio, u širem smislu — "pitanje o dodacima, čajevima ili kapsulama",
ne doslovan tekst pitanja.
"""
import argparse
import json
import os
import sys

SCENARIJI = {
    # ── Scenarij 1 — Lejla, 18, trudnoća i klobetazol ───────────────────────
    "scenarij_1": {
        "persona": {
            "pricljivost": 2,
            "obrazovanje": "srednje",
            "raspolozenje": "nervozan",
            "zurba": False,
            "zanimanje": "završila srednju školu, ne radi",
            "porodica": "prva trudnoća, živi kod svekrve",
            "odnos_prema_lijekovima": "vjeruje komšinici više nego ljekaru; misli da krema iz apoteke ne može škoditi",
        },
        "cinjenice": [
            {"id": "trudnoca_33s",
             "cinjenica": "u 33. je sedmici prve trudnoće",
             "okidac": "pitanje o trudnoći, dojenju ili posebnim stanjima, ili zašto uzima vitamine",
             "osjetljivo": False},
            {"id": "klobetazol_6mj",
             "cinjenica": "klobetazol 0,05% kremu maže svaki dan već šest mjeseci",
             "okidac": "pitanje koliko dugo koristi kremu ili koliko često je maže",
             "osjetljivo": False},
            {"id": "zalim_losion",
             "cinjenica": "uz kremu svaki dan koristi i Zalim losion, na isto mjesto",
             "okidac": "pitanje koristi li još nešto na koži, neki drugi preparat, losion ili mast",
             "osjetljivo": False},
            {"id": "komsinica",
             "cinjenica": "kremu joj je preporučila komšinica; zbog kože nije bila kod ljekara",
             "okidac": "pitanje ko joj je preporučio kremu ili je li bila kod ljekara zbog kože",
             "osjetljivo": True},
            {"id": "strije_mrlje",
             "cinjenica": "na koži su joj se pojavile strije i sjajne tanke mrlje, misli da je to od trudnoće",
             "okidac": "pitanje kako koža izgleda, ima li promjena, mrlja ili strija",
             "osjetljivo": False},
            {"id": "vitamini",
             "cinjenica": "uzima vitamine za trudnoću koje joj je propisao ginekolog",
             "okidac": "pitanje o lijekovima, vitaminima ili dodacima prehrani",
             "osjetljivo": False},
            {"id": "ginekolog_ne_zna",
             "cinjenica": "ginekologu nije spomenula da koristi kremu",
             "okidac": "pitanje zna li ginekolog za kremu ili je li nekome rekla",
             "osjetljivo": True},
        ],
    },

    # ── Scenarij 2 — Amra, 33, palpitacije i kantarion ──────────────────────
    "scenarij_2": {
        "persona": {
            "pricljivost": 3,
            "obrazovanje": "visoko",
            "raspolozenje": "uplasen",
            "zurba": False,
            "zanimanje": "radi u kancelariji",
            "porodica": "u braku, bračni problemi već mjesec dana",
            "odnos_prema_lijekovima": "misli da je prirodno automatski bezopasno; psihijatrijsku terapiju uzima uredno",
        },
        "cinjenice": [
            {"id": "kantarion",
             "cinjenica": "prije tri sedmice počela uzimati biljne kapsule 300 mg dnevno; na kutiji je biljka sa žutim cvijetom",
             "okidac": "pitanje uzima li dodatke prehrani, biljne preparate, čajeve, kapsule ili išta osim propisane terapije",
             "osjetljivo": True},
            {"id": "prijateljica",
             "cinjenica": "kapsule joj je preporučila prijateljica, za raspoloženje",
             "okidac": "pitanje ko joj je preporučio preparat ili zašto ga uzima",
             "osjetljivo": False},
            {"id": "potistenost",
             "cinjenica": "oko mjesec dana osjeća potištenost; ima bračne probleme",
             "okidac": "pitanje kako se psihički osjeća ili zašto je počela uzimati preparat za raspoloženje",
             "osjetljivo": True},
            {"id": "simptomi_sedmica",
             "cinjenica": "od prošle sedmice ima znojenje, nesanicu i lupanja srca — i u mirovanju i pri naporu, traju manje od minut i prestanu sama",
             "okidac": "pitanje o simptomima, kada su počeli, koliko traju i prate li ih drugi znaci",
             "osjetljivo": False},
            {"id": "salsa",
             "cinjenica": "sinoć joj je na plesu srce jako lupalo oko minut i uplašila se",
             "okidac": "pitanje šta se desilo neposredno prije nego što je otišla ljekaru",
             "osjetljivo": False},
            {"id": "nalazi_hitne",
             "cinjenica": "na hitnoj su joj izmjerili puls 150–160 i pritisak 110/68, EKG je pokazao supraventrikularnu tahikardiju, a laboratorij i ultrazvuk srca bili su uredni",
             "okidac": "pitanje je li bila kod ljekara i šta su utvrdili ili šta piše u nalazima",
             "osjetljivo": False},
            {"id": "ljekar_prekini",
             "cinjenica": "ljekar joj je rekao da je srce strukturno zdravo i da prekine s tim biljnim dodatkom",
             "okidac": "pitanje šta joj je ljekar rekao ili preporučio",
             "osjetljivo": False},
            {"id": "nije_rekla_ljekaru",
             "cinjenica": "ljekaru nije rekla tačno šta uzima jer joj je bilo neugodno",
             "okidac": "pitanje je li ljekar znao šta uzima ili je li mu rekla za kapsule",
             "osjetljivo": True},
            {"id": "bez_ostalog",
             "cinjenica": "nema bolova u grudima, ne guši se, nije se onesvijestila; ne puši, ne pije alkohol redovno i ne uzima druge lijekove",
             "okidac": "pitanje o pratećim simptomima, navikama, kafi, cigaretama ili drugim lijekovima",
             "osjetljivo": False},
        ],
    },

    # ── Scenarij 3 — Fadila, 65, gripa i akutni glaukom ─────────────────────
    "scenarij_3": {
        "persona": {
            "pricljivost": 4,
            "obrazovanje": "osnovno",
            "raspolozenje": "umoran",
            "zurba": False,
            "zanimanje": "penzionerka, radila u tekstilnoj industriji",
            "porodica": "živi sama, kćerka u inostranstvu",
            "odnos_prema_lijekovima": "ne voli smetati ljekaru; misli da gripa prolazi sama",
        },
        "cinjenice": [
            {"id": "gripa_5dana",
             "cinjenica": "prije pet dana počela je gripa s temperaturom i kašljem",
             "okidac": "pitanje koliko dugo traju tegobe ili kada je počelo",
             "osjetljivo": False},
            {"id": "sastav_preparata",
             "cinjenica": "uzima kombinovani preparat u kesicama koji sadrži paracetamol, dekstrometorfan i gvajfenezin — naziv i sastav pročita tek kad je pitaju šta piše na kutiji",
             "okidac": "pitanje šta tačno uzima, kako se preparat zove ili šta piše na kutiji",
             "osjetljivo": False},
            {"id": "prekoracena_doza",
             "cinjenica": "zadnja dva dana uzima ga češće nego što piše na uputstvu jer kašalj ne prestaje",
             "okidac": "pitanje koliko puta dnevno ga uzima ili koliko kesica popije",
             "osjetljivo": False},
            {"id": "mutan_vid",
             "cinjenica": "zadnja dva dana vid joj je mutan na oba oka; sama to ne spominje jer misli da joj se pogoršala mrena",
             "okidac": "pitanje o vidu, o očima ili vidi li lošije nego inače",
             "osjetljivo": False},
            {"id": "sareni_krugovi",
             "cinjenica": "uveče oko sijalica vidi šarene krugove poput duge",
             "okidac": "pitanje vidi li krugove, aureole ili odsjaje oko svjetla",
             "osjetljivo": False},
            {"id": "fotofobija_crvenilo",
             "cinjenica": "jako joj smeta svjetlost i oči su joj crvene; htjela je usput tražiti kapi za crvene oči i nešto protiv mučnine",
             "okidac": "pitanje smeta li joj svjetlost, kakve su joj oči ili treba li još nešto",
             "osjetljivo": False},
            {"id": "glavobolja_povracanje",
             "cinjenica": "jutros je povraćala i ima jaku glavobolju u čelu iznad obrva; sve pripisuje gripi",
             "okidac": "pitanje gdje je tačno boli glava, kakva je bol ili ima li mučninu",
             "osjetljivo": False},
            {"id": "zjenice",
             "cinjenica": "u ogledalu je primijetila da su joj zjenice krupne i da se ne skupljaju",
             "okidac": "pitanje o izgledu očiju ili zjenica; ili empatično pitanje je li primijetila još nešto neobično",
             "osjetljivo": True},
            {"id": "katarakta",
             "cinjenica": "prije godinu joj je oftalmolog rekao da ima početnu kataraktu; pregled još čeka",
             "okidac": "pitanje o ranijim očnim nalazima, pregledima ili bolestima očiju",
             "osjetljivo": False},
            {"id": "dioptrija",
             "cinjenica": "cijeli život nosi naočale s plus dioptrijom, oko +3, dalekovidna je",
             "okidac": "pitanje nosi li naočale ili kakvu ima dioptriju",
             "osjetljivo": False},
            {"id": "bez_drugih_lijekova",
             "cinjenica": "nema drugih bolesti i ne uzima nikakve druge lijekove ni biljne preparate",
             "okidac": "pitanje o drugim lijekovima, bolestima ili biljnim preparatima",
             "osjetljivo": False},
            {"id": "nije_isla_ljekaru",
             "cinjenica": "ljekaru zbog ovoga nije išla — ne želi smetati zbog gripe i misli da će proći samo",
             "okidac": "pitanje je li bila kod ljekara",
             "osjetljivo": False},
        ],
    },

    # ── Scenarij 4 — Stefan, 71, Tribulus i rabdomioliza ────────────────────
    "scenarij_4": {
        "persona": {
            "pricljivost": 3,
            "obrazovanje": "srednje",
            "raspolozenje": "umoran",
            "zurba": True,
            "zanimanje": "penzioner, radio kao vozač",
            "porodica": "oženjen, unuci",
            "odnos_prema_lijekovima": "prirodne preparate ne smatra lijekovima; misli da farmaceut ne treba znati njegovu dijagnozu",
        },
        "cinjenice": [
            {"id": "atorvastatin",
             "cinjenica": "već šest godina uzima bijele tablete za holesterol — atorvastatin 40 mg, naziv ne zna",
             "okidac": "pitanje o lijekovima za holesterol ili masnoće u krvi, ili traženje da pokaže spisak terapije",
             "osjetljivo": False},
            {"id": "metoprolol",
             "cinjenica": "uzima tablete za srce i pritisak — metoprolol sukcinat 100 mg, naziv ne zna",
             "okidac": "pitanje koje lijekove uzima za srce i pritisak",
             "osjetljivo": False},
            {"id": "aspirin",
             "cinjenica": "svaki dan uzima mali aspirin 100 mg — taj naziv zna",
             "okidac": "pitanje uzima li još neke lijekove ili razrjeđivač krvi",
             "osjetljivo": False},
            {"id": "tribulus",
             "cinjenica": "prije tačno dvije sedmice počeo uzimati Tribulus terrestris 500 mg kapsule, jednom dnevno, kupljene u sportskoj prodavnici a ne u apoteci",
             "okidac": "pitanje uzima li dodatke prehrani, biljne ili prirodne preparate, kapsule iz sportske prodavnice ili s interneta",
             "osjetljivo": True},
            {"id": "pocetak_boli",
             "cinjenica": "bol u mišićima počela je tri do četiri dana nakon što je počeo uzimati te kapsule i stalno se pogoršava",
             "okidac": "pitanje kada je tačno bol počela ili je li nešto novo uveo prije toga",
             "osjetljivo": False},
            {"id": "bol_u_prsima",
             "cinjenica": "jutros ga bole i prsa — opisuje kao stisak u grudima koji je počeo od mišića",
             "okidac": "pitanje o bolu u prsima, stezanju ili nelagodi u grudima",
             "osjetljivo": False},
            {"id": "tamna_mokraca",
             "cinjenica": "mokraća mu je jutros bila tamnija nego obično, kao čaj; misli da je samo dehidriran",
             "okidac": "pitanje o boji mokraće ili promjenama pri mokrenju",
             "osjetljivo": True},
            {"id": "nije_biciklirao",
             "cinjenica": "prošle sedmice zapravo nije biciklirao, iako to sam tvrdi kad uđe u apoteku",
             "okidac": "pitanje kada je tačno biciklirao, koliko i koliko često",
             "osjetljivo": True},
            {"id": "koronarna_bolest",
             "cinjenica": "ima koronarnu bolest srca — zbog nje uzima aspirin i lijek za srce",
             "okidac": "pitanje o srčanim bolestima, dijagnozama ili zašto uzima te lijekove",
             "osjetljivo": True},
            {"id": "nikad_ranije",
             "cinjenica": "nikad ranije nije imao problema s mišićima otkad uzima tablete za holesterol",
             "okidac": "pitanje je li se ovo ikad ranije dešavalo",
             "osjetljivo": False},
        ],
    },
}


def pregled():
    for sid, p in SCENARIJI.items():
        osjetljivih = sum(1 for c in p["cinjenice"] if c["osjetljivo"])
        print(f"\n{sid}: {len(p['cinjenice'])} činjenica ({osjetljivih} osjetljivih)")
        print(f"  persona: pričljivost {p['persona']['pricljivost']}, "
              f"{p['persona']['obrazovanje']}, {p['persona']['raspolozenje']}"
              + (", žuri mu se" if p["persona"]["zurba"] else ""))
        for c in p["cinjenice"]:
            oznaka = "  [osjetljivo]" if c["osjetljivo"] else ""
            print(f"  · {c['id']}{oznaka}")


def upisi():
    from dotenv import load_dotenv
    from supabase import create_client
    load_dotenv(".env")
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    postojeci = {r["id"] for r in db.table("scenarios").select("id").execute().data or []}
    for sid, p in SCENARIJI.items():
        if sid not in postojeci:
            print(f"  {sid}: nema ga u bazi, preskačem")
            continue
        db.table("scenarios").update({
            "persona": p["persona"],
            "cinjenice": p["cinjenice"],
        }).eq("id", sid).execute()
        print(f"  {sid}: upisano {len(p['cinjenice'])} činjenica i persona")
    print("\nStara kolona skriveni_detalji je netaknuta i služi kao zaštita.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--upisi", action="store_true", help="upiši u bazu")
    ap.add_argument("--pregled", action="store_true", help="samo ispiši")
    a = ap.parse_args()
    if a.upisi:
        upisi()
    elif a.pregled:
        pregled()
    else:
        ap.print_help()
        sys.exit(1)
