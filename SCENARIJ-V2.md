# Standard `scenarij_v2`

Jedan dokumentovan oblik scenarija. Čitaju ga i skill `/generisi-scenarij`, i
`upsert_scenarij.py`, i admin panel. Kad se polje mijenja, mijenja se **ovdje
prvo**, pa onda na ta tri mjesta.

Scenariji su nastajali u tri navrata (F0, F3, F4), pa je stariji oblik nosio
samo `skriveni_detalji` kao jedan blok teksta. Aplikacija ga i dalje prihvata —
ali scenarij bez `cinjenice`, `persona` i `otpor` gubi okidače, ličnost i
prigovore, dakle sve što razgovor čini razgovorom. **Novi scenariji se prave
isključivo u v2.**

## Polja

### Osnovno

| Polje | Tip | Obavezno | Šta je |
|---|---|---|---|
| `id` | text | da | `scenarij_N`, prvi slobodan broj |
| `naziv` | text | da | `Scenarij N — <naslov bez spojlera>` |
| `ime` | text | da | Bosansko ime pacijenta |
| `godine` | int | da | |
| `tegoba` | text | da | Razlog dolaska + kratka emocionalna nota |
| `terapija` | text | da | Ono što pacijent prizna odmah — namjerno nepotpuna slika |
| `pocetna_poruka` | text | da | Prva replika; banalan zahtjev, bez spojlera |
| `podrucje` | text | da | Vidi popis ispod |
| `tezina` | text | da | `tesko` ili `ekspertno` |

### Činjenice s okidačima (F3) — srce scenarija

`cinjenice` je niz od 6–10 objekata. Ovo je **jedini izvor istine** o pacijentu:
ono čega nema u listi, za pacijenta ne postoji.

```json
{
  "id": "tribulus",
  "cinjenica": "prije tačno dvije sedmice počeo uzimati kapsule kupljene u sportskoj prodavnici",
  "okidac": "pitanje uzima li dodatke prehrani, biljne preparate ili nešto s interneta",
  "osjetljivo": true
}
```

- `id` — kratka oznaka bez dijakritike; pacijent je upisuje u blok stanja kad
  činjenicu otkrije, pa mora biti stabilna i pamtljiva.
- `okidac` — pitanje koje je otključava. Piše se **šire nego doslovno**: „uzimate
  li još nešto" mora pokrivati suplemente. Preuzak okidač pravi igru pogađanja.
- `osjetljivo: true` — pacijent to prešućuje iz stida ili straha. Daje se na
  drugo postavljanje istog pitanja, ili odmah ako je farmaceut objasnio zašto
  pita. **Nikad se ne prešućuje zauvijek.**

Bar dvije činjenice moraju biti osjetljive, i bar jedna mora biti ona koja
otključava rješenje.

### Persona (F3) — kako govori, ne šta zna

```json
{
  "pricljivost": 3,
  "obrazovanje": "srednje",
  "raspolozenje": "umoran",
  "zurba": true,
  "zanimanje": "penzioner, radio kao vozač",
  "porodica": "oženjen, unuci",
  "odnos_prema_lijekovima": "prirodne preparate ne smatra lijekovima"
}
```

`pricljivost` 1–5. Persona **nikad** ne mijenja šta pacijent zna — samo ton,
dužinu odgovora i kome vjeruje.

### Otpor (F4) — prigovori s uslovom popuštanja

```json
{
  "redoslijed": 1,
  "replika": "Ma dobro, ali meni to pomaže, koristim već mjesecima.",
  "uslov_popustanja": "objasni konkretno šta se dešava ako nastavi",
  "prag_povjerenja": 5,
  "fatalno_ako_izda": false
}
```

Prigovori se iznose **jedan po replici**, redom. `fatalno_ako_izda: true` znači
da se taj prigovor ne povlači nikad — koristi se za zahtjev koji farmaceut ne
smije ispuniti.

### Vidljivi znakovi (F4)

`vidljivi_znakovi` — tekst; šta se na pacijentu vidi bez pitanja. Izvor za
didaskalije (`[žmirka na svjetlo]`). Bez ovoga pacijent stoji kao kip.

### Klinički okvir

| Polje | Šta je |
|---|---|
| `crvene_zastavice` | Šta se mora prepoznati + mehanizam (imenuj enzim/receptor) + ispravna akcija |
| `ocekivano` | Koraci savjetovanja, redom |
| `rubrika` | Format ispod — parsira ga `rubrika.py` |
| `obrazlozenje` | Za admina: sažetak case reporta, pedagoški cilj, gdje je lažni trag. **Ne upisuje se u bazu** |

### Rubrika — format se ne improvizuje

`rubrika.py` je parsira u kriterije i kazne, pa svako odstupanje tiho gubi
kriterij. Bez dijakritike unutar rubrike.

```
Ocijeni po ovim kategorijama (svaka 0-10):

ANAMNEZA (tezina 0.4): <5 kriterija za OVAJ slucaj, svaki (2)>
KAZNA: bez <kljucnog pitanja> max N/10; bez <drugog> max N/10

KOMUNIKACIJA (tezina 0.3): jezik laika(2), empatija bez osudjivanja(2), provjerio razumijevanje(2), strukturisan razgovor(2), jasna poruka(2)

SIGURNOST (tezina 0.3): <4 kriterija za OVAJ slucaj, bodovi u zbiru 10>
KAZNA: <fatalna greska> = 0/10 za Sigurnost; <ozbiljna greska> = max 3/10 za Sigurnost
```

Pravila koja parser i bodovanje traže:

1. Bodovi po kategoriji moraju dati **tačno 10**.
2. Kriterij se piše kao `opis(bodovi)` — zarezi unutar opisa su dozvoljeni.
3. Kazna koja počinje s „bez" tretira se kao **propust** i veže se za kriterij
   koji spominje; svaka druga je **radnja** koju model mora prijaviti s citatom.
4. **Kazna mora spominjati riječi iz kriterija na koji se odnosi.** Ako ne
   spominje, ostaje nevezana i nikad se ne pali — radije propuštena kazna nego
   lažna optužba. Provjeri to poslije generisanja (vidi ispod).

### Epilog (F6)

`epilog` i `uzoran_razgovor` se **ne pišu ručno** — generiše ih admin panel
jednom po scenariju, dugmetom „Generiši epilog".

## Područja

`podrucje` mora biti jedno od:

```
trudnoca_dojenje | kardio_interakcije | geriatrija | mentalno_zdravlje
pedijatrija | otc_zloupotreba | dermatologija
```

Cilj raspodjele: trudnoća i dojenje 2, kardio i interakcije 3, geriatrija 2,
mentalno zdravlje 2, pedijatrija 2, OTC zloupotreba 2, dermatologija 1.

## Provjera prije upisa

```bash
venv/Scripts/python skripte/provjeri_scenarij.py scenario/generisani/scenarij_N.json
```

Skripta provjerava sve gore navedeno i **odbija upis** ako rubrika ne daje 10
bodova po kategoriji, ako kazna ostane nevezana, ako nema osjetljivih činjenica
ili ako `podrucje`/`tezina` nisu iz popisa. Ne troši API.
