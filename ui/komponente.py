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


def prikazi_pravila(je_ispit, max_poteza):
    """Ekran s pravilima prije početka. Vraća True kad polaznik klikne „Počni“.

    Tajmer je ranije kretao onog trenutka kad se stranica otvori, pa je
    polaznik gubio poteze dok je još čitao ko mu je pacijent.
    """
    pravila = [
        f"Imate **{max_poteza} unosa**. Svaka vaša poruka troši jedan.",
        ("Na svaki odgovor imate **2 minute**. Istek ne briše razgovor, ali troši jedan unos."
         if je_ispit else "**Bez tajmera** — vježba se ne mjeri vremenom."),
        ("Rezultat ide na **ljestvicu** i scenarij se igra **samo jednom**."
         if je_ispit else "Rezultat **ne ide** na ljestvicu i vježbu možete ponoviti."),
        "Pacijent ne otkriva sve sam. Neke stvari kaže tek kad ga pitate — a neke tek "
        "kad mu objasnite zašto pitate.",
        "**Fatalne greške postoje.** Preporuka pogrešnog preparata može oboriti sigurnost na nulu.",
        "Razgovor se čuva — ako vam padne veza ili zatvorite stranicu, nastavljate gdje ste stali.",
    ]
    st.markdown(
        '<div style="background:white;border-radius:14px;padding:20px 24px;margin:12px 0;'
        'box-shadow:0 1px 4px rgba(0,0,0,0.07)">'
        '<div style="font-weight:700;color:#1e293b;margin-bottom:12px">Prije nego počnete</div>'
        + "".join(
            '<div style="font-size:14px;color:#475569;line-height:1.6;margin-bottom:9px">'
            f'• {p}</div>' for p in pravila)
        + '</div>', unsafe_allow_html=True)

    return st.button("Počni", type="primary", use_container_width=True)


BOJE_STATUSA = {
    "DA":         ("#16a34a", "#dcfce7", "DA"),
    "DJELIMICNO": ("#b45309", "#fef3c7", "DJELIMIČNO"),
    "NE":         ("#dc2626", "#fee2e2", "NE"),
}

REDOSLIJED_KATEGORIJA = ("anamneza", "komunikacija", "sigurnost")


def prikazi_kriterije(r):
    """Tabela: kriterij, status i doslovan citat iz vlastitog razgovora.

    Ovo je jezgro ocjenjivača v2 — polaznik prvi put vidi ZAŠTO je dobio
    ocjenu, a ne samo koliku. Prikazuje se samo za ocjene v2; stariji zapisi
    u bazi nemaju kriterije i idu kroz stari prikaz ispod.
    """
    kriteriji = r.get("kriteriji")
    if not kriteriji:
        return

    st.markdown("#### Ocjena po kriterijima")
    st.caption("Svaki priznat kriterij nosi citat iz vašeg razgovora. Ako mislite da je "
               "neki kriterij pogrešno ocijenjen, uložite žalbu ispod — administrator vidi "
               "tačno koji je sporan.")

    po_kategoriji = {}
    for kid, k in kriteriji.items():
        po_kategoriji.setdefault(k.get("kategorija", ""), []).append((kid, k))

    kazne = {}
    for kz in r.get("kazne_primijenjene") or []:
        kazne.setdefault(kz.get("kategorija", ""), []).append(kz)

    for kat_id in REDOSLIJED_KATEGORIJA:
        stavke = po_kategoriji.get(kat_id)
        if not stavke:
            continue
        stavke.sort(key=lambda p: p[0])
        naziv = stavke[0][1].get("naziv_kategorije", kat_id.capitalize())

        redovi = []
        for _, k in stavke:
            boja, pozadina, oznaka = BOJE_STATUSA.get(k.get("status", "NE"), BOJE_STATUSA["NE"])
            citat = html.escape(k.get("citat") or "")
            obrazlozenje = html.escape(k.get("obrazlozenje") or "")
            # Sve u jednom redu i bez uvlaka: Streamlit uvucen HTML prikaze kao
            # blok koda umjesto da ga iscrta.
            dokaz = (f'<div style="color:#475569;font-size:13px;margin-top:6px;'
                     f'border-left:3px solid {boja}44;padding-left:10px">„{citat}“</div>'
                     if citat else "")
            napomena = (f'<div style="color:#64748b;font-size:13px;margin-top:6px">'
                        f'{obrazlozenje}</div>' if obrazlozenje else "")
            redovi.append(
                '<div style="display:flex;gap:12px;padding:12px 0;border-top:1px solid #eef2f7">'
                f'<div style="flex:0 0 96px"><span style="background:{pozadina};color:{boja};'
                'font-size:11px;font-weight:700;padding:3px 8px;border-radius:6px;'
                f'white-space:nowrap">{oznaka}</span></div>'
                '<div style="flex:1;min-width:0">'
                f'<div style="color:#1e293b;font-size:14px">{html.escape(k.get("tekst", ""))}</div>'
                f'{dokaz}{napomena}</div>'
                '<div style="flex:0 0 44px;text-align:right;color:#94a3b8;font-size:13px">'
                f'{k.get("bodovi", 0):g}</div>'
                '</div>')

        st.markdown(
            '<div style="background:white;border-radius:14px;padding:6px 20px 16px;'
            'margin-bottom:14px;box-shadow:0 1px 4px rgba(0,0,0,0.06)">'
            '<div style="font-weight:700;color:#1e293b;padding:14px 0 2px">'
            f'{naziv} · {r.get(kat_id, 0)}/10</div>'
            + "".join(redovi) + '</div>', unsafe_allow_html=True)

        for kz in kazne.get(kat_id, []):
            st.warning(f"Kazna iz rubrike: **{kz.get('opis', '')}** — "
                       f"ocjena ove kategorije ograničena je na {kz.get('max', 0):g}/10.")


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

    prikazi_kriterije(r)

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

    # Kod ocjene v2 propusti su vec u tabeli kriterija — ne ponavljaju se.
    nije = None if r.get("kriteriji") else (r.get("nije_pitano") or r.get("propustena_pitanja"))
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
