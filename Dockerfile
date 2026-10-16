# Komunikator API za Cloud Run. Streamlit aplikacija ovo NE koristi — ona ide
# na Streamlit Community Cloud iz requirements.txt kao i do sada.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt api/requirements.txt ./zavisnosti/
RUN pip install --no-cache-dir -r zavisnosti/requirements.txt \
    && pip install --no-cache-dir fastapi==0.118.0 uvicorn==0.37.0 PyJWT==2.10.1

# Samo moduli koje API stvarno uvozi — bez UI-ja, skripti, kalibracije i scenario/.
COPY konfig.py baza.py posta.py promptovi.py motor.py ocjena.py rubrika.py \
     stanje.py scenariji.py ./
COPY api/__init__.py api/javno.py api/main.py ./api/

# Ključevi dolaze kao varijable okruženja Cloud Runa, nikad iz slike.
CMD exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080} --timeout-keep-alive 75
