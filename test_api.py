"""
Faza 1 — Test poziv prema Claude API-ju.
Provjerava da ključ i SDK rade ispravno.
"""

import os
from anthropic import Anthropic
from dotenv import load_dotenv

# Učitaj API ključ iz .env fajla
load_dotenv()

# Inicijalizuj klijenta (automatski čita ANTHROPIC_API_KEY iz okruženja)
client = Anthropic()

# Pošalji kratku poruku modelu
odgovor = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=256,
    messages=[
        {"role": "user", "content": "Reci 'Zdravo, Clinical Case Simulator radi!' na bosanskom."}
    ]
)

# Ispiši odgovor u terminalu
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print("Odgovor modela:")
print(odgovor.content[0].text)
