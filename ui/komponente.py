"""Dijelovi ekrana koje koristi vise stranica."""
import html

import streamlit as st

from stanje import ISHODI, krivulja_povjerenja, razdvoji_didaskalije


def prikazi_repliku(tekst, uloga="assistant"):
    """Replika pacijenta s didaskalijama odvojenim od govora.

    Didaskalije su ono sto se vidi za pultom — [zmirka na svjetlo]. Prikazuju
    se sivim kurzivom da se ne citaju kao izgovorene rijeci.
    """
    if uloga != "assistant":
        st.markdown(tekst)
        return
    for vrsta, dio in razdvoji_didaskalije(tekst):
        if vrsta == "didaskalija":
            st.markdown(
                f"<div style='color:#94a3b8;font-style:italic;font-size:13.5px;"
                f"margin:2px 0 6px'>{html.escape(dio)}</div>",
                unsafe_allow_html=True)
        else:
            st.markdown(dio)


def prikazi_povjerenje(stanja):
    """Krivulja povjerenja kroz razgovor — pokazuje gdje je komunikacija popustila."""
    krivulja = krivulja_povjerenja(stanja)
    if len(krivulja) < 2:
        return
    # Skala je uvijek 0-10, ne relativna na najvecu vrijednost: inace povjerenje
    # 5 i 6 izgledaju skoro jednako i krivulja prestaje nesto znaciti.
    stupci = "".join(
        f"<div title='potez {i + 1}: {v}/10' style='flex:1;display:flex;align-items:flex-end'>"
        f"<div style='width:100%;height:{max(4, int(v / 10 * 46))}px;border-radius:3px 3px 0 0;"
        f"background:{'#16a34a' if v >= 6 else ('#f59e0b' if v >= 4 else '#ef4444')}'></div></div>"
        for i, v in enumerate(krivulja))
    st.markdown(
        "<div style='margin:10px 0 18px'>"
        "<div style='font-size:13px;color:#64748b;margin-bottom:6px'>"
        "Povjerenje pacijenta kroz razgovor</div>"
        f"<div style='display:flex;gap:3px;align-items:flex-end;height:50px'>{stupci}</div>"
        f"<div style='display:flex;justify-content:space-between;font-size:11px;"
        f"color:#94a3b8;margin-top:4px'><span>prvi potez: {krivulja[0]}/10</span>"
        f"<span>na kraju: {krivulja[-1]}/10</span></div></div>",
        unsafe_allow_html=True)


def prikazi_ishod(stanja):
    ishod = ""
    for s in reversed(stanja or []):
        if s.get("ishod"):
            ishod = s["ishod"]
            break
    if not ishod:
        return
    boje = {"prihvatio": ("#16a34a", "#f0fdf4"), "prihvatio_nevoljko": ("#f59e0b", "#fffbeb"),
            "odbio": ("#ef4444", "#fef2f2"), "otisao_s_lijekom": ("#b91c1c", "#fef2f2")}
    boja, poz = boje.get(ishod, ("#64748b", "#f8fafc"))
    st.markdown(
        f"<div style='background:{poz};border-left:4px solid {boja};padding:12px 16px;"
        f"border-radius:8px;margin:8px 0 16px'>"
        f"<div style='font-size:12px;color:#64748b;letter-spacing:.5px;text-transform:uppercase'>"
        f"Ishod razgovora</div>"
        f"<div style='font-weight:700;color:{boja};font-size:16px;margin-top:2px'>"
        f"{ISHODI.get(ishod, ishod)}</div></div>",
        unsafe_allow_html=True)


def prikazi_ocjenu(r, stanja=None):
    ukupno = float(r.get("ukupna_ocjena", 0))
    boja = "#22c55e" if ukupno >= 7 else ("#f59e0b" if ukupno >= 5 else "#ef4444")
    bg = "#f0fdf4" if ukupno >= 7 else ("#fffbeb" if ukupno >= 5 else "#fef2f2")
    st.markdown(f"""
    <div style="background:{bg};border-radius:20px;padding:28px;text-align:center;
         margin:20px 0;border:2px solid {boja}22">
        <div style="font-size:48px;font-weight:800;color:{boja};line-height:1;margin-top:8px">
            {ukupno:.1f}
            <span style="font-size:22px;color:#94a3b8;font-weight:400">/10</span>
        </div>
        <div style="color:#64748b;font-size:15px;font-weight:500;margin-top:8px">Ukupna ocjena savjetovanja</div>
    </div>
    """, unsafe_allow_html=True)

    prikazi_ishod(stanja)
    prikazi_povjerenje(stanja)

    col1, col2, col3 = st.columns(3)
    col1.metric("Anamneza ×0.4", f"{r.get('anamneza', 0)}/10")
    col2.metric("Komunikacija ×0.3", f"{r.get('komunikacija', 0)}/10")
    col3.metric("Sigurnost ×0.3", f"{r.get('sigurnost', 0)}/10")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if r.get("pohvale"):
        st.markdown("#### Šta ste uradili dobro")
        for p in r["pohvale"]:
            if isinstance(p, dict):
                st.success(p.get("tekst", ""))
                if p.get("citat"):
                    st.caption(f"iz razgovora: „{p['citat']}“")
            else:
                st.success(p)

    # Pitanja koja jesu postavljena, a pacijent ih je izbjegao. Ovo se NE
    # kažnjava — prikazuje se da polaznik vidi gdje ga je pacijent odveo.
    if r.get("pitano_ali_neodgovoreno"):
        st.markdown("#### Pitali ste, ali niste dobili odgovor")
        st.caption("Ovo nije propust — pacijent je uskratio odgovor. Vrijedi vidjeti kako je to izveo.")
        for p in r["pitano_ali_neodgovoreno"]:
            if not isinstance(p, dict):
                continue
            st.info(
                f"**{p.get('pitanje','')}**\n\n"
                f"Vi: „{p.get('citat_farmaceuta','')}“\n\n"
                f"Pacijent: {p.get('reakcija_pacijenta','')}"
            )

    nije = r.get("nije_pitano") or r.get("propustena_pitanja")
    if nije:
        st.markdown("#### Niste pitali")
        for p in nije:
            if isinstance(p, dict):
                zasto = p.get("zasto_vazno", "")
                st.warning(f"**{p.get('pitanje','')}**" + (f"\n\n{zasto}" if zasto else ""))
            else:
                st.warning(p)

    if r.get("smjernice"):
        st.markdown("#### Smjernice za poboljšanje")
        for s in r["smjernice"]:
            st.info(s)
