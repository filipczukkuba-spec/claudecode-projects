# Launch posts — rules-compliant

Each platform has different self-promo rules. These scripts respect them.

## Universal rules

1. **Always disclose** that it's your project ("zrobiłem", "stworzyłem")
2. **Lead with value**, not the link
3. **Reply to comments** for 24h after posting — engagement boosts ranking
4. **Don't post the same thing to 10 places in one hour** — looks like spam
5. **Stagger by 1-2 days** between platforms

---

## 1. Wykop.pl

**Wykop rules:** self-promotion allowed but flag with `#autopromo`. Microblogi tolerate it; "Znaleziska" need 25 upvotes ("wykop") to hit main page. Best window: weekday 09:00–11:00 or 19:00–22:00.

**Tag with:** `#oszczedzanie` `#zakupy` `#biedronka` `#lidl` `#ai` `#autopromo` `#programista15k` (last one if developer angle)

### Mikroblog post (start here — lower barrier)

```
Zrobiłem porównywarkę cen w 7 sklepach (Biedronka, Lidl, Kaufland, Aldi,
Netto, Auchan, Carrefour). Skanujesz paragon telefonem, AI czyta, a apka
mówi gdzie miałeś zapłacić mniej.

Codzienna synchronizacja z gazetek online + społecznościowe ceny z paragonów.
Bez logowania, bez reklam, bez aplikacji do instalowania.

Link w komentarzu (żeby nie wyglądało jak spam).

#oszczedzanie #zakupy #autopromo #ai
```

Then in first comment:
```
👉 taniejkupuj.pl

Daję feedback? Najbardziej zależy mi na info które sklepy zostawić, a
których odpuścić. Lidl i Biedronka mają mniej danych bo blokują scraping —
dlatego zrobiłem ten skaner paragonów.
```

### Znalezisko post (only if mikroblog gets traction)

**Tytuł** (max 80 znaków):
```
AI czyta moje paragony i pokazuje gdzie mogłem zapłacić mniej
```

**Opis** (max 1500 znaków):
```
Tydzień robiłem porównywarkę cen w 7 polskich sklepach (Biedronka, Lidl,
Kaufland, Aldi, Netto, Auchan, Carrefour). Jest gotowa, działa, jest
darmowa.

Co potrafi:
• Wpisujesz listę zakupów → sprawdza ceny w 7 sklepach → mówi gdzie taniej
• Skanujesz paragon → AI (Claude Vision) wyciąga ceny → trafiają do bazy
  i pomagają innym
• Wkleisz przepis z neta → wyciąga składniki i porównuje koszty

Co ważne:
• Bez logowania, bez instalacji, bez reklam
• Ceny aktualizowane codziennie z gazetek online
• Lidl i Biedronka blokują scraping — dlatego ten skaner paragonów,
  społecznościowo robimy lepsze dane niż osobno

Stack: Next.js + Supabase + Claude API. Pisałem solo.
Mile widziany feedback, najbardziej zależy mi na realnych użytkownikach.

taniejkupuj.pl

#autopromo
```

---

## 2. Reddit

Reddit's 9:1 rule means for every self-promo post you need 9 regular
contributions. If your account is new, post once in r/SideProject or
r/programowanie first as a "show & tell" — less strict, easier first win.

### r/Polska (tough — needs value framing)

Title:
```
Stworzyłem darmową porównywarkę cen 7 polskich sklepów — szukam testerów i opinii
```

Body:
```
Cześć,

Spędziłem ostatni miesiąc robiąc porównywarkę cen produktów spożywczych
w 7 sklepach (Biedronka, Lidl, Kaufland, Aldi, Netto, Auchan, Carrefour).

Trzy powody dlaczego to zrobiłem:
1. Pricena.pl umarła, Promocje.pl skupiają się tylko na gazetkach
2. Większość porównywarek wymaga logowania i wciska reklamy
3. Chciałem sprawdzić jak daleko zajdę z AI w roli OCR-a

Jak to działa:
- Wpisujesz listę → porównanie cen w 7 sklepach
- Skanujesz paragon → AI czyta i dodaje prawdziwe ceny z półki
- Wklejasz przepis → wyciąga składniki

Strona: taniejkupuj.pl  
(zero reklam, zero logowania, zero apki do instalacji)

Najbardziej potrzebuję feedbacku:
• Czy jest sklep który powinien być a go nie ma?
• Które produkty są nieczytane / źle czytane?
• Co mnie odróżni od pricena/promocje jak wrócą?

Dzięki za poświęcony czas 🙏
```

**Important:** when you post, immediately reply to a few existing posts in
the subreddit so it doesn't look drive-by.

### r/programowanie (easier — dev "show & tell")

Title:
```
[Show] Porównywarka cen 7 polskich sklepów + skaner paragonów — Next.js + Claude Vision
```

Body:
```
TL;DR: zrobiłem porównywarkę cen w 7 sklepach (Biedronka/Lidl/Kaufland/
Aldi/Netto/Auchan/Carrefour) z OCR paragonów przez Claude Vision.
taniejkupuj.pl

Najciekawsze techniczne wyzwania:

1. SCRAPING — Lidl i Biedronka mają agresywnego Cloudflare'a. Próbowałem
   Firecrawl, Jina, ScrapingBee. Dla Biedronki pomogło użycie Jina (czyta
   raw text, omija JS overlaye), dla Lidla nic nie pomaga. Stąd skaner
   paragonów.

2. PARAGONY — Polskie paragony fiskalne mają specyfikę:
   - "0.63 x 14.99 = 9.44" → cena za kg, nie za sztukę
   - "*" / "RABAT" → to promocja, nie regularna cena
   - Kupony i Lidl Plus zniżki → trzeba je wykluczyć z głównych cen
   - NIP + NR paragonu jako dedup (lepsze niż hash obrazu)

3. WALIDACJA — sumowanie pozycji vs SUMA PLN (±2 zł tolerancja) wycina
   90% złych skanów. Plus outlier rejection (5x mediana = drop).

4. CROSS-STORE CALIBRATION — jak Lidl Cukinia = 8.99 z paragonu, to
   estymowana cena 3.50 w innych sklepach jest absurdalna. Liczę
   baseline (Biedronka = 1.0, Lidl = 0.97, etc.) i podbijam estymaty.

Stack: Next.js 16 App Router, Supabase, Claude Haiku 4.5 (Vision),
Resend, Vercel. Solo dev.

Pytania mile widziane.
```

### r/oszczedzanie

Title:
```
Porównywarka cen w 7 sklepach + skanowanie paragonów (darmowe, bez logowania)
```

Body — short and direct:
```
Robię to solo, jest darmowe, nie wymaga konta. Wpisujesz zakupy, dostajesz
porównanie cen w 7 sklepach z gazetek + społecznościowe ceny z paragonów.

taniejkupuj.pl

Chętnie posłucham co dodać. Najbardziej zależy mi na info które
produkty u Was są najgorzej rozpoznawane.
```

---

## 3. Facebook groups

**Rule of thumb:** ALWAYS read the group rules first. Most "oszczędzanie"
and "lista zakupów" groups allow soft promo if you contribute genuine value.

**DO NOT:**
- Post identical text in 5 groups in one hour (FB flags as spam)
- Use shortened URLs (bit.ly etc. — looks scammy in groups)
- Tag random people

**DO:**
- Wait at least 3 days between posts in the same group
- Reply to a few other people's posts in the group first
- Pin a comment with the URL if pasting in body looks promo

### Template — "I built this, looking for feedback"

```
Cześć grupo! 👋

Robię na boku darmową porównywarkę cen w 7 sklepach (Biedronka, Lidl,
Kaufland, Aldi, Netto, Auchan, Carrefour). Bez logowania, bez reklam.

Co ważne — można też zeskanować paragon i AI doda prawdziwe ceny z półki.
Dzięki temu Lidl i Biedronka też zaczynają działać (bo same blokują
scraping).

Adres w komentarzu, żeby moderator nie myślał że spam 🙏

Najbardziej zależy mi na realnym feedbacku — co działa, co nie działa,
których produktów brakuje. Z góry dzięki!
```

W komentarzu:
```
👉 taniejkupuj.pl

Jeszcze raz: darmowe, bez konta, bez aplikacji do instalowania.
Można dodać do ekranu głównego telefonu jak normalną apkę.
```

### Polish FB groups to try (search and request to join)

- Oszczędne gospodarowanie
- Tanie zakupy — gdzie kupuję
- Mama oszczędza — lista zakupów
- Krezus — oszczędzanie i finanse
- Biedronka — oferty i promocje (UWAGA: większość zabrania reklamy
  zewnętrznych stron — sprawdź regulamin)
- Lidl Polska — oferty
- Oszczędzaj z nami
- Lista zakupów — co u Was

---

## 4. Twitter / X

Niska aktywność polskiej "oszczędzanie" niche ale jeśli masz konto:

```
Zrobiłem porównywarkę cen w 7 polskich sklepach 🛒

• Wpisujesz zakupy → porównanie cen w Biedronce, Lidlu, Kauflandzie,
  Aldi, Netto, Auchanie i Carrefourze
• Skanujesz paragon → AI czyta i pomaga innym
• Bez logowania, bez reklam

taniejkupuj.pl

Solo project, każdy feedback złoty 🙏
```

---

## 5. ProductHunt — jeśli masz angielską wersję

Skip na razie. PH wymaga wersji angielskiej i polski projekt
prawdopodobnie nie zdobędzie tam trakcji.

---

## Kolejność wrzucania (tactical playbook)

### Dzień 1 (poniedziałek 09:00)
1. Wykop mikroblog — 5 minut
2. r/programowanie post — 10 minut
3. Spędź 30 min odpisując na komentarze pod oba posty

### Dzień 2 (wtorek)
1. r/oszczedzanie post
2. 2-3 polskie FB grupy "oszczędzanie"

### Dzień 3 (środa wieczór 20:00)
1. Wykop Znalezisko jeśli mikroblog dobrze poszedł
2. r/Polska post

### Dzień 4-7
- Sprawdzaj /admin/events codziennie
- Zobacz skąd faktycznie idzie ruch
- Powiel kanał który zadziałał, odpuść który nie

---

## Co śledzić w /admin/events

Po każdym poście sprawdź:
- **Top referrers** — który kanał daje ruch
- **Funnel** — czy ludzie z tego źródła faktycznie używają, czy klikają i wychodzą
- **store_click rate** — % wizyt → klik w sklep (to twoja konwersja przyszłej kasy)

Jeśli z Wykopa przyszło 200 osób ale 3% kliknęło dalej — Wykop daje
niski-quality ruch. Jeśli z Reddita 50 osób i 40% kliknęło — Reddit
jest twoim kanałem. Inwestuj tam.
