"""Komunikator API — tanak sloj oko istih modula koje koristi Streamlit.

Pokretanje iz korijena repoa:
    venv/Scripts/python -m uvicorn api.main:app --port 8000

Logika (pacijent, ocjenjivač, rubrika, stanje) se ovdje NE piše ponovo — sve
ide kroz motor/baza/scenariji. Ovaj fajl radi samo četiri stvari:
  1. prijava i token, uz provjeru odobrenja, suspenzije i roka članarine na
     SVAKOM zahtjevu;
  2. razgovor potez po potez, sa stanjem u attempts_progress (kao Streamlit);
  3. tajmer ispita na serveru, iz zadnji_potez_vrijeme;
  4. propušta prema telefonu samo polja iz api/javno.py.

Odluke 15.10.2026: svaki slučaj se igra jednom (ispit), vježba ostaje
isključena, nema kvote osim postojećeg dnevnog limita poruka.
"""
import json
import os
import queue
import threading
import time
import urllib.request
from contextvars import copy_context
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from konfig import DNEVNI_LIMIT_PORUKA, MAX_POTEZA, postavi_aktivnog, zabiljezi_gresku
from baza import (ISPIT, _ucitaj_objave, db_korisnici_za_obavijest, db_korisnik, db_log_upotrebu,
                  db_oznaci_obavijest, db_postavi_obavijesti, db_scenariji_obavijesti, db_login, db_leaderboard,
                  db_moji_rezultati, db_obrisi_napredak, db_obrisi_sve_podatke, db_pokusaj,
                  db_poruka_danas, db_posalji_zalbu, db_registruj, db_spremi_napredak,
                  db_ucitaj_napredak, db_vec_uradio, db_zavrseni_scenariji, nadimak_slobodan,
                  provjeri_lozinku)
from posta import email_novi_slucaj, posalji_emailove_skupno
from motor import ocijeni_razgovor, pozovi_pacijenta_stream, zatvori_razgovor
from scenariji import SCENARIJI, osvjezi_scenarije

from api.admin import napravi_ruter
from api.javno import (TAJMER_SEKUNDI, clanarina_vazi, javna_ljestvica, javni_korisnik,
                       javni_rezultat, javni_scenarij, javno_stanje, primijeni_tajmer)

# Tajna za potpis tokena. Bez nje API ne smije krenuti: zadana vrijednost bi
# značila da svako može iskovati token za bilo koji email.
TAJNA = os.environ.get("KOMUNIKATOR_TAJNA", "")
TOKEN_DANA = 30

DOZVOLJENI_IZVORI = [
    "https://simulator.farmaceutupraksi.ba",
    "https://komunikator-epc.web.app",
    "http://localhost:5173",
    "http://localhost:4317",
]

app = FastAPI(title="Komunikator API", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CORSMiddleware, allow_origins=DOZVOLJENI_IZVORI,
                   allow_methods=["GET", "POST", "DELETE"],
                   allow_headers=["Authorization", "Content-Type"])

# Jedan potez po korisniku u isto vrijeme. Dvostruki klik bi inače poslao dvije
# poruke nad istim stanjem, pa bi jedna pregazila drugu u attempts_progress.
# Radi unutar jednog procesa — Cloud Run zato ide s max 1 instancom.
_brave = {}
_brava_brava = threading.Lock()


def _brava(email):
    with _brava_brava:
        return _brave.setdefault(email, threading.Lock())


# ─── Prijava ─────────────────────────────────────────────────────────────────

def napravi_token(email):
    if not TAJNA:
        raise HTTPException(500, "Server nije podešen (KOMUNIKATOR_TAJNA).")
    istice = datetime.now(timezone.utc) + timedelta(days=TOKEN_DANA)
    return jwt.encode({"sub": email, "exp": istice}, TAJNA, algorithm="HS256")


def provjeri_pristup(k):
    """Ista pravila kao db_login, plus rok članarine. Vraća poruku ili None."""
    if not k:
        return "Nalog ne postoji."
    if k.get("suspended"):
        return "Vaš nalog je privremeno suspendovan. Kontaktirajte administratora."
    if not k.get("approved"):
        return "Vaš zahtjev čeka odobrenje administratora."
    if not clanarina_vazi(k):
        return ("Komunikator je dostupan članovima s plaćenom članarinom. "
                "Članarina nije pronađena ili je istekla.")
    return None


def korisnik(authorization: str = Header(default="")):
    """Zavisnost za svaki zaštićeni endpoint: token → svjež red iz baze."""
    if not TAJNA:
        raise HTTPException(500, "Server nije podešen (KOMUNIKATOR_TAJNA).")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        email = jwt.decode(token, TAJNA, algorithms=["HS256"])["sub"]
    except Exception:
        raise HTTPException(401, "Prijavite se ponovo.")
    k = db_korisnik(email)
    poruka = provjeri_pristup(k)
    if poruka:
        raise HTTPException(403, poruka)
    postavi_aktivnog(k["email"])
    return k


class Prijava(BaseModel):
    email: str
    lozinka: str


class Zahtjev(BaseModel):
    ime: str
    email: str
    institucija: str = ""
    nadimak: str = ""
    lozinka: str


@app.post("/prijava")
def prijava(p: Prijava):
    k, poruka = db_login(p.email, p.lozinka)
    if not k:
        raise HTTPException(401, poruka)
    if not clanarina_vazi(k):
        raise HTTPException(403, provjeri_pristup(k))
    return {"token": napravi_token(k["email"]), "korisnik": javni_korisnik(k)}


@app.post("/zahtjev")
def zahtjev(z: Zahtjev):
    """Zahtjev za pristup. Nalog nastaje s approved=false; pušta ga samo admin."""
    if not z.ime.strip() or not z.email.strip() or not z.lozinka:
        raise HTTPException(400, "Popunite sva polja.")
    n = z.nadimak.strip()
    if n and not (3 <= len(n) <= 24):
        raise HTTPException(400, "Nadimak mora imati između 3 i 24 znaka.")
    if n and "@" in n:
        raise HTTPException(400, "Nadimak ne smije sadržavati email adresu.")
    if n and not nadimak_slobodan(n, z.email):
        raise HTTPException(400, "Taj nadimak je već zauzet. Izaberite drugi.")
    if len(z.lozinka) < 6:
        raise HTTPException(400, "Lozinka mora imati najmanje 6 znakova.")
    ok, poruka = db_registruj(z.email, z.lozinka, z.ime, z.institucija, n)
    if not ok:
        raise HTTPException(400, poruka)
    return {"poruka": "Zahtjev je primljen. Javićemo vam se kad administrator odobri pristup."}


@app.get("/ja")
def ja(k=Depends(korisnik)):
    return javni_korisnik(k)


# ─── Scenariji ───────────────────────────────────────────────────────────────

def _aktivni_scenarij(sid):
    osvjezi_scenarije()
    sc = SCENARIJI.get(sid)
    if not sc or not sc.get("aktivan", True):
        raise HTTPException(404, "Scenarij nije dostupan.")
    return sc


@app.get("/scenariji")
def scenariji(k=Depends(korisnik)):
    osvjezi_scenarije()
    zavrseni = db_zavrseni_scenariji(k["email"])
    lista = [javni_scenarij(sid, sc, sid in zavrseni)
             for sid, sc in SCENARIJI.items() if sc.get("aktivan", True)]
    # Nezavršeni prvi, kao u Streamlitu.
    lista.sort(key=lambda s: s["zavrsen"])
    return {"scenariji": lista, "max_poteza": MAX_POTEZA, "sekundi_po_odgovoru": TAJMER_SEKUNDI}


def _ucitaj(email, sid):
    """Razgovor u toku iz baze, s vremenom zadnjeg poteza kao brojem sekundi."""
    s = db_ucitaj_napredak(email, sid, ISPIT)
    if not s or not s.get("poruke_prikaz"):
        return None
    z = s.get("zadnji_potez_vrijeme")
    if isinstance(z, str):
        try:
            s["zadnji_potez_vrijeme"] = datetime.fromisoformat(z.replace("Z", "+00:00")).timestamp()
        except ValueError:
            s["zadnji_potez_vrijeme"] = None
    return s


@app.post("/scenariji/{sid}/pocni")
def pocni(sid: str, k=Depends(korisnik)):
    """Otvara razgovor ili vraća prekinuti. Tajmer kreće iznova pri svakom ulasku,
    kao u Streamlitu: vrijeme provedeno van aplikacije se ne računa."""
    sc = _aktivni_scenarij(sid)
    email = k["email"]
    postavi_aktivnog(email, sid)
    if db_vec_uradio(email, sid):
        raise HTTPException(409, "Ovaj slučaj ste već odigrali. Svaki se igra jednom.")
    with _brava(email):
        stanje = _ucitaj(email, sid)
        vraceno = stanje is not None
        if not stanje:
            prva = sc["pocetna_poruka"]
            stanje = {"poruke_api": [{"role": "assistant", "content": prva}],
                      "poruke_prikaz": [{"role": "assistant", "content": prva}],
                      "stanja": [], "zadnje_stanje": None,
                      "broj_poteza": 0, "izgubljeno_ukupno": 0}
            db_log_upotrebu("start", sid)
        stanje["zadnji_potez_vrijeme"] = time.time()
        db_spremi_napredak(email, sid, stanje, ISPIT)
    return {"scenarij": javni_scenarij(sid, sc), "vraceno": vraceno,
            "razgovor": javno_stanje(stanje, MAX_POTEZA)}


def _zavrsi(stanje, sc, sid, email):
    """Završna replika pacijenta pa ocjena. Vraća rezultat ili None.

    Pri neuspjehu ocjene razgovor ostaje sačuvan, pa polaznik može ponoviti
    završetak — ocjena se plaća, a razgovor se ne smije izgubiti.
    """
    # SSE tok se izvršava u više niti (svaki korak generatora u svojoj), pa se
    # kontekst postavlja iznova — inače bi potrošnja završne replike i ocjene
    # otišla u usage_log bez emaila i scenarija.
    postavi_aktivnog(email, sid)
    if stanje["poruke_prikaz"] and not stanje.get("zatvoren"):
        zavrsna, novo, sirovi = zatvori_razgovor(stanje["poruke_api"], sc, stanje.get("zadnje_stanje"))
        stanje["zatvoren"] = True
        if zavrsna:
            stanje["poruke_prikaz"].append({"role": "assistant", "content": zavrsna})
            stanje["poruke_api"].append({"role": "assistant", "content": sirovi or zavrsna})
            if novo:
                stanje["stanja"].append(novo)
                stanje["zadnje_stanje"] = novo
    rezultat = ocijeni_razgovor(stanje, sc, sid, ISPIT, email)
    if rezultat:
        db_obrisi_napredak(email, sid, ISPIT)
        javi_pharma_questu(email, rezultat, sc, sid)
    else:
        db_spremi_napredak(email, sid, stanje, ISPIT)
    return rezultat


# ─── Most prema Pharma Questu ────────────────────────────────────────────────
# Odluka 15.10.2026: ocjena × 100 XP, jednom mjesečno (prvi završeni ispit u
# mjesecu). Pravilo „jednom" čuva PQ (komunikatorIsplate), pa se ovdje šalje
# svaki završeni ispit — PQ sam odbije drugi u istom mjesecu.
PQ_NAGRADA_URL = os.environ.get(
    "PQ_NAGRADA_URL", "https://europe-west1-pharma-quest-8c6cc.cloudfunctions.net/komunikatorNagrada")
PQ_NAGRADA_TAJNA = os.environ.get("PQ_NAGRADA_TAJNA", "")


def javi_pharma_questu(email, rezultat, sc, sid):
    """Bez pada: ocjena je već upisana, pa kvar PQ-a ne smije srušiti odgovor.

    Sinhrono i s kratkim rokom — Cloud Run poslije odgovora oduzima procesor,
    pa bi nit u pozadini mogla nikad ne završiti.
    """
    if not PQ_NAGRADA_TAJNA:
        return None
    try:
        tijelo = json.dumps({
            "email": email, "ocjena": float(rezultat.get("ukupna_ocjena") or 0),
            "naziv": (sc or {}).get("naziv", ""), "pokusajId": sid,
            "zavrseno": datetime.now(timezone.utc).isoformat(),
        }).encode("utf-8")
        zahtjev = urllib.request.Request(
            PQ_NAGRADA_URL, data=tijelo, method="POST",
            headers={"Content-Type": "application/json", "X-Komunikator-Tajna": PQ_NAGRADA_TAJNA})
        with urllib.request.urlopen(zahtjev, timeout=5) as odg:
            return json.loads(odg.read().decode("utf-8") or "{}")
    except Exception as e:
        zabiljezi_gresku(e)
        return None


def _sse(dogadjaj, podaci):
    return f"event: {dogadjaj}\ndata: {json.dumps(podaci, ensure_ascii=False)}\n\n"


class Poruka(BaseModel):
    tekst: str


@app.post("/scenariji/{sid}/poruka")
def poruka(sid: str, p: Poruka, k=Depends(korisnik)):
    """Jedan potez farmaceuta. Odgovor je SSE tok:
    `dio` (replika do sada, bez bloka stanja) … pa `stanje` ili `rezultat`."""
    sc = _aktivni_scenarij(sid)
    email = k["email"]
    tekst = (p.tekst or "").strip()
    if not tekst:
        raise HTTPException(400, "Poruka je prazna.")
    if len(tekst) > 2000:
        raise HTTPException(400, "Poruka je preduga.")
    if db_vec_uradio(email, sid):
        raise HTTPException(409, "Ovaj slučaj ste već odigrali.")
    brava = _brava(email)
    if not brava.acquire(blocking=False):
        raise HTTPException(429, "Prethodna poruka se još obrađuje.")

    def tok():
        try:
            postavi_aktivnog(email, sid)
            stanje = _ucitaj(email, sid)
            if not stanje:
                yield _sse("greska", {"poruka": "Razgovor nije započet."})
                return
            sad = time.time()

            # Dnevni limit poruka ostaje kao zaštita troška.
            if db_poruka_danas(email) >= DNEVNI_LIMIT_PORUKA:
                if stanje["broj_poteza"] > 0:
                    rez = _zavrsi(stanje, sc, sid, email)
                    yield _sse("rezultat" if rez else "greska",
                               javni_rezultat(rez, stanje.get("stanja"), sc) if rez
                               else {"poruka": "Ocjena nije uspjela. Pokušajte završiti ponovo."})
                else:
                    yield _sse("greska", {"poruka": "Dostigli ste dnevni limit poruka. Nastavite sutra."})
                return

            primijeni_tajmer(stanje, MAX_POTEZA, sad)
            if stanje["broj_poteza"] >= MAX_POTEZA:
                yield _sse("info", {"poruka": "Vrijeme je isteklo za sve pokušaje. Razgovor se ocjenjuje."})
                rez = _zavrsi(stanje, sc, sid, email)
                yield (_sse("rezultat", javni_rezultat(rez, stanje.get("stanja"), sc)) if rez
                       else _sse("greska", {"poruka": "Ocjena nije uspjela. Pokušajte završiti ponovo."}))
                return

            stanje["poruke_prikaz"].append({"role": "user", "content": tekst})
            stanje["poruke_api"].append({"role": "user", "content": tekst})
            stanje["broj_poteza"] += 1
            stanje["zadnji_potez_vrijeme"] = sad

            if stanje["broj_poteza"] >= MAX_POTEZA:
                db_spremi_napredak(email, sid, stanje, ISPIT)
                yield _sse("info", {"poruka": "Iskoristili ste sve unose. Razgovor se ocjenjuje."})
                rez = _zavrsi(stanje, sc, sid, email)
                yield (_sse("rezultat", javni_rezultat(rez, stanje.get("stanja"), sc)) if rez
                       else _sse("greska", {"poruka": "Ocjena nije uspjela. Pokušajte završiti ponovo."}))
                return

            # Pacijent odgovara u zasebnoj niti; dijelovi stižu kroz red.
            red = queue.Queue()
            ishod = {}

            def pacijent():
                try:
                    ishod["v"] = pozovi_pacijenta_stream(
                        stanje["poruke_api"], sc, stanje.get("zadnje_stanje"),
                        lambda dio: red.put(("dio", dio)))
                except Exception as e:      # pozovi_pacijenta_stream sam pada na obični poziv
                    ishod["e"] = e
                finally:
                    red.put(("kraj", None))

            threading.Thread(target=copy_context().run, args=(pacijent,), daemon=True).start()
            while True:
                vrsta, dio = red.get()
                if vrsta == "kraj":
                    break
                yield _sse("dio", {"tekst": dio})

            if "e" in ishod:
                zabiljezi_gresku(ishod["e"])
                # Poruka farmaceuta se vraća, a potez se ne troši: kvar nije njegov.
                yield _sse("greska", {"poruka": "Pacijent trenutno ne može odgovoriti. Pošaljite ponovo."})
                return
            odg, novo, sirovi = ishod["v"]
            stanje["poruke_prikaz"].append({"role": "assistant", "content": odg})
            # U historiju ide SIROVI odgovor, s blokom stanja (vidi app.py).
            stanje["poruke_api"].append({"role": "assistant", "content": sirovi or odg})
            if novo:
                stanje["stanja"].append(novo)
                stanje["zadnje_stanje"] = novo
            db_spremi_napredak(email, sid, stanje, ISPIT)
            yield _sse("stanje", javno_stanje(stanje, MAX_POTEZA))
        except Exception as e:
            zabiljezi_gresku(e)
            yield _sse("greska", {"poruka": "Greška na serveru. Pokušajte ponovo."})
        finally:
            brava.release()

    return StreamingResponse(tok(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/scenariji/{sid}/zavrsi")
def zavrsi(sid: str, k=Depends(korisnik)):
    """Polaznik sam završava (od drugog poteza naviše, kao u Streamlitu)."""
    sc = _aktivni_scenarij(sid)
    email = k["email"]
    postavi_aktivnog(email, sid)
    if db_vec_uradio(email, sid):
        raise HTTPException(409, "Ovaj slučaj je već ocijenjen.")
    with _brava(email):
        stanje = _ucitaj(email, sid)
        if not stanje:
            raise HTTPException(400, "Razgovor nije započet.")
        if stanje["broj_poteza"] < 2:
            raise HTTPException(400, "Razgovor se može završiti tek poslije drugog unosa.")
        rez = _zavrsi(stanje, sc, sid, email)
    if not rez:
        raise HTTPException(502, "Ocjena nije uspjela. Razgovor je sačuvan — pokušajte ponovo.")
    return javni_rezultat(rez, stanje.get("stanja"), sc)


@app.post("/scenariji/{sid}/istek")
def istek(sid: str, k=Depends(korisnik)):
    """Telefon javlja da je, po njegovom satu, isteklo vrijeme za sve unose.

    Sudi server: obračuna tajmer i ocjenjuje samo ako stvarno nema više unosa;
    inače vraća trenutni razgovor. Ništa se ne upisuje u razgovor — ranije bi
    telefon morao poslati lažnu poruku, a ona bi ušla u transkript kad god se
    satovi razilaze.
    """
    sc = _aktivni_scenarij(sid)
    email = k["email"]
    postavi_aktivnog(email, sid)
    if db_vec_uradio(email, sid):
        raise HTTPException(409, "Ovaj slučaj je već ocijenjen.")
    with _brava(email):
        stanje = _ucitaj(email, sid)
        if not stanje:
            raise HTTPException(400, "Razgovor nije započet.")
        primijeni_tajmer(stanje, MAX_POTEZA, time.time())
        if stanje["broj_poteza"] < MAX_POTEZA:
            db_spremi_napredak(email, sid, stanje, ISPIT)
            return {"razgovor": javno_stanje(stanje, MAX_POTEZA)}
        rez = _zavrsi(stanje, sc, sid, email)
    if not rez:
        raise HTTPException(502, "Ocjena nije uspjela. Razgovor je sačuvan — pokušajte ponovo.")
    return {"rezultat": javni_rezultat(rez, stanje.get("stanja"), sc)}


@app.get("/scenariji/{sid}/rezultat")
def rezultat(sid: str, k=Depends(korisnik)):
    osvjezi_scenarije()
    sc = SCENARIJI.get(sid) or {}
    pok = db_pokusaj(k["email"], sid)
    if not pok:
        raise HTTPException(404, "Za ovaj slučaj nema ocjene.")
    try:
        rez = json.loads(pok.get("result_json") or "{}")
    except ValueError:
        rez = {}
    javno = javni_rezultat(rez, pok.get("stanje_json") or [], sc)
    javno.update({
        "pokusaj_id": pok["id"],
        "transkript": pok.get("transcript") or "",
        "zavrseno": pok.get("completed_at"),
        "prigovor": {"status": pok.get("appeal_status"), "tekst": pok.get("appeal_text"),
                     "odgovor": pok.get("appeal_response")},
    })
    return javno


# ─── Ljestvica, moji rezultati, prigovor, brisanje naloga ────────────────────

@app.get("/ljestvica")
def ljestvica(period: str = "sve", k=Depends(korisnik)):
    if period not in ("sedmicno", "mjesecno", "godisnje", "sve"):
        raise HTTPException(400, "Nepoznat period.")
    return {"ljestvica": javna_ljestvica(db_leaderboard(period))}


@app.get("/moji-rezultati")
def moji_rezultati(k=Depends(korisnik)):
    osvjezi_scenarije()
    return {"rezultati": [{
        "pokusaj_id": r["id"], "scenarij_id": r["scenario_id"],
        "naziv": (SCENARIJI.get(r["scenario_id"]) or {}).get("naziv", r["scenario_id"]),
        "ocjena": float(r.get("score") or 0), "zavrseno": r.get("completed_at"),
        "prigovor": r.get("appeal_status"),
    } for r in db_moji_rezultati(k["email"]) if r.get("mode", ISPIT) == ISPIT]}


class Prigovor(BaseModel):
    pokusaj_id: str
    tekst: str


@app.post("/prigovor")
def prigovor(p: Prigovor, k=Depends(korisnik)):
    # db_posalji_zalbu mijenja red po id-u, pa se vlasništvo provjerava ovdje.
    if not any(r["id"] == p.pokusaj_id for r in db_moji_rezultati(k["email"])):
        raise HTTPException(404, "Pokušaj nije pronađen.")
    if len(p.tekst.strip()) < 10:
        raise HTTPException(400, "Opišite prigovor u bar jednoj rečenici.")
    ok, poruka_ = db_posalji_zalbu(p.pokusaj_id, p.tekst)
    if not ok:
        raise HTTPException(500, poruka_)
    return {"poruka": "Prigovor je poslan."}


class Brisanje(BaseModel):
    lozinka: str


@app.delete("/nalog")
def obrisi_nalog(b: Brisanje, k=Depends(korisnik)):
    tacna, _ = provjeri_lozinku(b.lozinka, k.get("password_hash"))
    if not tacna:
        raise HTTPException(403, "Pogrešna lozinka.")
    if not db_obrisi_sve_podatke(k["email"]):
        raise HTTPException(500, "Brisanje nije uspjelo. Kontaktirajte administratora.")
    return {"poruka": "Nalog i svi podaci su obrisani."}


# ─── Obavijesti o novom slučaju ──────────────────────────────────────────────

class Obavijesti(BaseModel):
    email: bool


@app.post("/ja/obavijesti")
def postavi_obavijesti(o: Obavijesti, k=Depends(korisnik)):
    if not db_postavi_obavijesti(k["email"], o.email):
        raise HTTPException(500, "Postavka nije sačuvana. Pokušajte ponovo.")
    return {"obavijesti_email": o.email}


def admin(k=Depends(korisnik)):
    if k.get("role") != "admin":
        raise HTTPException(403, "Samo za administratora.")
    return k


def _primaoci():
    """Članovi kojima ide obavijest: odobreni, nesuspendovani, s važećom
    članarinom, bez isključenih obavijesti. Admin nalozi se preskaču."""
    return [u for u in db_korisnici_za_obavijest()
            if u.get("role") != "admin" and clanarina_vazi(u)]


@app.get("/admin/obavijesti")
def admin_obavijesti(k=Depends(admin)):
    osvjezi_scenarije()
    poslano = db_scenariji_obavijesti()
    return {
        "primalaca": len(_primaoci()),
        "slucajevi": [{"id": sid, "naziv": sc.get("naziv", ""), "aktivan": bool(sc.get("aktivan", True)),
                       "obavijest_poslana": poslano.get(sid)}
                      for sid, sc in SCENARIJI.items()],
    }


@app.get("/admin/obavijesti/{sid}")
def admin_pregled_obavijesti(sid: str, k=Depends(admin)):
    sc = _aktivni_scenarij(sid)
    naslov, html = email_novi_slucaj("Ime Prezime", sc, sid)
    return {"naslov": naslov, "html": html, "primalaca": len(_primaoci())}


class Slanje(BaseModel):
    ponovo: bool = False


@app.post("/admin/obavijesti/{sid}")
def admin_posalji_obavijest(sid: str, z: Slanje, k=Depends(admin)):
    """Šalje svakom primaocu poseban email. Dugme pritiska Semir — nikad se ne
    šalje samo od sebe pri otključavanju slučaja."""
    sc = _aktivni_scenarij(sid)
    if db_scenariji_obavijesti().get(sid) and not z.ponovo:
        raise HTTPException(409, "Obavijest za ovaj slučaj je već poslana.")
    poruke = []
    for u in _primaoci():
        naslov, html = email_novi_slucaj(u.get("full_name") or "", sc, sid)
        poruke.append({"to": u["email"], "subject": naslov, "html": html})
    if not poruke:
        raise HTTPException(400, "Nema primalaca.")
    poslano, greske = posalji_emailove_skupno(poruke)
    if poslano:
        db_oznaci_obavijest(sid, datetime.now(timezone.utc).isoformat())
    if not poslano:
        raise HTTPException(502, "Slanje nije uspjelo: " + "; ".join(greske))
    return {"poslano": poslano, "ukupno": len(poruke), "greske": greske}


# ─── Objave za članove i admin ───────────────────────────────────────────────

@app.get("/objave")
def objave(k=Depends(korisnik)):
    """Aktivne objave admina — traka na vrhu liste slučajeva (isto kao u Streamlitu)."""
    return {"objave": [{"id": o["id"], "tekst": o.get("tekst", ""), "tip": o.get("tip") or "info"}
                       for o in _ucitaj_objave()]}


app.include_router(napravi_ruter(korisnik))
