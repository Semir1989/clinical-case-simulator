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
| `rubrika.py` | Rubrika v2: kriteriji, kazne, izračun bodova, shema alata — čist Python |
| `SCENARIJ-V2.md` | Standard scenarija. Mijenja se **prvo ovdje**, pa u skillu i `upsert_scenarij.py` |
| `stanje.py` | Skriveno stanje pacijenta i didaskalije — takođe čist Python |
| `scenariji.py` | Ugrađeni scenariji + oni iz baze |
| `demo.py` | Besplatan demo slučaj, unaprijed napisan, bez API poziva |
| `stil.py` + `stil.css` | Izgled |
| `ui/` | Ekrani: prijava, ljestvica, moji rezultati, admin panel |
| `kalibracija/` | Mjerenje odstupanja ocjenjivača od referentnih ocjena |
| `skripte/` | Konverzija scenarija i testni skup ponašanja pacijenta |
| `arhiva/` | Stari fajlovi iz ranih verzija, ne koriste se |

Redoslijed uvoza je jednosmjeran i nema kružnih zavisnosti:

```
konfig → baza, posta → promptovi → ocjena, stanje, rubrika → scenariji → motor → ui → app
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
venv/Scripts/python test_rubrika.py    # rubrika v2: parsiranje, bodovi, kazne

# Provjera generisanog scenarija prije upisa u bazu (ne troši API):
venv/Scripts/python skripte/provjeri_scenarij.py scenario/generisani/scenarij_N.json
venv/Scripts/python test_lozinke.py    # bcrypt migracija, zaključavanje, uloge
venv/Scripts/python test_prompt.py     # gradnja prompta, persona, povratak na stari tekst
venv/Scripts/python test_stanje.py     # parsiranje skrivenog stanja i didaskalija
```

Ne troše API i ne diraju bazu. Pokreću se iz korijena projekta.

Poslije svake izmjene prompta ocjenjivača pokrenuti i kalibraciju — ona **troši
API**, oko 0,02 USD po transkriptu:

```bash
venv/Scripts/python kalibracija/izvuci_referencu.py    # jednom, vadi transkripte
venv/Scripts/python kalibracija/izmjeri.py             # poslije svake izmjene
```

Poslije izmjene priručnika pacijenta pokrenuti testni skup ponašanja — takođe
**troši API**, oko 0,005 USD po testu:

```bash
venv/Scripts/python skripte/test_ponasanja.py         # svih osam
venv/Scripts/python skripte/test_ponasanja.py 1 4     # samo odabrani
venv/Scripts/python skripte/test_otpor.py osudjujuci  # povjerenje pada, ništa se ne otkriva
venv/Scripts/python skripte/test_otpor.py empatican   # povjerenje raste, osjetljivo izlazi
```

Model nije determinističan, pa te testove ocjenjuje čovjek; automatska provjera
postoji samo tamo gdje se očekuje konkretna riječ.

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
  mode            text not null default 'ispit',  -- ispit | vjezba; ljestvica broji samo ispite
  score           numeric not null,
  anamneza        integer,
  komunikacija    integer,
  sigurnost       integer,
  result_json     text,        -- kompletna ocjena, uključujući citate i odbačene tvrdnje
  transcript      text,        -- popunjeno tek od 2. jula 2026.
  stanje_json     jsonb,       -- niz skrivenih stanja po potezu: povjerenje, faza, ishod
  appeal_status   text,        -- null | otvorena | prihvacena | odbijena
  appeal_text     text,
  appeal_response text,
  completed_at    timestamptz default now()
);

-- Razgovor u toku. Bez ovoga osvjezavanje stranice brise razgovor, a tajmer
-- nastavlja trositi poteze. Red se brise cim je pokusaj ocijenjen.
create table attempts_progress (
  id                   bigint generated always as identity primary key,
  user_email           text not null,
  scenario_id          text not null,
  mode                 text not null default 'ispit',
  broj_poteza          integer not null default 0,
  izgubljeno_ukupno    integer not null default 0,
  poruke_api           jsonb not null default '[]',
  poruke_prikaz        jsonb not null default '[]',
  stanja               jsonb not null default '[]',
  zadnje_stanje        jsonb,
  zadnji_potez_vrijeme timestamptz not null default now(),
  zapoceto_at          timestamptz not null default now(),
  azurirano_at         timestamptz not null default now(),
  unique (user_email, scenario_id, mode)
);

-- Scenariji iz admin panela. Nadjačavaju ugrađene ako dijele isti id.
create table scenarios (
  id               text primary key,
  naziv            text not null,
  ime              text,
  godine           integer,
  tegoba           text,
  terapija         text,
  skriveni_detalji text,        -- stari oblik; koristi se samo ako je cinjenice NULL
  cinjenice        jsonb,       -- [{id, cinjenica, okidac, osjetljivo}] — jedini izvor istine
  persona          jsonb default '{}',   -- kako pacijent govori, ne sta zna
  otpor            jsonb,       -- [{id, replika, redoslijed, uslov_popustanja, prag_povjerenja}]
  vidljivi_znakovi text,        -- sta se vidi bez pitanja; izvor za didaskalije
  crvene_zastavice text,
  ocekivano        text,
  pocetna_poruka   text,
  rubrika          text,
  podrucje         text,        -- filter na listi; popis vrijednosti u SCENARIJ-V2.md
  tezina           text,        -- tesko | ekspertno
  epilog           text,        -- sta se s pacijentom desilo; generise admin, jednom
  uzoran_razgovor  text,        -- kako je razgovor mogao izgledati; generise admin, jednom
  active           boolean default false,
  created_at       timestamptz default now()
);

-- Potrošnja tokena: analitika, procjena troška i dnevni limit poruka.
create table usage_log (
  id          bigserial primary key,
  user_email  text,
  event       text,        -- start | poruka | evaluacija | epilog | generisanje_scenarija
  tokens_in   integer,     -- OD 9. 9. 2026: ekvivalent punih ulaznih tokena.
                           -- Upis kesa se racuna 1,25x, citanje 0,1x. Ranije se
                           -- bilježio samo input_tokens, pa je procjena troska
                           -- bila osjetno niza od stvarne.
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
- **Činjenice imaju okidače.** Pacijent činjenicu daje čim farmaceut postavi pitanje koje
  pogađa njen okidač. Osjetljive daje na drugo pitanje ili nakon empatije — nikad ih ne
  krije zauvijek. Scenarij bez liste činjenica pada na stari tekst `skriveni_detalji`; taj
  povratak ne uklanjati dok svi scenariji nisu konvertovani.
- **Blok stanja ostaje u historiji koja ide modelu**, a skida se samo pri prikazu. Bez toga
  pacijent svaki potez počinje s povjerenjem 5 i krivulja prestaje značiti išta. Ako blok
  fali, zadržava se prethodno stanje — nagli pad bez razloga u razgovoru je gora greška.
- **Završna replika ide kao potez korisnika**, ne samo kroz sistemski prompt. Historija
  završava replikom pacijenta, pa bi model inače nastavljao tu istu repliku i vraćao prazno.
- **Prigovor bez uslova popuštanja je samo prepreka.** Svaki prigovor osim onih označenih
  `fatalno_ako_izda` mora imati uslov — inače polaznik nema šta naučiti iz toga kako ga je skinuo.
- **Persona mijenja samo KAKO pacijent govori**, nikad ŠTA zna. Ako se u personu ubaci
  klinički podatak, prestaje biti provjerljivo šta je pacijent smio otkriti.
- **Sentry `ThreadingIntegration` mora ostati isključena** — lomi Streamlit
  threadove.
