# Komunikator API za Cloud Run. Streamlit aplikacija ovo NE koristi — ona ide
# na Streamlit Community Cloud iz requirements.txt kao i do sada.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Oba fajla se zovu requirements.txt — u istom folderu drugi bi prepisao prvi.
# Zato idu pod svojim putanjama; api/requirements.txt poziva ../requirements.txt.
COPY requirements.txt ./
COPY api/requirements.txt ./api/
RUN pip install --no-cache-dir -r api/requirements.txt

# Samo moduli koje API stvarno uvozi — bez UI-ja, skripti, kalibracije i scenario/.
COPY konfig.py baza.py posta.py promptovi.py motor.py ocjena.py rubrika.py \
     stanje.py scenariji.py ./
COPY api/__init__.py api/javno.py api/main.py api/admin.py ./api/

# Ključevi dolaze kao varijable okruženja Cloud Runa, nikad iz slike.
CMD exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080} --timeout-keep-alive 75
