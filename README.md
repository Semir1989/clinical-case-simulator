# Clinical Case Simulator

Simulator kliničkih slučajeva za farmaceute. Polaznik vodi razgovor s pacijentom
kojeg glumi model, a nakon razgovora dobija ocjenu po rubrici s citatima iz
vlastitog transkripta.

Projekat **Edu Pharma Community**. Pristup imaju samo članovi zajednice — svaki
nalog odobrava administrator ručno. Uz to postoji besplatan demo slučaj koji
radi bez registracije i bez ijednog poziva prema modelu.

Streamlit + Supabase + Anthropic API + Resend, deploy na Streamlit Community Cloud.

---

## Struktura

Do septembra 2026. sve je živjelo u jednom fajlu od 3.281 linije. Sada:

| Modul | Šta radi |
|---|---|
| `app.py` | Ulazna tačka: podešavanje stranice, navigacija, ekran razgovora |
| `konfig.py` | Ključevi, klijenti (`ai`, `db`), Sentry, konstante, jezično pravilo |
| `baza.py` | Sve što dira Supabase: korisnici, lozinke, pokušaji, scenariji, objave |
| `posta.py` | Slanje emaila preko Resend API-ja |
| `promptovi.py` | Sistemski promptovi za pacijenta, ocjenjivača i generator |
| `motor.py` | Pozivi prema modelu |
| `ocjena.py` | Provjera dokaza i izračun ocjene — čist Python, bez Streamlita |
| `scenariji.py` | Ugrađeni scenariji + oni iz baze |
| `demo.py` | Besplatan demo slučaj, unaprijed napisan, bez API poziva |
| `stil.py` + `stil.css` | Izgled |
| `ui/` | Ekrani: prijava, ljestvica, moji rezultati, admin panel |
| `kalibracija/` | Mjerenje odstupanja ocjenjivača od referentnih ocjena |
| `arhiva/` | Stari fajlovi iz ranih verzija, ne koriste se |

Redoslijed uvoza je jednosmjeran i nema kružnih zavisnosti:

```
konfig → baza, posta → promptovi → ocjena, motor → scenariji → ui → app
```

`konfig.py` ne uvozi nijedan drugi modul projekta. Ako se to promijeni, kružne
zavisnosti su pitanje vremena.

## Pokretanje lokalno

```bash
python -m venv venv
venv/Scripts/pip install -r requirements.txt      # Linux/Mac: venv/bin/pip
venv/Scripts/python -m streamlit run app.py
```

`.env` u korijenu (nije u gitu):

```
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://<projekat>.supabase.co
SUPABASE_KEY=...
RESEND_API_KEY=...        # opciono, bez njega se emailovi ne šalju
SENTRY_DSN=...            # opciono
```

Na Streamlit Cloudu isti ključevi idu u **Settings → Secrets**, ne u `.env`.

## Testovi

```bash
venv/Scripts/python test_ocjena.py     # provjera dokaza i izračun ocjene
venv/Scripts/python test_lozinke.py    # bcrypt migracija, zaključavanje, uloge
```

Ne troše API i ne diraju bazu. Pokreću se iz korijena projekta.

Poslije svake izmjene prompta ocjenjivača pokrenuti i kalibraciju — ona **troši
API**, oko 0,02 USD po transkriptu:

```bash
venv/Scripts/python kalibracija/izvuci_referencu.py    # jednom, vadi transkripte
venv/Scripts/python kalibracija/izmjeri.py             # poslije svake izmjene
```

## Shema baze

```sql
-- Korisnici. Pristup odobrava admin: approved je false dok ga ne postavi.
create table users (
  id             uuid primary key default gen_random_uuid(),
  email          text not null unique,
  password_hash  text not null,              -- bcrypt; stari SHA-256 se migrira pri prijavi
  full_name      text,
  institution    text,
  nadimak        text,                       -- jedino ime koje se vidi na ljestvici
  role           text not null default 'korisnik',   -- korisnik | mentor | admin
  approved       boolean default false,
  suspended      boolean default false,
  failed_logins  integer not null default 0,
  locked_until   timestamptz,                -- zaključan do; 5 promašaja = 15 min
  created_at     timestamptz default now()
);
create unique index users_nadimak_uniq on users (lower(nadimak)) where nadimak is not null;

-- Jedan završen pokušaj scenarija.
create table attempts (
  id              uuid primary key default gen_random_uuid(),
  user_email      text not null,
  scenario_id     text not null,
  score           numeric not null,
  anamneza        integer,
  komunikacija    integer,
  sigurnost       integer,
  result_json     text,        -- kompletna ocjena, uključujući citate i odbačene tvrdnje
  transcript      text,        -- popunjeno tek od 2. jula 2026.
  appeal_status   text,        -- null | otvorena | prihvacena | odbijena
  appeal_text     text,
  appeal_response text,
  completed_at    timestamptz default now()
);

-- Scenariji iz admin panela. Nadjačavaju ugrađene ako dijele isti id.
create table scenarios (
  id               text primary key,
  naziv            text not null,
  ime              text,
  godine           integer,
  tegoba           text,
  terapija         text,
  skriveni_detalji text,
  crvene_zastavice text,
  ocekivano        text,
  pocetna_poruka   text,
  rubrika          text,
  active           boolean default false,
  created_at       timestamptz default now()
);

-- Potrošnja tokena: analitika, procjena troška i dnevni limit poruka.
create table usage_log (
  id          bigserial primary key,
  user_email  text,
  event       text,        -- start | poruka | evaluacija | generisanje_scenarija
  scenario_id text,
  tokens_in   integer default 0,
  tokens_out  integer default 0,
  created_at  timestamptz default now()
);

-- Baner na vrhu aplikacije.
create table announcements (
  id         bigserial primary key,
  tekst      text not null,
  tip        text default 'info',    -- info | warning
  active     boolean default true,
  created_at timestamptz default now()
);
```

RLS je uključen na svim tabelama. Aplikacija pristupa bazi serverskim ključem
koji nikad ne stiže u browser.

## Šta ne dirati bez razloga

- **Priručnik pacijenta** (`promptovi.PACIJENT_PRIRUCNIK`) je namjerno dug: prelazi
  1.024 tokena, što je prag od kojeg Anthropic API kešira prompt. Skraćivanje ga
  tiho gasi i poskupljuje svaki potez.
- **Ocjenjivač radi u dva koraka** — prvo doslovno popiše sva pitanja farmaceuta,
  pa tek onda sudi. Bez toga se vraća stara greška: model je nabrajao ono što
  *nije saznato* pod naslovom „propuštena pitanja“ i time krivio polaznika za
  odgovore koje je pacijent uskratio.
- **Ukupnu ocjenu računa Python** (`ocjena.provjeri_ocjenu`), ne model. Isto
  važi za odbacivanje tvrdnji čiji citat nije u transkriptu.
- **Demo nema nijedan API poziv.** Ako mu se ikad doda model, gubi smisao —
  postoji upravo zato da se može ostaviti otvoren svima bez troška.
- **Sentry `ThreadingIntegration` mora ostati isključena** — lomi Streamlit
  threadove.
