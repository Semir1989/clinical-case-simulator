"""Izgled aplikacije — CSS i mali HTML dodaci.

CSS zivi u stil.css da se moze uredjivati bez diranja Pythona. Ucitava se
jednom po sesiji; ako fajl nedostaje, aplikacija radi dalje bez stila umjesto
da padne.
"""
import io
import os

import streamlit as st

# Indikator za meni na mobitelu — nestaje nakon 6 sekundi.
MENI_HINT = """
<div id="menuHint" style="
    position: fixed;
    top: 18px;
    left: 62px;
    z-index: 999998;
    background: white;
    color: #1E3A8A;
    font-size: 14px;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.12);
    display: none;
    align-items: center;
    gap: 4px;
    animation: hintFade 6s ease-in-out forwards;
    pointer-events: none;
">
    <span style="font-size:16px">&#8592;</span> Meni
</div>
<style>
    @media (max-width: 768px) {
        #menuHint { display: flex !important; }
    }
    @keyframes hintFade {
        0% { opacity: 0; transform: translateX(8px); }
        8% { opacity: 1; transform: translateX(0); }
        75% { opacity: 1; }
        100% { opacity: 0; display: none; }
    }
</style>
"""


def _ucitaj_css():
    put = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stil.css")
    try:
        return io.open(put, encoding="utf-8").read()
    except OSError:
        return ""


def primijeni():
    css = _ucitaj_css()
    if css:
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    st.markdown(MENI_HINT, unsafe_allow_html=True)
