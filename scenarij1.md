# Scenarij 1: Trudnica i topikalni kortikosteroidi

## Podaci o pacijentu

- **Ime i godine:** Lejla, 18 godina
- **Gestacija:** 33. sedmica trudnoće (primigravida — prva trudnoća)
- **Glavna tegoba:** Svrbež i peckanje kože na grudima već oko 6 mjeseci
- **Trenutna terapija:** Nije na hroničnoj terapiji (vitamini za trudnoću)
- **Šta sama već koristi (skriveno):** Zalim losion (fenol + tinktura joda + kristal violet) i Clobetasol propionat 0.05% krema — kupila ih sama u apoteci prije 2 sedmice, koristi svakodnevno

---

## Kako pacijent dolazi u apoteku

Lejla dolazi po još jedan tub Clobetasol kreme (kaže da joj ponestaje) i pita ima li nešto "jače" jer svrbež traje. Izgleda blago zabrinuto. Trudnoća je vidljiva.

---

## Skriveni detalji (otkrij SAMO na pravo pitanje)

- Svrbež je počeo **6 mjeseci ranije** (dakle, koristila je proizvode mnogo duže nego što kaže na početku)
- Na koži su se pojavile **strije, sjajne mrlje i crvenilo** — misli da je to od trudnoće
- **Nije konzultovala ljekara** — kupila je preparate sama, po preporuci komšinice
- Zalim losion i kortikosteroidnu kremu koristi **zajedno, svakodnevno**, na isto mjesto
- Pita koliko još smije koristiti — boji se da će koža "ostati takva"

---

## Crvene zastavice — kada odmah uputiti ljekaru

1. **Trudnoća + superpotentni topikalni kortikosteroid** (Clobetasol 0.05%) = apsolutna kontraindikacija; rizik od supresije HPA osi i fetotoksičnosti
2. **Zalim losion u trudnoći** = fenol se apsorbira kroz kožu i djeluje kaustično; potencijalno teratogeno
3. **6 mjeseci kontinuirane primjene** = atrofija kože, telangiektazije, strije već nastupaju (nuspojave su aktivne)
4. **Vidljive promjene na koži** = dermatološka hitnost; treba dermatolog + ginekolog
5. **Samoliječenje bez nadzora u trudnoći** = uvijek crvena zastavica

---

## Ispravan put savjetovanja (bilješka za evaluator)

Farmaceut MORA:

1. Pitati o trudnoći i gestacijskoj sedmici (ako nije odmah vidljivo, pitati direktno)
2. Pitati šta trenutno koristi na koži i koliko dugo
3. Prepoznati Clobetasol kao superpotentni TC — kontraindiciran u trudnoći, posebno na velikoj površini
4. Prepoznati Zalim losion kao potencijalno štetan (fenol, kaustično djelovanje, resorpcija)
5. Jasno reći da oba preparata treba odmah prekinuti
6. NE preporučivati nikakvu zamjenu bez ljekarske konzultacije
7. Uputiti hitno ginekologu i dermatologu
8. Objasniti rizik na razumljiv način, bez izazivanja panike

Farmaceut NE SMIJE:
- Izdati Clobetasol bez recepta u trudnoći
- Preporučiti "blažu" alternativu bez ljekarskog pregleda
- Reći "to sigurno nije ništa ozbiljno" i pustiti je s preparatima

---

## Napomena za prilagodbu u kodu (pacijent_agent.py)

```python
IME = "Lejla"
GODINE = 18
TEGOBA = "svrbež i peckanje kože na grudima, dolazi po još Clobetasol kremu"
TERAPIJA = "vitamini za trudnoću (33. sedmica trudnoće, prva trudnoća)"
SKRIVENI_DETALJI = (
    "već 6 mjeseci koristi Zalim losion i Clobetasol 0.05% kremu zajedno svakodnevno na grudima; "
    "na koži su se pojavile strije i sjajne mrlje koje pripisuje trudnoći; "
    "nije bila kod ljekara, preparate je uzela po preporuci komšinice; "
    "boji se da će koža ostati oštećena"
)
CRVENE_ZASTAVICE = (
    "Clobetasol 0.05% je superpotentni TC — kontraindiciran u trudnoći; "
    "Zalim losion (fenol) toksičan i resorptivan — kontraindiciran u trudnoći; "
    "6 mjeseci primjene = aktivne nuspojave (atrofija, strije, telangiektazije); "
    "hitno uputiti ginekologu i dermatologu; ne izdavati Clobetasol bez recepta"
)
```
