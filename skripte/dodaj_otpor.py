"""Upisuje prigovore i vidljive znakove u scenarije (F4).

    python skripte/dodaj_otpor.py --pregled
    python skripte/dodaj_otpor.py --upisi

Prigovori su iz Semirove liste od 8. 9. 2026, raspoređeni po slučajevima kojima
pripadaju. Univerzalni prigovori (3, 5, 11) žive u priručniku i ne ponavljaju se
ovdje.

Svaki prigovor ima uslov popuštanja — šta farmaceut mora reći da ga pacijent
povuče. Bez toga je prigovor samo prepreka; s njim je vježba, jer polaznik ima
šta naučiti iz toga kako ga je skinuo.

prag_povjerenja: pacijent popušta tek kad je uslov ispunjen I povjerenje toliko.
fatalno_ako_izda: prigovor koji se NIKAD ne popušta — izdavanje je greška.
"""
import argparse
import os
import sys

OTPOR = {
    # ── Lejla, 18, trudnica ─────────────────────────────────────────────────
    "scenarij_1": {
        "vidljivi_znakovi": (
            "vidno je trudna; povremeno se počeše po grudima kroz odjeću; "
            "djeluje nelagodno kad se spomene ljekar"
        ),
        "otpor": [
            {"id": "vec_koristim", "redoslijed": 1,
             "replika": "Ma nemojte mi to objašnjavati, ja to već koristim mjesecima i dobro mi je.",
             "uslov_popustanja": "prizna joj da joj je krema pomogla prije nego uvede novi podatak, "
                                 "umjesto da odmah kaže da griješi",
             "prag_povjerenja": 4, "kriterij": "empatija bez osuđivanja"},
            {"id": "komsinica_ista", "redoslijed": 2,
             "replika": "Komšinica je koristila istu kremu i njoj je odmah pomoglo. Dajte mi isto.",
             "uslov_popustanja": "objasni zašto isti lijek nije isti za dvije osobe, konkretno na "
                                 "njenoj trudnoći, a ne uopšteno",
             "prag_povjerenja": 5, "kriterij": "individualizacija terapije"},
            {"id": "niste_ljekar", "redoslijed": 3,
             "replika": "Vi niste ljekar, molim Vas da mi date ono što sam tražila.",
             "uslov_popustanja": "mirno imenuje svoju ulogu i odgovornost, bez izvinjavanja i bez "
                                 "nadmenosti, i kaže šta konkretno smije uraditi za nju",
             "prag_povjerenja": 5, "kriterij": "granice profesije"},
            {"id": "izdaj_bez_recepta", "redoslijed": 4,
             "replika": "Pa dajte mi barem jednu tubu dok ne odem ljekaru, molim Vas.",
             "uslov_popustanja": None, "fatalno_ako_izda": True,
             "kriterij": "sigurnost"},
        ],
    },

    # ── Amra, 33, kantarion ─────────────────────────────────────────────────
    "scenarij_2": {
        "vidljivi_znakovi": (
            "djeluje nervozno, povremeno stavi ruku na grudi; gleda oko sebe ko je u redu iza nje"
        ),
        "otpor": [
            {"id": "biljno_je_bezopasno", "redoslijed": 1,
             "replika": "Ne želim ja lijekove, to je biljno, prirodno — kako to može škoditi?",
             "uslov_popustanja": "prizna da biljno nije isto što i bezopasno i navede konkretnu "
                                 "interakciju s njenom terapijom, a ne samo kaže da 'to ne valja'",
             "prag_povjerenja": 5, "kriterij": "sigurnost, jezik laika"},
            {"id": "internet_jetra", "redoslijed": 2,
             "replika": "Na internetu sam pročitala da baš ti lijekovi za smirenje štete jetri. Je li to tačno?",
             "uslov_popustanja": "ne ismije izvor, razdvoji tačno od netačnog i kaže šta konkretno "
                                 "da prati",
             "prag_povjerenja": 4, "kriterij": "dezinformacije"},
            {"id": "dva_dana", "redoslijed": 3,
             "replika": "A ako mi ne prođe za dva dana, mogu li onda uzeti nešto jače?",
             "uslov_popustanja": "dâ jasan rok i jasnu granicu — šta smije, šta ne smije i kada se "
                                 "mora javiti — umjesto neodređenog 'vidjećemo'",
             "prag_povjerenja": 4, "kriterij": "sigurnosna mreža"},
        ],
    },

    # ── Fadila, 65, glaukom ─────────────────────────────────────────────────
    "scenarij_3": {
        "vidljivi_znakovi": (
            "žmirka na jakom svjetlu i zaklanja oči rukom, sve češće kako razgovor traje; "
            "oči su joj crvene; povremeno se pridržava za pult; djeluje iscrpljeno"
        ),
        "otpor": [
            {"id": "nemam_vremena", "redoslijed": 1,
             "replika": "Nemam ja vremena čekati po ambulantama, samo mi recite šta da uzmem.",
             "uslov_popustanja": "u dvije rečenice kaže jedno pitanje koje mora postaviti i zašto, "
                                 "umjesto da nastavi ispitivati kao da nije čuo",
             "prag_povjerenja": 4, "kriterij": "trijaža pod pritiskom"},
            {"id": "gripa_prolazi", "redoslijed": 2,
             "replika": "Ma to je od gripe, proći će samo. Neću ja ljekaru zbog gripe.",
             "uslov_popustanja": "jasno razdvoji simptome gripe od onoga što nije gripa i kaže "
                                 "konkretno šta se rizikuje čekanjem",
             "prag_povjerenja": 5, "kriterij": "prepoznavanje hitnosti"},
            {"id": "kapi_za_oci", "redoslijed": 3,
             "replika": "Dajte mi bar one kapi za crvene oči, to ne može škoditi.",
             "uslov_popustanja": None, "fatalno_ako_izda": True,
             "kriterij": "sigurnost"},
            {"id": "preskupo", "redoslijed": 4,
             "replika": "A koliko to košta? Ja sam penzionerka, nemam ja para bacati.",
             "uslov_popustanja": "pita koliki joj je budžet ili ponudi jeftiniju opciju i objasni "
                                 "šta se time gubi",
             "prag_povjerenja": 4, "kriterij": "pristupačnost"},
        ],
    },

    # ── Stefan, 71, Tribulus ────────────────────────────────────────────────
    "scenarij_4": {
        "vidljivi_znakovi": (
            "hoda ukočeno i sporo se okreće; oslanja se na pult obje ruke; "
            "povremeno protrlja natkoljenice; gleda na sat"
        ),
        "otpor": [
            {"id": "od_bicikla_je", "redoslijed": 1,
             "replika": "Ma to je od bicikla, šta ću, star sam. Dajte mi neku mast pa idem.",
             "uslov_popustanja": "objasni zašto bol po cijelom tijelu ne odgovara naporu i traži "
                                 "konkretan podatak umjesto da samo ponovi da je zabrinut",
             "prag_povjerenja": 4, "kriterij": "kritičko razmišljanje"},
            {"id": "toliko_tableta", "redoslijed": 2,
             "replika": "Ne mogu ja svaki dan piti toliko tableta. Dajte mi nešto što djeluje odmah.",
             "uslov_popustanja": "pita šta mu je konkretno teško — broj, veličina, raspored — i "
                                 "predloži pojednostavljenje, umjesto da ponovi uputu",
             "prag_povjerenja": 4, "kriterij": "adherencija"},
            {"id": "doktor_rekao_dva", "redoslijed": 3,
             "replika": "Doktor mi je rekao da uzimam dva puta dnevno, a vi sad nešto drugo govorite.",
             "uslov_popustanja": "ne ospori ljekara pred njim, nego provjeri šta tačno piše i "
                                 "predloži zajedničku provjeru",
             "prag_povjerenja": 5, "kriterij": "kolegijalnost, sigurnost doze"},
            {"id": "zamjena", "redoslijed": 4,
             "replika": "Neću ja zamjenu, hoću isključivo ono što mi je doktor propisao.",
             "uslov_popustanja": "objasni šta generik jeste ili prihvati odbijanje bez pritiska, "
                                 "uz ponudu da nazove ljekara",
             "prag_povjerenja": 4, "kriterij": "generička zamjena"},
            {"id": "daj_analgetik", "redoslijed": 5,
             "replika": "Pa dajte mi bar nešto protiv bolova dok ne odem, ne mogu ovako.",
             "uslov_popustanja": None, "fatalno_ako_izda": True,
             "kriterij": "sigurnost"},
        ],
    },
}


def pregled():
    for sid, p in OTPOR.items():
        fatalnih = sum(1 for o in p["otpor"] if o.get("fatalno_ako_izda"))
        print(f"\n{sid}: {len(p['otpor'])} prigovora ({fatalnih} bez popuštanja)")
        for o in p["otpor"]:
            oznaka = "  [NE POPUŠTA]" if o.get("fatalno_ako_izda") else \
                     f"  [povjerenje >= {o.get('prag_povjerenja')}]"
            print(f"  {o['redoslijed']}. {o['replika'][:66]}...{oznaka}")
        print(f"  vidljivo: {p['vidljivi_znakovi'][:70]}...")


def upisi():
    from dotenv import load_dotenv
    from supabase import create_client
    load_dotenv(".env")
    db = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    postojeci = {r["id"] for r in db.table("scenarios").select("id").execute().data or []}
    for sid, p in OTPOR.items():
        if sid not in postojeci:
            print(f"  {sid}: nema ga u bazi, preskačem")
            continue
        db.table("scenarios").update({
            "otpor": p["otpor"],
            "vidljivi_znakovi": p["vidljivi_znakovi"],
        }).eq("id", sid).execute()
        print(f"  {sid}: upisano {len(p['otpor'])} prigovora i vidljivi znakovi")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--upisi", action="store_true")
    ap.add_argument("--pregled", action="store_true")
    a = ap.parse_args()
    if a.upisi:
        upisi()
    elif a.pregled:
        pregled()
    else:
        ap.print_help()
        sys.exit(1)
