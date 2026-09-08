"""Ugradjeni scenariji + oni iz baze.

Scenariji iz Supabasea nadjacavaju ugradjene ako dijele isti id.
"""
from baza import _ucitaj_db_scenarije

SCENARIJI = {
    "scenarij_1": {
        "naziv": "Scenarij 1 — Trudnica i topikalni kortikosteroidi",
        "ime": "Lejla",
        "godine": 18,
        "tegoba": "svrbež i peckanje kože na grudima, dolazi po još Clobetasol kremu",
        "terapija": "vitamini za trudnoću (33. sedmica trudnoće, prva trudnoća)",
        "skriveni_detalji": (
            "već 6 mjeseci koristi Zalim losion i Clobetasol 0.05% kremu zajedno svakodnevno; "
            "na koži su se pojavile strije i sjajne mrlje koje pripisuje trudnoći; "
            "nije bila kod ljekara, uzela preparate po preporuci komšinice"
        ),
        "crvene_zastavice": (
            "Clobetasol 0.05% kontraindiciran u trudnoći; "
            "Zalim losion (fenol) toksičan u trudnoći; "
            "6 mjeseci primjene = aktivne nuspojave; hitno uputiti ginekologu i dermatologu"
        ),
        "ocekivano": (
            "Pita o trudnoći i gestacijskoj sedmici; pita šta već koristi i koliko dugo; "
            "prepoznaje Clobetasol kao superpotentni TC kontraindiciran u trudnoći; "
            "odbija izdati bez recepta; savjetuje prekid oba preparata i hitnu posjetu ljekaru."
        ),
        "pocetna_poruka": "Dobro jutro, trebala bih još jednu Clobetasol kremu, ponestaje mi.",
        "rubrika": """Ocijeni po ovim kategorijama (svaka 0-10):

ANAMNEZA (tezina 0.4): pitao trajanje tegobe(2), sta koristi i koliko dugo(2), trudnocu/stanja(2), alergije(2), prepoznao zastavice(2)
KAZNA: bez pitanja o trudnoci max 4/10; bez pitanja sta koristi max 6/10

KOMUNIKACIJA (tezina 0.3): jezik laika(2), empatija bez osudjivanja(2), provjerio razumijevanje(2), strukturisan razgovor(2), jasna poruka(2)

SIGURNOST (tezina 0.3): odbio Clobetasol bez recepta(3), savjetovao prekid oba preparata(3), nije predlozio zamjensku terapiju(2), uputio ljekaru(2)
KAZNA: dao kortikosteroid trudnici = 0/10 za Sigurnost""",
    },
    "scenarij_2": {
        "naziv": "Scenarij 2 — Palpitacije i biljni dodatak prehrani",
        "ime": "Amra",
        "godine": 33,
        "tegoba": "epizode lupanja srca koje traju već nekoliko dana, došla po nešto za smirenje",
        "terapija": "od prije 3 mjeseca koristi lijekove na recept, kvetiapin 100 mg i sertralin 50 mg",
        "skriveni_detalji": (
            "Ima bračne probleme i osjećaj potištenosti koji traje oko mjesec dana; "
            "prije tri sedmice počela uzimati biljni dodatak prehrani u kapsulama koji joj je preporučila prijateljica "
            "(na kutiji piše da je biljka sa žutim cvijetom, uzima 300 mg dnevno); "
            "od prošle sedmice ima znojenje, nesanicu i česte epizode lupanja srca, "
            "i u mirovanju i pri naporu, traju manje od minut i prestanu same; "
            "sinoć je bila na plesanju salse i na plesnom podiju joj je srce počelo jako lupati, "
            "trajalo je oko minut i uplašila se; "
            "bila je kod ljekara — na prijemu su joj izmjerili puls 150-160 otkucaja, "
            "krvni pritisak 110/68, uradili EKG koji je pokazao supraventrikularnu tahikardiju, "
            "svi laboratorijski nalazi uredni (krvna slika, biohemija, troponin negativan), "
            "uradili su ultrazvuk srca koji je bio potpuno uredan; "
            "ljekar joj je rekao da je srce strukturno zdravo i da prekine sa tim biljnim dodatkom; "
            "nije rekla ljekaru tačno šta uzima jer joj je bilo neugodno; "
            "nema bolova u grudima, nema otežanog disanja, nije se onesvijestila; "
            "ne koristi nikakve druge lijekove, ne puši, ne pije alkohol redovno"
        ),
        "crvene_zastavice": (
            "Biljni dodatak sa žutim cvijetom = kantarion (Hypericum perforatum); "
            "kantarion može izazvati supraventrikularnu tahikardiju čak i bez prethodne srčane bolesti; "
            "vremenski slijed: simptomi počeli 3 sedmice nakon početka uzimanja; "
            "kantarion je induktor CYP 3A4 enzima i može uzrokovati opasne interakcije sa mnogim lijekovima; "
            "simptomi znojenja i nesanice mogu ukazivati na serotonergičke efekte kantariona; "
            "potrebno je odmah prekinuti uzimanje dodatka i uputiti na kontrolu kod ljekara/kardiologa"
        ),
        "ocekivano": (
            "Pita kako se osjeća i koje simptome ima; pita koliko dugo traju palpitacije i kada su počele; "
            "pita da li uzima neke lijekove, dodatke prehrani ili biljne preparate; "
            "pita detalje o biljnom dodatku (šta piše na kutiji, koliko dugo ga uzima, ko joj ga je preporučio); "
            "prepoznaje vezu između biljnog dodatka (kantarion) i palpitacija; "
            "pita da li je bila kod ljekara i šta su joj rekli; "
            "savjetuje da odmah prestane uzimati biljni dodatak; "
            "objašnjava da biljni dodaci nisu bezopasni i da mogu imati ozbiljne nuspojave; "
            "uputuje na kontrolu kod kardiologa; "
            "ne preporučuje zamjenski biljni preparat za raspoloženje bez konsultacije sa ljekarom."
        ),
        "pocetna_poruka": "Dobar dan. Imate li nešto za smirenje? Srce mi lupa već danima, ne znam šta da radim.",
        "rubrika": """Ocijeni po ovim kategorijama (svaka 0-10):

ANAMNEZA (tezina 0.4): pitao koliko dugo traju simptomi i kada su poceli(2), pitao koje lijekove/dodatke prehrani koristi(2), pitao detalje o biljnom dodatku (opis, doza, trajanje)(2), pitao da li je bila kod ljekara i sta su utvrdili(2), prepoznao vezu kantarion-palpitacije(2)
KAZNA: bez pitanja o dodacima prehrani/biljnim preparatima max 3/10; bez pitanja da li je posjetila ljekara max 5/10

KOMUNIKACIJA (tezina 0.3): jezik laika bez medicinskog zargona(2), empatija i razumijevanje za strah pacijentice(2), provjerio da li je razumjela savjete(2), strukturisan razgovor sa logicnim redoslijedom pitanja(2), jasna i nedvosmislena poruka o prekidu dodatka(2)

SIGURNOST (tezina 0.3): savjetovao odmah prekid biljnog dodatka(3), objasnio da biljni preparati mogu imati ozbiljne nuspojave(2), uputio na kontrolu kod kardiologa/ljekara(3), nije preporucio zamjenski biljni preparat bez konsultacije sa ljekarom(2)
KAZNA: preporucio nastavak uzimanja biljnog dodatka = 0/10 za Sigurnost; preporucio drugi biljni lijek za raspolozenje bez upucivanja ljekaru = max 3/10 za Sigurnost""",
    },
}

# ─── AI ───────────────────────────────────────────────────────────────────────
SCENARIJI.update(_ucitaj_db_scenarije())
