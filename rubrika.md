# Rubrika za ocjenjivanje — Clinical Case Simulator

## Formula

```
Ukupna ocjena = Anamneza × 0.4 + Komunikacija × 0.3 + Sigurnost × 0.3
```

Svaka kategorija se ocjenjuje od **0 do 10**.

---

## Kategorija 1: Anamneza (težina 0.4)

Farmaceut mora prikupiti dovoljno informacija da donese ispravnu kliničku odluku.

| Bodovi | Kriterij |
|--------|----------|
| 2 | Pitao za **trajanje tegobe** (koliko dugo traje svrbež/problem) |
| 2 | Pitao za **trenutnu terapiju** — šta već koristi na koži i koliko dugo |
| 2 | Pitao o **trudnoći / posebnim stanjima** (gestacijska sedmica, dojenje, hronične bolesti) |
| 2 | Pitao za **alergije** ili prethodne reakcije na lijekove |
| 2 | **Prepoznao crvene zastavice** iz odgovora (kontraindikacija, dugotrajna primjena, vidljive promjene na koži) |

**Maksimum: 10 bodova**

> Ako farmaceut nije pitao o trudnoći, maksimalna ocjena za Anamnezu je **4/10**.
> Ako nije pitao šta pacijent već koristi, maksimalna ocjena je **6/10**.

---

## Kategorija 2: Komunikacija (težina 0.3)

Farmaceut mora komunicirati jasno, empatično i prilagođeno pacijentu.

| Bodovi | Kriterij |
|--------|----------|
| 2 | Koristio **razumljiv jezik laika** (izbjegao ili objasnio stručne termine) |
| 2 | **Empatičan ton** — nije paničio, nije osuđivao, pacijent se nije osjećao postiđeno |
| 2 | **Provjerio razumijevanje** (npr. "Jeste li razumjeli zašto je ovo važno?" ili slično) |
| 2 | **Strukturisan razgovor** — logičan slijed pitanja, nije skakao s teme na temu |
| 2 | **Jasno prenio poruku** o potrebi prekida terapije i odlaska ljekaru, bez zbunjivanja |

**Maksimum: 10 bodova**

---

## Kategorija 3: Sigurnost preporuke (težina 0.3)

Farmaceut mora donijeti klinički ispravnu i sigurnu odluku.

| Bodovi | Kriterij |
|--------|----------|
| 3 | **Odbio izdati Clobetasol** (ili drugi superpotentni TC) bez recepta trudnici |
| 3 | **Jasno rekao da oba preparata treba odmah prekinuti** (Clobetasol + Zalim losion) |
| 2 | **Nije preporučio zamjensku terapiju** bez ljekarskog pregleda |
| 2 | **Uputio na pregled** — ginekolog i/ili dermatolog, uz objašnjenje zašto hitno |

**Maksimum: 10 bodova**

> Ako je farmaceut ipak izdao ili predložio kortikosteroid bez recepta trudnici = **automatski 0/10** za Sigurnost.
> Ako je preporučio bilo kakvu zamjenu bez pregleda = maksimum **5/10** za Sigurnost.

---

## Primjer izračuna ocjene

**Primjer A — Dobro savjetovanje:**
- Anamneza: 9/10 × 0.4 = 3.6
- Komunikacija: 8/10 × 0.3 = 2.4
- Sigurnost: 10/10 × 0.3 = 3.0
- **Ukupno: 9.0/10**

**Primjer B — Propustio pitati o trudnoći:**
- Anamneza: 4/10 × 0.4 = 1.6
- Komunikacija: 7/10 × 0.3 = 2.1
- Sigurnost: 3/10 × 0.3 = 0.9 (nije prepoznao kontraindikaciju jer nije znao za trudnoću)
- **Ukupno: 4.6/10**

**Primjer C — Izdao Clobetasol bez recepta:**
- Anamneza: 6/10 × 0.4 = 2.4
- Komunikacija: 6/10 × 0.3 = 1.8
- Sigurnost: 0/10 × 0.3 = 0.0
- **Ukupno: 4.2/10**

---

## Lista propuštenih pitanja (za evaluator)

Evaluator treba označiti koja od sljedećih pitanja farmaceut NIJE postavio:

- [ ] Koliko dugo traju tegobe?
- [ ] Šta trenutno koristite na toj koži?
- [ ] Koliko dugo koristite te preparate?
- [ ] Jeste li trudni ili dojite?
- [ ] U kojoj ste sedmici trudnoće?
- [ ] Imate li alergije na lijekove?
- [ ] Jeste li bili kod ljekara zbog ovog problema?
- [ ] Jeste li primijetili promjene na koži (crvenilo, mrlje, strije)?

---

## Napomena za evaluator-Claude

Pri ocjenjivanju transkripta, evaluator treba:

1. Pročitati cijeli razgovor između farmaceuta i pacijenta
2. Za svaki kriterij u tabeli — provjeriti da li je farmaceut ispunio uvjet (DA/NE/DJELIMIČNO)
3. Dodijeliti bodove prema gornjoj skali
4. Primijeniti penalizacijska pravila (trudnoća, izdavanje Clobetasola)
5. Izračunati ukupnu ocjenu po formuli
6. Navesti konkretne propuštene radnje i prijedloge za poboljšanje

Ton povratne informacije treba biti **konstruktivan i edukativan** — cilj je razvoj, ne kažnjavanje.
