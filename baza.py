"""Sve sto dira Supabase: korisnici, lozinke, pokusaji, scenariji, objave.

Nijedna funkcija ovdje ne baca izuzetak prema pozivaocu — baza moze biti
nedostupna (Supabase Free pauzira projekat), a aplikacija tada mora nastaviti
raditi u okrnjenom obliku umjesto da padne.
"""
import csv
import hashlib
import io
import json
import secrets
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import bcrypt
import streamlit as st

from konfig import ADMIN_EMAIL, KONTAKT_EMAIL, db, zabiljezi_gresku

# ─── Lozinke ─────────────────────────────────────────────────────────────────
# Do septembra 2026. lozinke su čuvane kao goli SHA-256 bez soli — takav hash se
# razbija gotovim tablicama ako baza ikad procuri. Prelazi se na bcrypt, ali bez
# prekida za korisnike: stari hash se i dalje prihvata pri prijavi i tada se
# odmah tiho prepisuje bcrypt hashom (vidi migriraj_hash u db_login).
BROJ_PROMASAJA_ZA_ZAKLJUCAVANJE = 5
ZAKLJUCAVANJE_MINUTA = 15


def hash_loz(lozinka: str) -> str:
    """Legacy SHA-256. Ostaje samo da se stare lozinke mogu provjeriti."""
    return hashlib.sha256(lozinka.encode()).hexdigest()


def hash_loz_bcrypt(lozinka: str) -> str:
    return bcrypt.hashpw(lozinka.encode(), bcrypt.gensalt()).decode()


def provjeri_lozinku(lozinka: str, sacuvani_hash: str):
    """Vraća (tačna_lozinka, treba_migraciju)."""
    h = sacuvani_hash or ""
    if h.startswith("$2"):                      # bcrypt
        try:
            return bcrypt.checkpw(lozinka.encode(), h.encode()), False
        except ValueError:
            return False, False
    return secrets.compare_digest(h, hash_loz(lozinka)), True


def nadimak_za(korisnik, email=""):
    """Javno ime na ljestvici. Pravo ime i institucija se tamo nikad ne prikazuju.

    Zatečeni korisnici nemaju nadimak — dok ga ne postave dobijaju stabilnu
    neutralnu oznaku izvedenu iz emaila, koja ne otkriva ko su.
    """
    n = (korisnik or {}).get("nadimak") or ""
    if n.strip():
        return n.strip()
    em = (korisnik or {}).get("email") or email or ""
    return "Farmaceut-" + hashlib.sha256(em.encode()).hexdigest()[:4].upper()


def je_admin(korisnik=None):
    """Uloga iz baze, uz email kao sigurnosnu mrežu.

    ADMIN_EMAIL ostaje kao fallback da pogrešan upis u koloni 'role' nikad ne
    zaključa Semira izvan admin panela.
    """
    k = korisnik if korisnik is not None else (st.session_state.get("korisnik") or {})
    return (k.get("role") == "admin") or (k.get("email", "") == ADMIN_EMAIL)


def je_mentor(korisnik=None):
    k = korisnik if korisnik is not None else (st.session_state.get("korisnik") or {})
    return k.get("role") in ("mentor", "admin") or je_admin(k)


def db_postavi_ulogu(email, uloga):
    if not db:
        return False, "Baza podataka nije dostupna."
    if uloga not in ("korisnik", "mentor", "admin"):
        return False, "Nepoznata uloga."
    if email == ADMIN_EMAIL and uloga != "admin":
        return False, "Glavnom administratoru se uloga ne može oduzeti."
    try:
        db.table("users").update({"role": uloga}).eq("email", email).execute()
        return True, "ok"
    except Exception as e:
        zabiljezi_gresku(e)
        return False, f"Greška: {e}"


def nadimak_slobodan(nadimak, email):
    if not db:
        return True
    try:
        r = db.table("users").select("email, nadimak").execute()
        n = nadimak.strip().lower()
        return not any((u.get("nadimak") or "").strip().lower() == n
                       and u["email"] != email for u in (r.data or []))
    except Exception:
        return True


def db_postavi_nadimak(email, nadimak):
    if not db:
        return False, "Baza podataka nije dostupna."
    n = (nadimak or "").strip()
    if len(n) < 3:
        return False, "Nadimak mora imati najmanje 3 znaka."
    if len(n) > 24:
        return False, "Nadimak može imati najviše 24 znaka."
    if "@" in n:
        return False, "Nadimak ne smije sadržavati email adresu."
    if not nadimak_slobodan(n, email):
        return False, "Taj nadimak je već zauzet. Izaberite drugi."
    try:
        db.table("users").update({"nadimak": n}).eq("email", email).execute()
        return True, "ok"
    except Exception as e:
        zabiljezi_gresku(e)
        return False, f"Greška: {e}"


def db_registruj(email, lozinka, ime, institucija, nadimak=""):
    if not db:
        return False, "Baza podataka nije dostupna."
    try:
        r = db.table("users").select("email").eq("email", email.lower().strip()).execute()
        if r.data:
            return False, "Email je već registrovan."
        db.table("users").insert({
            "email": email.lower().strip(),
            "password_hash": hash_loz_bcrypt(lozinka),
            "full_name": ime.strip(),
            "institution": institucija.strip(),
            "nadimak": (nadimak or "").strip() or None,
            "approved": False,   # pristup odobrava iskljucivo admin, rucno
        }).execute()
        return True, "ok"
    except Exception as e:
        zabiljezi_gresku(e)
        return False, f"Greška: {e}"


def _minuta_do(vrijeme_iso):
    try:
        do = datetime.fromisoformat(vrijeme_iso.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return 0
    return max(0, int((do - datetime.now(timezone.utc)).total_seconds() // 60) + 1)


def db_login(email, lozinka):
    if not db:
        return None, "Baza podataka nije dostupna."
    try:
        em = email.lower().strip()
        r = db.table("users").select("*").eq("email", em).execute()
        # Ista poruka za nepostojeći email i za pogrešnu lozinku — inače ekran
        # prijave sam otkriva ko je registrovan.
        if not r.data:
            return None, "Pogrešan email ili lozinka."
        k = r.data[0]

        zakljucan_do = k.get("locked_until")
        if zakljucan_do and _minuta_do(zakljucan_do) > 0:
            return None, (f"Nalog je zaključan zbog previše pogrešnih pokušaja. "
                          f"Pokušajte ponovo za {_minuta_do(zakljucan_do)} min.")

        tacna, treba_migraciju = provjeri_lozinku(lozinka, k.get("password_hash"))
        if not tacna:
            promasaji = int(k.get("failed_logins") or 0) + 1
            izmjena = {"failed_logins": promasaji}
            if promasaji >= BROJ_PROMASAJA_ZA_ZAKLJUCAVANJE:
                izmjena["locked_until"] = (
                    datetime.now(timezone.utc) + timedelta(minutes=ZAKLJUCAVANJE_MINUTA)
                ).isoformat()
            try:
                db.table("users").update(izmjena).eq("email", em).execute()
            except Exception:
                pass        # brojač ne smije oboriti prijavu ako kolone još nema
            if promasaji >= BROJ_PROMASAJA_ZA_ZAKLJUCAVANJE:
                return None, (f"Nalog je zaključan na {ZAKLJUCAVANJE_MINUTA} min zbog "
                              f"{promasaji} pogrešna pokušaja prijave.")
            preostalo = BROJ_PROMASAJA_ZA_ZAKLJUCAVANJE - promasaji
            return None, f"Pogrešan email ili lozinka. Preostalo pokušaja: {preostalo}."

        # Uspjeh: brojač na nulu, i tiha migracija starog SHA-256 hasha na bcrypt.
        izmjena = {"failed_logins": 0, "locked_until": None}
        if treba_migraciju:
            izmjena["password_hash"] = hash_loz_bcrypt(lozinka)
        try:
            db.table("users").update(izmjena).eq("email", em).execute()
            k.update(izmjena)
        except Exception as e:
            zabiljezi_gresku(e)

        if k.get("suspended", False):
            return None, "Vaš nalog je privremeno suspendovan. Kontaktirajte administratora."
        if not k.get("approved", False):
            return None, ("Vaš nalog čeka odobrenje administratora. Pristup je otvoren samo članovima "
                          f"Edu Pharma Community. Kontakt: {KONTAKT_EMAIL}")
        return k, "ok"
    except Exception as e:
        zabiljezi_gresku(e)
        return None, f"Greška: {e}"


ISPIT = "ispit"
VJEZBA = "vjezba"


def db_zavrseni_scenariji(email):
    """Scenariji koje je korisnik ISPITNO završio — ti se više ne mogu igrati.

    Vježbe se namjerno ne broje: vježba je neograničena i ne smije zaključati
    scenarij. Lista scenarija je ranije zvala db_vec_uradio dvaput po
    scenariju, a Streamlit prerenderuje pri svakoj interakciji — uz 15
    scenarija to je 30 upita po kliku.
    """
    if not db:
        return set()
    try:
        r = (db.table("attempts").select("scenario_id")
             .eq("user_email", email).eq("mode", ISPIT).execute())
        return {a["scenario_id"] for a in (r.data or [])}
    except Exception:
        return set()


def db_broj_vjezbi(email):
    """Koliko je puta korisnik vježbao svaki scenarij — {scenario_id: broj}."""
    if not db:
        return {}
    try:
        r = (db.table("attempts").select("scenario_id")
             .eq("user_email", email).eq("mode", VJEZBA).execute())
        brojac = defaultdict(int)
        for a in (r.data or []):
            brojac[a["scenario_id"]] += 1
        return dict(brojac)
    except Exception:
        return {}


def db_vec_uradio(email, scenario_id):
    """Je li scenarij ISPITNO odigran. Vježbe ne zaključavaju scenarij."""
    if not db:
        return False
    try:
        r = (db.table("attempts").select("id").eq("user_email", email)
             .eq("scenario_id", scenario_id).eq("mode", ISPIT).execute())
        return len(r.data) > 0
    except Exception:
        return False


def db_spremi(email, scenario_id, rezultat, transkript="", stanja=None, mode=ISPIT):
    if not db:
        return
    red = {
        "user_email": email,
        "scenario_id": scenario_id,
        "mode": mode,
        "score": float(rezultat.get("ukupna_ocjena", 0)),
        # Kolone kategorija su cjelobrojne, a rubrika v2 daje i polovine (7.5)
        # jer DJELIMICNO nosi pola bodova. Zaokruzuje se, ne odsijeca — tacna
        # vrijednost ostaje u score i u result_json, odakle je ekran i cita.
        "anamneza": round(float(rezultat.get("anamneza", 0))),
        "komunikacija": round(float(rezultat.get("komunikacija", 0))),
        "sigurnost": round(float(rezultat.get("sigurnost", 0))),
        "result_json": json.dumps(rezultat, ensure_ascii=False),
    }
    try:
        db.table("attempts").insert(
            {**red, "transcript": transkript, "stanje_json": stanja or None}).execute()
    except Exception:
        # Postepeno odustajanje ako neka od novijih kolona još ne postoji u bazi.
        # Rezultat korisnika je ono što se ne smije izgubiti — radije bez stanja
        # i bez transkripta nego bez ocjene.
        try:
            db.table("attempts").insert({**red, "transcript": transkript}).execute()
        except Exception:
            try:
                db.table("attempts").insert(red).execute()
            except Exception:
                try:
                    # Zadnja odbrana: baza bez kolone 'mode'. Ocjena je vaznija
                    # od podatka je li bila vjezba ili ispit.
                    db.table("attempts").insert(
                        {k: v for k, v in red.items() if k != "mode"}).execute()
                except Exception as e:
                    zabiljezi_gresku(e)


def db_dohvati_ocjenu(email, scenario_id, mode=ISPIT):
    """Ocjena za scenarij. Podrazumijevano ispitna — vježbe se ne prikazuju
    na ekranu završenog scenarija, jer ih može biti više."""
    if not db:
        return None
    try:
        r = (db.table("attempts").select("result_json").eq("user_email", email)
             .eq("scenario_id", scenario_id).eq("mode", mode)
             .order("completed_at", desc=True).execute())
        if r.data and r.data[0].get("result_json"):
            return json.loads(r.data[0]["result_json"])
    except Exception:
        pass
    return None


def db_dohvati_transkript(email, scenario_id, mode=ISPIT):
    """Transkript završenog pokušaja.

    Ekran završenog scenarija je transkript čitao iz sesije, pa je poslije
    odjave i ponovne prijave ostajao prazan.
    """
    if not db:
        return ""
    try:
        r = (db.table("attempts").select("transcript").eq("user_email", email)
             .eq("scenario_id", scenario_id).eq("mode", mode)
             .order("completed_at", desc=True).execute())
        if r.data:
            return r.data[0].get("transcript") or ""
    except Exception:
        pass
    return ""


def db_moji_rezultati(email):
    if not db:
        return []
    try:
        r = db.table("attempts").select("*").eq("user_email", email).order("completed_at", desc=True).execute()
        return r.data
    except Exception:
        return []


# ─── Trajnost razgovora ──────────────────────────────────────────────────────
# Razgovor je do sada zivio samo u st.session_state. Osvjezavanje stranice na
# mobitelu ga je brisalo, a tajmer je nastavljao oduzimati poteze — polaznik bi
# se vratio u prazan ekran s potrosenim pokusajima. Sada se stanje upisuje
# poslije svakog poteza i vraca pri ulasku u scenarij.

def db_ucitaj_napredak(email, scenario_id, mode=ISPIT):
    """Vraća sačuvani razgovor u toku ili None."""
    if not db:
        return None
    try:
        r = (db.table("attempts_progress").select("*")
             .eq("user_email", email).eq("scenario_id", scenario_id)
             .eq("mode", mode).execute())
        if not r.data:
            return None
        red = r.data[0]
        return {
            "poruke_api": red.get("poruke_api") or [],
            "poruke_prikaz": red.get("poruke_prikaz") or [],
            "stanja": red.get("stanja") or [],
            "zadnje_stanje": red.get("zadnje_stanje"),
            "broj_poteza": red.get("broj_poteza") or 0,
            "izgubljeno_ukupno": red.get("izgubljeno_ukupno") or 0,
            "zadnji_potez_vrijeme": red.get("zadnji_potez_vrijeme"),
        }
    except Exception:
        return None


def db_spremi_napredak(email, scenario_id, stanje, mode=ISPIT):
    """Upisuje razgovor u toku. Tiho odustaje — ovo ne smije srušiti potez."""
    if not db or not email:
        return
    try:
        db.table("attempts_progress").upsert({
            "user_email": email,
            "scenario_id": scenario_id,
            "mode": mode,
            "broj_poteza": stanje.get("broj_poteza", 0),
            "izgubljeno_ukupno": stanje.get("izgubljeno_ukupno", 0),
            "poruke_api": stanje.get("poruke_api") or [],
            "poruke_prikaz": stanje.get("poruke_prikaz") or [],
            "stanja": stanje.get("stanja") or [],
            "zadnje_stanje": stanje.get("zadnje_stanje"),
            "azurirano_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="user_email,scenario_id,mode").execute()
    except Exception as e:
        zabiljezi_gresku(e)


def db_obrisi_napredak(email, scenario_id, mode=ISPIT):
    """Briše sačuvani razgovor — poziva se kad je scenarij ocijenjen."""
    if not db or not email:
        return
    try:
        (db.table("attempts_progress").delete()
         .eq("user_email", email).eq("scenario_id", scenario_id)
         .eq("mode", mode).execute())
    except Exception as e:
        zabiljezi_gresku(e)


def db_leaderboard(period):
    if not db:
        return []
    try:
        now = datetime.now(timezone.utc)
        if period == "sedmicno":
            od = (now - timedelta(days=7)).isoformat()
        elif period == "mjesecno":
            od = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        elif period == "godisnje":
            od = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        else:
            od = "2020-01-01T00:00:00+00:00"

        # Ljestvica broji samo ispite — vjezba je neogranicena, pa bi inace
        # rang mjerio upornost umjesto znanja.
        r = (db.table("attempts")
             .select("user_email, score, anamneza, komunikacija, sigurnost")
             .eq("mode", ISPIT).gte("completed_at", od).execute())
        if not r.data:
            return []

        skupovi = defaultdict(lambda: {"scores": [], "anamneza": [], "komunikacija": [], "sigurnost": []})
        for row in r.data:
            skupovi[row["user_email"]]["scores"].append(float(row["score"]))
            if row.get("anamneza") is not None:
                skupovi[row["user_email"]]["anamneza"].append(float(row["anamneza"]))
            if row.get("komunikacija") is not None:
                skupovi[row["user_email"]]["komunikacija"].append(float(row["komunikacija"]))
            if row.get("sigurnost") is not None:
                skupovi[row["user_email"]]["sigurnost"].append(float(row["sigurnost"]))

        emailovi = list(skupovi.keys())
        im = db.table("users").select("email, nadimak").in_("email", emailovi).execute()
        info = {u["email"]: u for u in im.data}

        lista = []
        for em, data in skupovi.items():
            k = info.get(em, {})
            scores = data["scores"]
            avg_a = round(sum(data["anamneza"]) / len(data["anamneza"]), 1) if data["anamneza"] else 0
            avg_k = round(sum(data["komunikacija"]) / len(data["komunikacija"]), 1) if data["komunikacija"] else 0
            avg_s = round(sum(data["sigurnost"]) / len(data["sigurnost"]), 1) if data["sigurnost"] else 0
            lista.append({
                "email": em,
                # Ljestvica je javna unutar zajednice — ide samo nadimak.
                "ime": nadimak_za(k, em),
                "institucija": "",
                "ukupno": round(sum(scores), 2),
                "slucajeva": len(scores),
                "prosjek": round(sum(scores) / len(scores), 2),
                "avg_anamneza": avg_a,
                "avg_komunikacija": avg_k,
                "avg_sigurnost": avg_s,
            })

        lista.sort(key=lambda x: x["ukupno"], reverse=True)
        return lista
    except Exception:
        return []


# ─── Admin DB funkcije ───────────────────────────────────────────────────────
def db_neodobreni_korisnici():
    if not db:
        return []
    try:
        r = db.table("users").select("*").eq("approved", False).execute()
        return r.data or []
    except Exception:
        return []


def db_odobri_korisnika(email):
    if not db:
        st.error("Baza podataka nije dostupna.")
        return False
    try:
        db.table("users").update({"approved": True}).eq("email", email).execute()
        return True
    except Exception as e:
        st.error(f"DB greška (odobri): {e}")
        return False


def db_odbij_korisnika(email):
    if not db:
        st.error("Baza podataka nije dostupna.")
        return False
    try:
        db.table("users").delete().eq("email", email).execute()
        return True
    except Exception as e:
        st.error(f"DB greška (odbij): {e}")
        return False


def db_svi_korisnici():
    if not db:
        return []
    try:
        r = db.table("users").select("*").eq("approved", True).order("full_name").execute()
        return r.data or []
    except Exception:
        return []


def db_resetuj_lozinku(email):
    """Postavlja privremenu lozinku i vraća je (None uz grešku)."""
    if not db:
        st.error("Baza podataka nije dostupna.")
        return None
    try:
        abeceda = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"
        privremena = "".join(secrets.choice(abeceda) for _ in range(10))
        db.table("users").update({"password_hash": hash_loz_bcrypt(privremena),
                                  "failed_logins": 0, "locked_until": None}).eq("email", email).execute()
        return privremena
    except Exception as e:
        st.error(f"DB greška (reset lozinke): {e}")
        return None


def db_postavi_suspenziju(email, suspendovan):
    if not db:
        st.error("Baza podataka nije dostupna.")
        return False
    try:
        db.table("users").update({"suspended": suspendovan}).eq("email", email).execute()
        return True
    except Exception as e:
        st.error(f"DB greška (suspenzija): {e}")
        return False


def db_pokusaji_korisnika(email):
    """Svi pokušaji jednog korisnika, s transkriptom (za admin pregled)."""
    if not db:
        return []
    try:
        r = db.table("attempts").select("*").eq("user_email", email).order("completed_at", desc=True).execute()
        return r.data or []
    except Exception:
        return []


def db_obrisi_sve_podatke(email):
    """GDPR brisanje: uklanja nalog i SVE povezane podatke (pokušaji,
    transkripti, žalbe, log korištenja)."""
    if not db:
        st.error("Baza podataka nije dostupna.")
        return False
    try:
        db.table("attempts").delete().eq("user_email", email).execute()
        db.table("usage_log").delete().eq("user_email", email).execute()
        db.table("users").delete().eq("email", email).execute()
        return True
    except Exception as e:
        zabiljezi_gresku(e)
        st.error(f"DB greška (GDPR brisanje): {e}")
        return False


def db_svi_pokusaji_export():
    """Svi pokušaji (bez transkripta) za CSV export."""
    if not db:
        return []
    try:
        r = db.table("attempts").select(
            "user_email, scenario_id, mode, score, anamneza, komunikacija, sigurnost, "
            "completed_at, appeal_status"
        ).order("completed_at", desc=True).execute()
        return r.data or []
    except Exception as e:
        zabiljezi_gresku(e)
        return []


def napravi_csv(zaglavlje, redovi):
    """Gradi CSV bajtove (UTF-8 sa BOM-om, ';' separator — radi u Excelu)."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\n")
    w.writerow(zaglavlje)
    w.writerows(redovi)
    return buf.getvalue().encode("utf-8-sig")


# ─── Žalbe na ocjenu ─────────────────────────────────────────────────────────
def db_posalji_zalbu(attempt_id, tekst):
    if not db:
        return False, "Baza podataka nije dostupna."
    try:
        db.table("attempts").update({
            "appeal_status": "otvorena",
            "appeal_text": tekst.strip(),
        }).eq("id", attempt_id).execute()
        return True, "ok"
    except Exception as e:
        return False, f"Greška: {e}"


def db_otvorene_zalbe():
    if not db:
        return []
    try:
        r = db.table("attempts").select("*").eq("appeal_status", "otvorena").order("completed_at", desc=True).execute()
        return r.data or []
    except Exception:
        return []


def db_rijesi_zalbu(attempt_id, status, odgovor, nove_ocjene=None, novi_kriteriji=None):
    """Zatvara žalbu ('rijesena'/'odbijena'); opcionalno ispravlja ocjene.

    `novi_kriteriji` dolazi iz žalbe na ocjenu v2 — administrator je preokrenuo
    sporni kriterij, pa se u zapis mora upisati i nova presuda, ne samo broj.
    Inače bi polazniku ostala tabela koja proturječi vlastitoj ocjeni.
    """
    if not db:
        st.error("Baza podataka nije dostupna.")
        return False
    try:
        payload = {"appeal_status": status, "appeal_response": odgovor.strip()}
        if nove_ocjene:
            # Rubrika v2 daje i polovine bodova; ukupna ocjena se racuna iz
            # tacnih vrijednosti, a kolone kategorija primaju zaokruzene.
            a = round(float(nove_ocjene["anamneza"]), 1)
            k = round(float(nove_ocjene["komunikacija"]), 1)
            s = round(float(nove_ocjene["sigurnost"]), 1)
            ukupna = round(a * 0.4 + k * 0.3 + s * 0.3, 2)
            payload.update({"anamneza": round(a), "komunikacija": round(k),
                            "sigurnost": round(s), "score": ukupna})
            r = db.table("attempts").select("result_json").eq("id", attempt_id).execute()
            if r.data and r.data[0].get("result_json"):
                rez = json.loads(r.data[0]["result_json"])
                rez.update({
                    "anamneza": a, "komunikacija": k, "sigurnost": s,
                    "ukupna_ocjena": ukupna, "korigovano_od_admina": True,
                })
                if novi_kriteriji:
                    rez["kriteriji"] = novi_kriteriji
                payload["result_json"] = json.dumps(rez, ensure_ascii=False)
        db.table("attempts").update(payload).eq("id", attempt_id).execute()
        return True
    except Exception as e:
        st.error(f"DB greška (žalba): {e}")
        return False


# ─── Log korištenja — analitika, troškovi, dnevni limit ──────────────────────
def db_log_upotrebu(event, scenario_id="", tokens_in=0, tokens_out=0):
    if not db:
        return
    try:
        db.table("usage_log").insert({
            "user_email": st.session_state.get("korisnik_email", ""),
            "event": event,
            "scenario_id": scenario_id,
            "tokens_in": int(tokens_in),
            "tokens_out": int(tokens_out),
        }).execute()
    except Exception:
        pass


def db_poruka_danas(email):
    """Broj AI poruka korisnika danas (za dnevni limit). Fail-open na 0."""
    if not db:
        return 0
    try:
        od = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        r = (db.table("usage_log").select("id", count="exact")
             .eq("user_email", email).eq("event", "poruka").gte("created_at", od).execute())
        return r.count or 0
    except Exception:
        return 0


def db_statistika():
    """Sirovi podaci za admin statistiku (pokušaji, korisnici, upotreba 30 dana)."""
    if not db:
        return None
    try:
        pokusaji = db.table("attempts").select(
            "user_email, scenario_id, mode, score, completed_at").execute().data or []
        korisnici = db.table("users").select("email, approved").execute().data or []
        od30 = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        upotreba = db.table("usage_log").select(
            "user_email, event, scenario_id, tokens_in, tokens_out, created_at"
        ).gte("created_at", od30).execute().data or []
        return {"pokusaji": pokusaji, "korisnici": korisnici, "upotreba": upotreba}
    except Exception:
        return None


# ─── CMS: scenariji iz baze ──────────────────────────────────────────────────
@st.cache_data(ttl=120)
def _ucitaj_db_scenarije():
    """Scenariji iz Supabase — nadjačavaju/dopunjuju ugrađene (isti id)."""
    if not db:
        return {}
    try:
        r = db.table("scenarios").select("*").execute()
        out = {}
        for red in r.data or []:
            out[red["id"]] = {
                "naziv": red.get("naziv") or red["id"],
                "ime": red.get("ime") or "",
                "godine": red.get("godine") or 0,
                "tegoba": red.get("tegoba") or "",
                "terapija": red.get("terapija") or "",
                "skriveni_detalji": red.get("skriveni_detalji") or "",
                "crvene_zastavice": red.get("crvene_zastavice") or "",
                "ocekivano": red.get("ocekivano") or "",
                "pocetna_poruka": red.get("pocetna_poruka") or "",
                "rubrika": red.get("rubrika") or "",
                "persona": red.get("persona") or {},
                "cinjenice": red.get("cinjenice") or None,
                "otpor": red.get("otpor") or None,
                "vidljivi_znakovi": red.get("vidljivi_znakovi") or "",
                "epilog": red.get("epilog") or "",
                "uzoran_razgovor": red.get("uzoran_razgovor") or "",
                "aktivan": bool(red.get("active", False)),
                "_iz_baze": True,
            }
        return out
    except Exception:
        return {}


def db_scenarij_spremi(sid, podaci):
    """Upsert scenarija u bazu (podaci = dict s poljima tabele scenarios)."""
    if not db:
        st.error("Baza podataka nije dostupna.")
        return False
    try:
        db.table("scenarios").upsert({"id": sid.strip(), **podaci}).execute()
        _ucitaj_db_scenarije.clear()
        return True
    except Exception as e:
        st.error(f"DB greška (scenarij): {e}")
        return False


def db_scenarij_aktivan(sid, aktivan):
    if not db:
        return False
    try:
        db.table("scenarios").update({"active": aktivan}).eq("id", sid).execute()
        _ucitaj_db_scenarije.clear()
        return True
    except Exception as e:
        st.error(f"DB greška (scenarij): {e}")
        return False


def db_scenarij_obrisi(sid):
    if not db:
        return False
    try:
        db.table("scenarios").delete().eq("id", sid).execute()
        _ucitaj_db_scenarije.clear()
        return True
    except Exception as e:
        st.error(f"DB greška (scenarij): {e}")
        return False


# ─── Objave / banner ─────────────────────────────────────────────────────────
@st.cache_data(ttl=120)
def _ucitaj_objave():
    if not db:
        return []
    try:
        r = (db.table("announcements").select("*")
             .eq("active", True).order("created_at", desc=True).execute())
        return r.data or []
    except Exception:
        return []


def db_objave_sve():
    if not db:
        return []
    try:
        r = db.table("announcements").select("*").order("created_at", desc=True).execute()
        return r.data or []
    except Exception:
        return []


def db_objava_nova(tekst, tip):
    if not db:
        st.error("Baza podataka nije dostupna.")
        return False
    try:
        db.table("announcements").insert({"tekst": tekst.strip(), "tip": tip, "active": True}).execute()
        _ucitaj_objave.clear()
        return True
    except Exception as e:
        st.error(f"DB greška (objava): {e}")
        return False


def db_objava_aktivna(oid, aktivna):
    if not db:
        return False
    try:
        db.table("announcements").update({"active": aktivna}).eq("id", oid).execute()
        _ucitaj_objave.clear()
        return True
    except Exception as e:
        st.error(f"DB greška (objava): {e}")
        return False


def db_objava_obrisi(oid):
    if not db:
        return False
    try:
        db.table("announcements").delete().eq("id", oid).execute()
        _ucitaj_objave.clear()
        return True
    except Exception as e:
        st.error(f"DB greška (objava): {e}")
        return False
