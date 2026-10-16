"""Admin u Komunikatoru — sve iz Streamlit admina osim generisanja i uređivanja
scenarija (odluka 16.10.2026: to ostaje u Streamlitu).

Logika se ne piše ponovo: iste funkcije baze (baza.py), rubrike (rubrika.py) i
pošte (posta.py) koje koristi Streamlit admin. Ovdje je samo pristup (uloga
admin, provjerena na svakom zahtjevu kroz `korisnik`) i oblik odgovora.

Email ide preko Breva (posta.py), pojedinačno. Ništa se ne šalje bez izričitog
admin poziva — nema automatskih mailova pri otključavanju slučaja.
"""
import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

import rubrika
from baza import (db, db_neodobreni_korisnici, db_objava_aktivna, db_objava_nova,
                  db_objava_obrisi, db_objave_sve, db_obrisi_sve_podatke, db_odbij_korisnika,
                  db_odobri_korisnika, db_otvorene_zalbe, db_pokusaji_korisnika,
                  db_postavi_suspenziju, db_postavi_ulogu, db_resetuj_lozinku,
                  db_restartuj_scenarij, db_rijesi_zalbu, db_scenarij_aktivan, db_statistika,
                  db_svi_korisnici, db_svi_pokusaji_export, napravi_csv)
from konfig import ADMIN_EMAIL, CIJENA_IZLAZ_USD, CIJENA_ULAZ_USD, zabiljezi_gresku
from posta import posalji_email, posalji_email_masovni, posalji_email_odobrenje
from scenariji import SCENARIJI, osvjezi_scenarije

from api.javno import clanarina_vazi


def napravi_ruter(korisnik):
    """`korisnik` je zavisnost iz api/main.py (token → svjež red iz baze)."""
    r = APIRouter(prefix="/admin")

    def admin(k=Depends(korisnik)):
        if k.get("role") != "admin":
            raise HTTPException(403, "Samo za administratora.")
        return k

    def naziv(sid):
        return (SCENARIJI.get(sid) or {}).get("naziv", sid)

    def javni_nalog(u):
        return {
            "email": u["email"], "ime": u.get("full_name") or "", "institucija": u.get("institution") or "",
            "nadimak": u.get("nadimak") or "", "uloga": u.get("role") or "korisnik",
            "suspendovan": bool(u.get("suspended")), "odobren": bool(u.get("approved")),
            "clan_do": str(u["clan_do"])[:10] if u.get("clan_do") else None,
            "clanarina_vazi": clanarina_vazi(u), "obavijesti_email": u.get("obavijesti_email", True) is not False,
            "registrovan": u.get("created_at"),
        }

    def nalog_ili_404(email):
        if not db:
            raise HTTPException(500, "Baza nije dostupna.")
        red = db.table("users").select("*").eq("email", email).execute().data
        if not red:
            raise HTTPException(404, "Nalog ne postoji.")
        return red[0]

    def zasticen(email, k):
        if email == ADMIN_EMAIL or email == k["email"]:
            raise HTTPException(400, "Ovo se ne radi nad glavnim administratorom ni nad vlastitim nalogom.")

    def postavi_clan_do(email, clan_do):
        if clan_do is not None:
            try:
                date.fromisoformat(clan_do)
            except ValueError:
                raise HTTPException(400, "Datum mora biti u obliku GGGG-MM-DD.")
        db.table("users").update({"clan_do": clan_do}).eq("email", email).execute()

    # ── Pregled: brojke za značke na tabovima ────────────────────────────────
    @r.get("/pregled")
    def pregled(k=Depends(admin)):
        return {"zahtjeva": len(db_neodobreni_korisnici()), "zalbi": len(db_otvorene_zalbe())}

    # ── Zahtjevi ─────────────────────────────────────────────────────────────
    @r.get("/zahtjevi")
    def zahtjevi(k=Depends(admin)):
        return {"zahtjevi": [javni_nalog(u) for u in db_neodobreni_korisnici()]}

    class Odobravanje(BaseModel):
        emailovi: list[str]
        clan_do: str | None = None      # rok članarine; bez njega nalog ne ulazi u Komunikator
        posalji_email: bool = True

    @r.post("/zahtjevi/odobri")
    def odobri(o: Odobravanje, k=Depends(admin)):
        if o.clan_do:
            try:      # provjera prije petlje — inače bi pola liste prošlo, pola ne
                date.fromisoformat(o.clan_do)
            except ValueError:
                raise HTTPException(400, "Datum mora biti u obliku GGGG-MM-DD.")
        rezultati = []
        cekaju = {u["email"]: u for u in db_neodobreni_korisnici()}
        for email in o.emailovi:
            u = cekaju.get(email)
            if not u:
                rezultati.append({"email": email, "ok": False, "poruka": "Nije na listi zahtjeva."})
                continue
            if o.clan_do:
                postavi_clan_do(email, o.clan_do)
            if not db_odobri_korisnika(email):
                rezultati.append({"email": email, "ok": False, "poruka": "Odobravanje nije uspjelo."})
                continue
            poruka = "Odobren."
            if o.posalji_email:
                ok, msg = posalji_email_odobrenje(email, u.get("full_name") or "")
                poruka += " Email poslan." if ok else f" Email NIJE poslan: {msg}"
            rezultati.append({"email": email, "ok": True, "poruka": poruka})
        return {"rezultati": rezultati}

    class Email(BaseModel):
        email: str

    @r.post("/zahtjevi/odbij")
    def odbij(e: Email, k=Depends(admin)):
        if e.email not in {u["email"] for u in db_neodobreni_korisnici()}:
            raise HTTPException(400, "Odbija se samo zahtjev koji čeka — odobren nalog se briše u Korisnicima.")
        if not db_odbij_korisnika(e.email):
            raise HTTPException(500, "Brisanje zahtjeva nije uspjelo.")
        return {"poruka": "Zahtjev odbijen i obrisan."}

    # ── Korisnici ────────────────────────────────────────────────────────────
    @r.get("/korisnici")
    def korisnici(k=Depends(admin)):
        broj = defaultdict(int)
        try:
            for p in db.table("attempts").select("user_email").eq("mode", "ispit").execute().data or []:
                broj[p["user_email"]] += 1
        except Exception as e:
            zabiljezi_gresku(e)
        return {"korisnici": [{**javni_nalog(u), "odigrano": broj.get(u["email"], 0)}
                              for u in db_svi_korisnici()]}

    class ClanDo(BaseModel):
        clan_do: str | None = None

    @r.post("/korisnici/{email}/clan_do")
    def clan_do(email: str, c: ClanDo, k=Depends(admin)):
        nalog_ili_404(email)
        postavi_clan_do(email, c.clan_do or None)
        return javni_nalog(nalog_ili_404(email))

    class Suspenzija(BaseModel):
        suspendovan: bool

    @r.post("/korisnici/{email}/suspenzija")
    def suspenzija(email: str, s: Suspenzija, k=Depends(admin)):
        zasticen(email, k)
        nalog_ili_404(email)
        if not db_postavi_suspenziju(email, s.suspendovan):
            raise HTTPException(500, "Promjena nije uspjela.")
        return javni_nalog(nalog_ili_404(email))

    @r.post("/korisnici/{email}/lozinka")
    def lozinka(email: str, k=Depends(admin)):
        zasticen(email, k)
        nalog_ili_404(email)
        privremena = db_resetuj_lozinku(email)
        if not privremena:
            raise HTTPException(500, "Reset lozinke nije uspio.")
        # Prikazuje se samo sada — nigdje se ne čuva u čitljivom obliku.
        return {"privremena": privremena}

    class Uloga(BaseModel):
        uloga: str

    @r.post("/korisnici/{email}/uloga")
    def uloga(email: str, u: Uloga, k=Depends(admin)):
        zasticen(email, k)
        ok, poruka = db_postavi_ulogu(email, u.uloga)
        if not ok:
            raise HTTPException(400, poruka)
        return javni_nalog(nalog_ili_404(email))

    @r.delete("/korisnici/{email}")
    def obrisi(email: str, k=Depends(admin)):
        zasticen(email, k)
        nalog_ili_404(email)
        if not db_obrisi_sve_podatke(email):
            raise HTTPException(500, "Brisanje nije uspjelo.")
        return {"poruka": "Nalog i svi podaci su obrisani."}

    @r.get("/korisnici/{email}/pokusaji")
    def pokusaji(email: str, k=Depends(admin)):
        osvjezi_scenarije()
        return {"pokusaji": [{
            "id": p["id"], "scenarij_id": p["scenario_id"], "naziv": naziv(p["scenario_id"]),
            "mode": p.get("mode") or "ispit", "ocjena": float(p.get("score") or 0),
            "anamneza": p.get("anamneza"), "komunikacija": p.get("komunikacija"), "sigurnost": p.get("sigurnost"),
            "zavrseno": p.get("completed_at"), "transkript": p.get("transcript") or "",
            "prigovor": {"status": p.get("appeal_status"), "tekst": p.get("appeal_text"),
                         "odgovor": p.get("appeal_response")},
        } for p in db_pokusaji_korisnika(email)]}

    class Restart(BaseModel):
        email: str
        scenarij_id: str
        mode: str = "ispit"

    @r.post("/pokusaji/restart")
    def restart(x: Restart, k=Depends(admin)):
        ok, broj = db_restartuj_scenarij(x.email, x.scenarij_id, x.mode)
        if not ok:
            raise HTTPException(500, "Restart nije uspio.")
        return {"obrisano": broj}

    # ── Prigovori (žalbe) ────────────────────────────────────────────────────
    def kriteriji_iz(z):
        try:
            rez = json.loads(z.get("result_json") or "{}")
        except ValueError:
            rez = {}
        return rez.get("kriteriji") or None, [x.get("id") for x in rez.get("radnje") or [] if isinstance(x, dict)]

    @r.get("/zalbe")
    def zalbe(k=Depends(admin)):
        osvjezi_scenarije()
        imena = {u["email"]: u.get("full_name") or u["email"] for u in db_svi_korisnici()}
        out = []
        for z in db_otvorene_zalbe():
            kriteriji, _ = kriteriji_iz(z)
            sc = SCENARIJI.get(z["scenario_id"]) or {}
            rub = rubrika.za_scenarij(sc, z["scenario_id"]) if sc and kriteriji else None
            kategorije = None
            if rub:
                kategorije = [{"naziv": kat["naziv"], "kriteriji": [{
                    "id": kr["id"], "tekst": kr["tekst"],
                    "status": (kriteriji.get(kr["id"]) or {}).get("status", "NE"),
                    "citat": (kriteriji.get(kr["id"]) or {}).get("citat", ""),
                } for kr in kat["kriteriji"]]} for kat in rub["kategorije"]]
            out.append({
                "id": z["id"], "email": z["user_email"], "ime": imena.get(z["user_email"], z["user_email"]),
                "scenarij_id": z["scenario_id"], "naziv": naziv(z["scenario_id"]),
                "ocjena": float(z.get("score") or 0), "anamneza": z.get("anamneza"),
                "komunikacija": z.get("komunikacija"), "sigurnost": z.get("sigurnost"),
                "tekst": z.get("appeal_text") or "", "transkript": z.get("transcript") or "",
                "kategorije": kategorije,
            })
        return {"zalbe": out}

    def zalba_ili_404(zid):
        z = next((x for x in db_otvorene_zalbe() if str(x["id"]) == str(zid)), None)
        if not z:
            raise HTTPException(404, "Prigovor nije pronađen ili je već riješen.")
        return z

    def preracunaj(z, statusi):
        """Ista funkcija koja je dodijelila bodove računa i ispravljene —
        ispravljena ocjena zato ne može ispasti iz rubrike."""
        kriteriji, radnje = kriteriji_iz(z)
        sc = SCENARIJI.get(z["scenario_id"]) or {}
        rub = rubrika.za_scenarij(sc, z["scenario_id"]) if sc else None
        if not rub or not kriteriji:
            return None, None
        novi = {}
        for kat in rub["kategorije"]:
            for kr in kat["kriteriji"]:
                stari = dict(kriteriji.get(kr["id"]) or {"status": "NE"})
                s = statusi.get(kr["id"], stari.get("status", "NE"))
                stari["status"] = s if s in rubrika.STATUSI else "NE"
                novi[kr["id"]] = stari
        b = rubrika.izracunaj(rub, novi, radnje)
        ocjene = {"anamneza": b.get("anamneza", 0), "komunikacija": b.get("komunikacija", 0),
                  "sigurnost": b.get("sigurnost", 0)}
        return ocjene, novi

    def ukupno(o):
        return round(float(o["anamneza"]) * 0.4 + float(o["komunikacija"]) * 0.3 + float(o["sigurnost"]) * 0.3, 2)

    class Statusi(BaseModel):
        statusi: dict[str, str] = {}

    @r.post("/zalbe/{zid}/preracunaj")
    def zalba_preracunaj(zid: str, s: Statusi, k=Depends(admin)):
        osvjezi_scenarije()
        ocjene, _ = preracunaj(zalba_ili_404(zid), s.statusi)
        if not ocjene:
            raise HTTPException(400, "Rubrika nije dostupna — ocjena se unosi ručno.")
        return {**ocjene, "ukupno": ukupno(ocjene)}

    class Odluka(BaseModel):
        odluka: str                      # "ispravi" | "odbij"
        odgovor: str
        statusi: dict[str, str] | None = None
        rucno: dict[str, float] | None = None   # {anamneza, komunikacija, sigurnost} kad rubrike nema

    @r.post("/zalbe/{zid}")
    def zalba_odluka(zid: str, o: Odluka, k=Depends(admin)):
        osvjezi_scenarije()
        z = zalba_ili_404(zid)
        if len(o.odgovor.strip()) < 3:
            raise HTTPException(400, "Upišite odgovor korisniku.")
        if o.odluka == "odbij":
            ok = db_rijesi_zalbu(z["id"], "odbijena", o.odgovor)
        elif o.odluka == "ispravi":
            ocjene, novi = (preracunaj(z, o.statusi) if o.statusi is not None else (None, None))
            if not ocjene:
                if not o.rucno:
                    raise HTTPException(400, "Nedostaju nove ocjene.")
                ocjene = {x: max(0.0, min(10.0, float(o.rucno.get(x, 0))))
                          for x in ("anamneza", "komunikacija", "sigurnost")}
            ok = db_rijesi_zalbu(z["id"], "rijesena", o.odgovor, ocjene, novi)
        else:
            raise HTTPException(400, "Nepoznata odluka.")
        if not ok:
            raise HTTPException(500, "Upis nije uspio.")
        return {"poruka": "Prigovor zatvoren."}

    # ── Statistika i izvoz ───────────────────────────────────────────────────
    @r.get("/statistika")
    def statistika(k=Depends(admin)):
        osvjezi_scenarije()
        p = db_statistika()
        if not p:
            raise HTTPException(500, "Statistika nije dostupna.")
        ispiti = [x for x in p["pokusaji"] if (x.get("mode") or "ispit") == "ispit"]
        upotreba = p["upotreba"]
        sada = datetime.now(timezone.utc)
        danas, od7, od30 = sada.date().isoformat(), (sada - timedelta(days=7)).isoformat(), (sada - timedelta(days=30)).isoformat()

        def aktivni(od):
            return len({u["user_email"] for u in upotreba if str(u.get("created_at", "")) >= od} - {"", None})

        def trosak(redovi):
            ti = sum(u.get("tokens_in") or 0 for u in redovi)
            to = sum(u.get("tokens_out") or 0 for u in redovi)
            return {"tokena": ti + to, "usd": round(ti * CIJENA_ULAZ_USD + to * CIJENA_IZLAZ_USD, 2)}

        po_sc = defaultdict(lambda: {"n": 0, "suma": 0.0})
        for x in ispiti:
            po_sc[x["scenario_id"]]["n"] += 1
            po_sc[x["scenario_id"]]["suma"] += float(x.get("score") or 0)
        startovi, zavrseni30 = defaultdict(int), defaultdict(int)
        for u in upotreba:
            if u.get("event") == "start" and u.get("scenario_id"):
                startovi[u["scenario_id"]] += 1
        for x in ispiti:
            if str(x.get("completed_at", "")) >= od30:
                zavrseni30[x["scenario_id"]] += 1
        po_korisniku = defaultdict(int)
        for u in upotreba:
            po_korisniku[u.get("user_email") or "?"] += (u.get("tokens_in") or 0) + (u.get("tokens_out") or 0)

        return {
            "korisnika": sum(1 for x in p["korisnici"] if x.get("approved")),
            "aktivni_danas": aktivni(danas), "aktivni_7d": aktivni(od7),
            "ispita": len(ispiti), "vjezbi": len(p["pokusaji"]) - len(ispiti),
            "po_scenariju": [{
                "naziv": naziv(sid), "pokusaja": d["n"], "prosjek": round(d["suma"] / d["n"], 1) if d["n"] else 0,
                "zavrsenost": (min(100, round(100 * zavrseni30[sid] / startovi[sid])) if startovi.get(sid) else None),
            } for sid, d in sorted(po_sc.items())],
            "trosak": {"danas": trosak([u for u in upotreba if str(u.get("created_at", "")) >= danas]),
                       "dana7": trosak([u for u in upotreba if str(u.get("created_at", "")) >= od7]),
                       "dana30": trosak(upotreba)},
            "top_tokeni": [{"email": em, "tokena": t} for em, t in sorted(po_korisniku.items(), key=lambda x: -x[1])[:5]],
        }

    def csv_odgovor(ime, sadrzaj):
        return Response(sadrzaj, media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": f'attachment; filename="{ime}"'})

    @r.get("/izvoz/rezultati")
    def izvoz_rezultati(k=Depends(admin)):
        osvjezi_scenarije()
        kor = {u["email"]: u for u in db_svi_korisnici()}
        redovi = [[kor.get(p["user_email"], {}).get("full_name", ""), p["user_email"],
                   kor.get(p["user_email"], {}).get("institution", ""), naziv(p["scenario_id"]),
                   p.get("score", ""), p.get("anamneza", ""), p.get("komunikacija", ""), p.get("sigurnost", ""),
                   str(p.get("completed_at", ""))[:16].replace("T", " "), p.get("appeal_status") or ""]
                  for p in db_svi_pokusaji_export()]
        return csv_odgovor(f"rezultati_{date.today()}.csv", napravi_csv(
            ["Ime", "Email", "Institucija", "Scenarij", "Ocjena", "Anamneza", "Komunikacija",
             "Sigurnost", "Datum", "Žalba"], redovi))

    @r.get("/izvoz/korisnici")
    def izvoz_korisnici(k=Depends(admin)):
        redovi = [[u.get("full_name", ""), u["email"], u.get("institution", ""),
                   "suspendovan" if u.get("suspended") else "aktivan", str(u.get("clan_do") or ""),
                   str(u.get("created_at", ""))[:16].replace("T", " ")] for u in db_svi_korisnici()]
        return csv_odgovor(f"korisnici_{date.today()}.csv", napravi_csv(
            ["Ime", "Email", "Institucija", "Status", "Članarina do", "Registrovan"], redovi))

    # ── Slučajevi: samo otključavanje/zaključavanje ──────────────────────────
    class Aktivan(BaseModel):
        aktivan: bool

    @r.post("/slucajevi/{sid}/aktivan")
    def aktivan(sid: str, a: Aktivan, k=Depends(admin)):
        osvjezi_scenarije()
        sc = SCENARIJI.get(sid)
        if not sc or not sc.get("_iz_baze"):
            raise HTTPException(400, "Ugrađeni scenarij se mijenja samo u Streamlitu (prvo kopija u bazu).")
        if not db_scenarij_aktivan(sid, a.aktivan):
            raise HTTPException(500, "Promjena nije uspjela.")
        osvjezi_scenarije()
        return {"aktivan": a.aktivan}

    # ── Objave (traka na vrhu za članove) ────────────────────────────────────
    @r.get("/objave")
    def objave(k=Depends(admin)):
        return {"objave": [{"id": o["id"], "tekst": o.get("tekst", ""), "tip": o.get("tip") or "info",
                            "aktivna": bool(o.get("active")), "kreirana": o.get("created_at")}
                           for o in db_objave_sve()]}

    class NovaObjava(BaseModel):
        tekst: str
        tip: str = "info"

    @r.post("/objave")
    def nova_objava(o: NovaObjava, k=Depends(admin)):
        if len(o.tekst.strip()) < 3 or o.tip not in ("info", "warning"):
            raise HTTPException(400, "Upišite tekst objave.")
        if not db_objava_nova(o.tekst, o.tip):
            raise HTTPException(500, "Objava nije sačuvana.")
        return {"poruka": "Objava postavljena."}

    class Vidljiva(BaseModel):
        aktivna: bool

    @r.post("/objave/{oid}")
    def objava_vidljiva(oid: str, v: Vidljiva, k=Depends(admin)):
        if not db_objava_aktivna(oid, v.aktivna):
            raise HTTPException(500, "Promjena nije uspjela.")
        return {"aktivna": v.aktivna}

    @r.delete("/objave/{oid}")
    def objava_obrisi(oid: str, k=Depends(admin)):
        if not db_objava_obrisi(oid):
            raise HTTPException(500, "Brisanje nije uspjelo.")
        return {"poruka": "Objava obrisana."}

    # ── Email ────────────────────────────────────────────────────────────────
    class Masovni(BaseModel):
        primaoci: list[str] | None = None   # None = svi odobreni
        naslov: str
        poruka: str

    @r.post("/email")
    def masovni(m: Masovni, k=Depends(admin)):
        if not m.naslov.strip() or len(m.poruka.strip()) < 5:
            raise HTTPException(400, "Upišite naslov i tekst poruke.")
        svi = db_svi_korisnici()
        lista = svi if m.primaoci is None else [u for u in svi if u["email"] in set(m.primaoci)]
        if not lista:
            raise HTTPException(400, "Nema primalaca.")
        poslano, greske = 0, []
        for u in lista:
            ok, msg = posalji_email_masovni(u["email"], u.get("full_name") or "", m.naslov.strip(), m.poruka)
            if ok:
                poslano += 1
            else:
                greske.append(f"{u['email']}: {msg}")
        return {"poslano": poslano, "ukupno": len(lista), "greske": greske}

    class Probni(BaseModel):
        email: str

    @r.post("/email/probni")
    def probni(p: Probni, k=Depends(admin)):
        """Jedan probni email na zadanu adresu — provjera da Brevo radi."""
        if "@" not in p.email:
            raise HTTPException(400, "Neispravan email.")
        ok, msg = posalji_email(p.email, "Probni email — Komunikator", (
            "<div style='font-family:Inter,Segoe UI,sans-serif;max-width:520px;margin:0 auto;padding:24px'>"
            "<h2 style='color:#0D8A9E'>Komunikator</h2><p>Ovo je probni email iz admin panela Komunikatora. "
            "Ako ga vidite, slanje preko Breva radi.</p></div>"))
        if not ok:
            raise HTTPException(502, msg)
        return {"poruka": f"Probni email poslan na {p.email}."}

    return r
