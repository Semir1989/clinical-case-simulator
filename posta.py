"""Slanje emaila preko Brevo transakcijskog API-ja.

Do 16.10.2026. je ovdje bio Resend, ali RESEND_API_KEY nikad nije bio podešen,
pa nijedan email iz aplikacije (odobrenje naloga, masovni) nije stvarno otišao.
Brevo je već tu: pošiljalac info@farmaceutupraksi.ba je potvrđen, a paket ima
transakcijske emailove. Šalje se pojedinačno — Brevo liste i kampanje se ne diraju.
"""
import json
import os
import urllib.error
import urllib.request

import streamlit as st

from konfig import zabiljezi_gresku

# Pošiljalac mora biti potvrđen u Brevu (Senders) — inače Brevo odbija slanje.
POSILJALAC_EMAIL = "info@farmaceutupraksi.ba"
POSILJALAC_IME = "Edu Pharma Community"
KOMUNIKATOR_URL = "https://simulator.farmaceutupraksi.ba"


# ─── Email notifikacije (Brevo) ──────────────────────────────────────────────
def _brevo_kljuc():
    """Prvo okruženje (Komunikator API na Cloud Runu), pa Streamlit secrets.
    Van Streamlita st.secrets baca grešku, ne vraća prazno."""
    kljuc = os.getenv("BREVO_API_KEY", "")
    if not kljuc:
        try:
            kljuc = st.secrets.get("BREVO_API_KEY", "")
        except Exception:
            pass
    return kljuc


def _brevo_posalji(kljuc, to_email, subject, html):
    payload = json.dumps({
        "sender": {"name": POSILJALAC_IME, "email": POSILJALAC_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.brevo.com/v3/smtp/email", data=payload, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json", "api-key": kljuc})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status in (200, 201, 202)


def posalji_email(to_email, subject, html):
    """Generičko slanje jednog emaila. Vraća (uspjeh, poruka)."""
    try:
        kljuc = _brevo_kljuc()
        if not kljuc:
            return False, "BREVO_API_KEY nije podešen."
        if _brevo_posalji(kljuc, to_email, subject, html):
            return True, "ok"
        return False, "Brevo nije prihvatio poruku."
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        zabiljezi_gresku(e)
        return False, f"Brevo HTTP {e.code}: {body[:300]}"
    except Exception as e:
        zabiljezi_gresku(e)
        return False, str(e)


def email_okvir(sadrzaj_html):
    """Zajednički HTML okvir (header + footer) za sve emailove."""
    return f"""
    <div style="font-family:Inter,sans-serif;max-width:520px;margin:0 auto;padding:32px">
        <div style="text-align:center;margin-bottom:24px">
            <img src="{KOMUNIKATOR_URL}/epc-logo.png" alt="Edu Pharma Community" width="64" style="width:64px;height:auto">
            <h2 style="color:#0D8A9E;margin:8px 0 0">Komunikator</h2>
            <p style="color:#64748b;margin:4px 0 0">Edu Pharma Community</p>
        </div>
        {sadrzaj_html}
        <p style="color:#64748b;font-size:13px;margin-top:24px;border-top:1px solid #e2e8f0;padding-top:16px">
            Edu Pharma Community · Farmaceutski trening
        </p>
    </div>
    """


def posalji_email_odobrenje(korisnik_email, korisnik_ime):
    sadrzaj = f"""
        <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:20px;text-align:center;margin-bottom:20px">
            <div style="font-size:18px;font-weight:600;color:#166534;margin-bottom:8px">&#10003;</div>
            <div style="font-size:18px;font-weight:600;color:#166534">Nalog odobren!</div>
        </div>
        <p style="color:#1e293b;font-size:15px;line-height:1.6">
            Poštovani/a <strong>{korisnik_ime}</strong>,
        </p>
        <p style="color:#1e293b;font-size:15px;line-height:1.6">
            Vaš nalog u <strong>Komunikatoru</strong> je odobren.
            Prijavite se emailom i lozinkom koje ste upisali u zahtjevu.
        </p>
        <p style="text-align:center;margin:24px 0">
            <a href="{KOMUNIKATOR_URL}/#/prijava" style="background:#0D8A9E;color:#ffffff;text-decoration:none;font-weight:700;padding:12px 28px;border-radius:10px;display:inline-block">Otvori Komunikator</a>
        </p>
        <p style="color:#64748b;font-size:13px;line-height:1.6">
            Na telefonu ga možete instalirati kao aplikaciju — uputstvo se pojavi čim otvorite stranicu.
        </p>
    """
    return posalji_email(
        korisnik_email,
        "Vaš nalog je odobren — Komunikator",
        email_okvir(sadrzaj),
    )


def posalji_email_masovni(to_email, korisnik_ime, subject, poruka_tekst):
    """Masovni email — čisti tekst admina pretvara u HTML unutar okvira."""
    tijelo = poruka_tekst.strip().replace("\n", "<br>")
    sadrzaj = f"""
        <p style="color:#1e293b;font-size:15px;line-height:1.6">
            Poštovani/a <strong>{korisnik_ime}</strong>,
        </p>
        <p style="color:#1e293b;font-size:15px;line-height:1.6">{tijelo}</p>
    """
    return posalji_email(to_email, subject, email_okvir(sadrzaj))


# ─── Komunikator: obavijest o novom slučaju ──────────────────────────────────
# Šalje je admin dugmetom u Komunikatoru (nikad automatski pri otključavanju):
# jedan pogrešan klik u adminu ne smije otići svim članovima. Svaki primalac
# dobija svoj email — niko ne vidi tuđe adrese.


def _esc(t):
    return (str(t or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def email_novi_slucaj(ime, sc, sid):
    """(naslov, html) obavijesti o novom slučaju za jednog člana."""
    link = f"{KOMUNIKATOR_URL}/#/slucaj/{sid}"
    pacijent = _esc(sc.get("ime", "")) + (f", {int(sc['godine'])} god." if sc.get("godine") else "")
    pozdrav = f"Poštovani/a <strong>{_esc(ime)}</strong>," if ime else "Poštovani/a,"
    html = f"""
    <div style="font-family:Inter,Segoe UI,sans-serif;max-width:520px;margin:0 auto;padding:28px 20px;color:#1e293b">
        <div style="text-align:center;margin-bottom:20px">
            <img src="{KOMUNIKATOR_URL}/epc-logo.png" alt="Edu Pharma Community" width="72" style="width:72px;height:auto">
            <h2 style="color:#0D8A9E;margin:8px 0 0">Komunikator</h2>
        </div>
        <p style="font-size:15px;line-height:1.6">{pozdrav}</p>
        <p style="font-size:15px;line-height:1.6">u Komunikatoru vas čeka <strong>novi slučaj</strong>.</p>
        <div style="background:#f1f5f9;border-radius:12px;padding:16px 18px;margin:16px 0">
            <div style="font-size:17px;font-weight:700;margin-bottom:6px">{_esc(sc.get("naziv", ""))}</div>
            <div style="font-size:14px;color:#475569;line-height:1.6">
                <strong>Pacijent:</strong> {pacijent}<br>
                <strong>Razlog dolaska:</strong> {_esc(sc.get("tegoba", ""))}
            </div>
        </div>
        <p style="font-size:15px;line-height:1.6">Imate 7 unosa i 2 minute po odgovoru. Slučaj se igra jednom,
            a ocjena dolazi s povratnom informacijom: šta je bilo dobro, šta loše i šta ste propustili.
            Prvi odigrani slučaj u mjesecu donosi i XP u Pharma Questu, ako tamo igrate s istim emailom.</p>
        <p style="text-align:center;margin:24px 0">
            <a href="{link}" style="background:#0D8A9E;color:#ffffff;text-decoration:none;font-weight:700;padding:12px 28px;border-radius:10px;display:inline-block">Otvori slučaj</a>
        </p>
        <p style="color:#64748b;font-size:12px;line-height:1.5;margin-top:24px;border-top:1px solid #e2e8f0;padding-top:14px">
            Ovaj email dobijate kao član Edu Pharma Community s pristupom Komunikatoru.
            Obavijesti o novim slučajevima isključujete u Komunikatoru → Moj nalog.
        </p>
    </div>
    """
    return f"Novi slučaj u Komunikatoru: {sc.get('naziv', '')}", html


def posalji_emailove_skupno(poruke):
    """poruke = [{"to", "subject", "html"}]. Vraća (poslano, greske).

    Brevo, jedan poziv po primaocu — svako dobija svoj email i ne vidi tuđe
    adrese. Pad jednog ne zaustavlja ostale; vraća se koliko je stvarno otišlo.
    """
    kljuc = _brevo_kljuc()
    if not kljuc:
        return 0, ["BREVO_API_KEY nije podešen."]
    poslano, greske = 0, []
    for p in poruke:
        try:
            if _brevo_posalji(kljuc, p["to"], p["subject"], p["html"]):
                poslano += 1
            else:
                greske.append(f"{p['to']}: Brevo nije prihvatio")
        except urllib.error.HTTPError as e:
            zabiljezi_gresku(e)
            greske.append(f"{p['to']}: Brevo HTTP {e.code} {e.read().decode('utf-8', errors='replace')[:150]}")
        except Exception as e:
            zabiljezi_gresku(e)
            greske.append(f"{p['to']}: {str(e)[:150]}")
    return poslano, greske
