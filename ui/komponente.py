"""Dijelovi ekrana koje koristi vise stranica."""
import streamlit as st


def prikazi_ocjenu(r):
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
