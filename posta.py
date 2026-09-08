"""Slanje emaila preko Resend HTTP API-ja."""
import json
import os
import urllib.error
import urllib.request

import streamlit as st

from konfig import zabiljezi_gresku

# ─── Email notifikacije (Resend) ─────────────────────────────────────────────
def posalji_email(to_email, subject, html):
    """Generičko slanje jednog emaila preko Resend HTTP API-ja."""
    try:
        api_key = st.secrets.get("RESEND_API_KEY", "")
        from_email = st.secrets.get("RESEND_FROM", "onboarding@resend.dev")

        if not api_key:
            return False, "RESEND_API_KEY nije konfigurisan u secrets."

        payload = json.dumps({
            "from": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html,
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status in (200, 201):
                return True, "ok"
            else:
                return False, f"Resend status: {resp.status}"
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        zabiljezi_gresku(e)
        return False, f"Resend HTTP {e.code}: {body}"
    except Exception as e:
        zabiljezi_gresku(e)
        return False, str(e)


def email_okvir(sadrzaj_html):
    """Zajednički HTML okvir (header + footer) za sve emailove."""
    return f"""
    <div style="font-family:Inter,sans-serif;max-width:520px;margin:0 auto;padding:32px">
        <div style="text-align:center;margin-bottom:24px">
            <h2 style="color:#1E3A8A;margin:0">Clinical Case Simulator</h2>
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
            Vaš nalog na platformi <strong>Clinical Case Simulator</strong> je odobren.
            Sada se možete prijaviti i započeti rad na kliničkim scenarijima.
        </p>
    """
    return posalji_email(
        korisnik_email,
        "Vaš nalog je odobren — Clinical Case Simulator",
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
