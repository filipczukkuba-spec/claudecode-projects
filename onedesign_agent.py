import sys
import os
import json
import time
from datetime import datetime, timedelta
from anthropic import Anthropic

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

client = Anthropic()

TODAY = datetime.now().strftime("%Y-%m-%d")
START_DATE = (datetime.now() + timedelta(days=(7 - datetime.now().weekday()))).strftime("%Y-%m-%d")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
STRATEGY_DIR = os.path.join(os.path.dirname(__file__), "strategies")
DATA_FILE = os.path.join(DATA_DIR, f"{TODAY}_collection.json")
STRATEGY_FILE = os.path.join(STRATEGY_DIR, f"{TODAY}_strategia.md")


# ═══════════════════════════════════════════════════════════════
# PHASE 1 — DATA COLLECTION (zero API calls)
# ═══════════════════════════════════════════════════════════════

SEARCH_QUERIES = [
    "interior design trends 2026 luxury residential warm minimalism Japandi",
    "Warsaw Poland real estate renovation market 2025 2026 high income families",
    "Instagram Reels strategy interior design luxury account growth 2026",
]

def web_search(query, max_results=6):
    if DDGS is None:
        print(f"  [!] DDGS not installed — skipping: {query}", flush=True)
        return []
    try:
        time.sleep(1.5)
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        for r in results:
            if "body" in r and len(r["body"]) > 350:
                r["body"] = r["body"][:350] + "..."
        return results
    except Exception as e:
        print(f"  [!] Search error: {e}", flush=True)
        return []


def build_persona(archetype, age_range, family, property_type, budget, trigger):
    drivers = {
        "mloda_ambitna_para": {
            "primary_driver": "Status i aspiracja — dom ma odzwierciedlać ich sukces zawodowy",
            "fear": "Błędy kosztujące czas i pieniądze przy pierwszym dużym remoncie",
            "instagram_behavior": "Scrollują wieczorami, zapisują posty do albumów, porównują style",
            "content_they_dm": "Konkretne ceny i harmonogramy, realistyczne 'przed i po'",
            "objections": ["Czy projektant zrozumie nasz gust?", "Ile to naprawdę kosztuje?", "Jak długo potrwa?"],
        },
        "ugruntowana_rodzina": {
            "primary_driver": "Dziedzictwo i komfort — dom ma służyć całej rodzinie przez dekady",
            "fear": "Remont zakłóci codzienne życie dzieci i rodziny",
            "instagram_behavior": "Aktywni rano, szukają funkcjonalności, nie tylko estetyki",
            "content_they_dm": "Rozwiązania dla rodzin z dziećmi, materiały odporne na zniszczenia",
            "objections": ["Jak żyć podczas remontu?", "Kto koordynuje wykonawców?", "Czy jest bezpieczne dla dzieci?"],
        },
        "premium_upgrade": {
            "primary_driver": "Jakość życia — po latach ciężkiej pracy zasługują na przestrzeń marzeń",
            "fear": "Skończą z czymś modnym dziś, ale bezosobowym za 5 lat",
            "instagram_behavior": "Oglądają dłuższe treści, śledzą konta z wyraźnym POV",
            "content_they_dm": "Filozofia designu, proces twórczy, efekty 'wow' po zakończeniu",
            "objections": ["Czy projektant ma wyraźną wizję?", "Referencje od klientów?", "Jak dbają o szczegóły?"],
        },
    }
    d = drivers.get(archetype, drivers["ugruntowana_rodzina"])
    return {
        "archetype": archetype,
        "age_range": age_range,
        "family": family,
        "property": property_type,
        "budget_pln": budget,
        "renovation_trigger": trigger,
        "psychology": d,
        "decision_timeline": "3-6 miesięcy od pierwszego kontaktu do umowy",
        "how_they_find_designer": "Instagram, rekomendacje znajomych, Google 'projektant wnętrz Warszawa'",
    }


def build_strategy_scaffold():
    return {
        "content_pillars": [
            {"name": "Transformacja", "description": "Projekty przed/po z wyjaśnieniem DLACZEGO tak zdecydowano", "posts_per_week": 2, "formats": ["Reel", "Karuzela"]},
            {"name": "Edukacja Klienta", "description": "Odpowiedzi na pytania klientów, obalanie mitów, transparentność kosztów", "posts_per_week": 2, "formats": ["Karuzela", "Reel Q&A"]},
            {"name": "Kulisy", "description": "Proces roboczy, wizyty na budowie, wybór materiałów — autentyczność", "posts_per_week": 1, "formats": ["Stories", "Reel"]},
        ],
        "posting_cadence": {
            "Poniedzialek": "Reel — start tygodnia / transformacja",
            "Sroda": "Karuzela — edukacja / trendy",
            "Piatek": "Reel lub Karuzela — projekt / CTA",
            "Sobota": "Reel krótki — inspiracja, szeroki zasięg",
            "Stories": "Codziennie — backstage, ankiety, Q&A",
        },
        "hashtag_tiers": {
            "niszowe_5_15k": ["#projektwnetrz", "#wnetrzawarszawa", "#projektowaniewnetrz", "#architekturawnetrz"],
            "srednie_50_500k": ["#wnetrza", "#interiordesignpoland", "#dommarzeń", "#wystrójwnetrz"],
            "szerokie_1m": ["#interior", "#homedecor", "#interiordesign"],
            "brandowane": ["#onedesignpl"],
            "zasada": "3-5 hashtagów: 2 niszowe + 1 średnie + 1 brandowany",
        },
        "content_ratio": "40% edukacja / 40% autentyczność / 20% sprzedaż",
        "key_messages": [
            "Projektujemy domy, w których chce się żyć — nie galerie",
            "Jeden punkt kontaktu, zero chaosu koordynacyjnego",
            "Dobry projekt to oszczędność — błędy kosztują 2x więcej",
        ],
        "seasonal_hooks_q2": {
            "maj": "Wiosenna metamorfoza — sezon startów remontowych",
            "czerwiec": "Dom gotowy na lato — tarasy, przestrzenie indoor-outdoor",
        },
    }


def build_calendar_scaffold(start_date_str, weeks=4, posts_per_week=4):
    start = datetime.strptime(start_date_str, "%Y-%m-%d")
    week_themes = [
        "Zanim zaczniesz remont — co musisz wiedzieć",
        "Metamorfoza — projekt od środka",
        "Dla kogo projektujemy — życie naszych klientów",
        "Trendy vs. Ponadczasowość — głos eksperta",
    ]
    format_rotation = [
        ("Poniedzialek", 0, "Reel"),
        ("Sroda", 2, "Karuzela"),
        ("Piatek", 4, "Reel"),
        ("Sobota", 5, "Reel krótki"),
    ]
    calendar = []
    for w in range(weeks):
        week_start = start + timedelta(weeks=w)
        posts = []
        for day_name, offset, fmt in format_rotation[:posts_per_week]:
            posts.append({
                "date": (week_start + timedelta(days=offset)).strftime("%Y-%m-%d"),
                "day": day_name,
                "format": fmt,
                "pillar": "?",
                "polish_hook": "?",
                "content": "?",
                "hashtag_tier": "2 niszowe + 1 średnie + 1 brandowany",
            })
        calendar.append({
            "week": w + 1,
            "theme": week_themes[w % len(week_themes)],
            "start": week_start.strftime("%Y-%m-%d"),
            "posts": posts,
        })
    return calendar


def phase1_collect():
    print("\n--- FAZA 1: Zbieranie danych (bez API) ---", flush=True)
    os.makedirs(DATA_DIR, exist_ok=True)

    print("Wyszukiwanie trendów...", flush=True)
    trends = []
    for i, query in enumerate(SEARCH_QUERIES, 1):
        print(f"  [{i}/{len(SEARCH_QUERIES)}] {query[:60]}...", flush=True)
        results = web_search(query)
        trends.append({"query": query, "results": results})

    print("Budowanie person klientów...", flush=True)
    personas = [
        build_persona("mloda_ambitna_para", "35-42", "małżeństwo, 1-2 dzieci w wieku 4-10 lat",
                      "dom 130-160m² w Wilanowie lub Ursynowie", "180 000-320 000 PLN",
                      "nowo zakupiona nieruchomość do generalnego remontu"),
        build_persona("ugruntowana_rodzina", "43-52", "małżeństwo, 2 dzieci w wieku 8-16 lat",
                      "mieszkanie 90-120m² w Mokotowie lub Żoliborzu", "120 000-220 000 PLN",
                      "mieszkanie za małe na rozrastającą się rodzinę lub chęć modernizacji"),
        build_persona("premium_upgrade", "48-57", "małżeństwo, dzieci już starsze lub wyprowadzone",
                      "nowe premium mieszkanie lub dom 150m²+ w dobrej lokalizacji", "250 000-500 000 PLN",
                      "przeprowadzka do wymarzonego miejsca lub nagroda po latach ciężkiej pracy"),
    ]

    print("Budowanie szkieletu strategii...", flush=True)
    strategy = build_strategy_scaffold()
    calendar = build_calendar_scaffold(START_DATE, weeks=4, posts_per_week=4)

    data = {
        "generated_at": TODAY,
        "calendar_start": START_DATE,
        "trends": trends,
        "personas": personas,
        "strategy_scaffold": strategy,
        "calendar_scaffold": calendar,
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✓ Dane zapisane: {DATA_FILE}", flush=True)
    return data


# ═══════════════════════════════════════════════════════════════
# PHASE 2 — GENERATION (exactly ONE API call)
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Jesteś ekspertem od marketingu w mediach społecznościowych dla polskiego rynku luksusowego projektowania wnętrz.

Pracujesz dla One Design (@onedesignpl) — warszawskiej pracowni projektowania wnętrz i wykończeń.

**Klient docelowy:** Pary 35-55 lat z dziećmi, właściciele nieruchomości 100m²+, budżety 120 000–500 000 PLN, Warszawa.

**Estetyka marki:** Ciepły luksus, orientacja na rodzinę, NIE zimny minimalizm. Wyraźny punkt widzenia.

**Zasady contentu:** Posty w 1. os. liczby mnogiej ("projektujemy", "pomagamy"). Hooki muszą być konkretne i chwytliwe, NIE ogólnikowe. Unikaj "Nowy projekt ✨" — pisz tak, żeby klient poczuł że post jest o nim."""


def phase2_generate(data):
    print("\n--- FAZA 2: Generowanie strategii (1 wywołanie API) ---", flush=True)
    os.makedirs(STRATEGY_DIR, exist_ok=True)

    # Build compact prompt from collected data
    trends_text = ""
    for t in data["trends"]:
        trends_text += f"\n**Zapytanie:** {t['query']}\n"
        for r in t["results"][:4]:
            trends_text += f"- {r.get('title','')}: {r.get('body','')}\n"

    personas_text = json.dumps(data["personas"], ensure_ascii=False, indent=1)
    strategy_text = json.dumps(data["strategy_scaffold"], ensure_ascii=False, indent=1)
    calendar_text = json.dumps(data["calendar_scaffold"], ensure_ascii=False, indent=1)

    user_message = f"""Na podstawie poniższych danych napisz kompletny raport strategii Instagram dla @onedesignpl.

## DANE TRENDÓW (z wyszukiwania)
{trends_text}

## PERSONY KLIENTÓW
{personas_text}

## SZKIELET STRATEGII
{strategy_text}

## SZKIELET KALENDARZA (do wypełnienia)
{calendar_text}

---

Napisz raport w dokładnie tym formacie Markdown:

# @onedesignpl — Strategia Instagram
**Wygenerowano:** {TODAY} | **Okres:** {START_DATE} — 4 tygodnie

---

## Część 1: Trendy (3-4 punkty z konkretnymi danymi ze źródeł powyżej)

## Część 2: Persony Klientów
### Persona 1: [imię] — [archetype]
[wszystkie pola z JSON + 2-3 zdania jak to wpływa na content]
### Persona 2: [imię] — [archetype]
### Persona 3: [imię] — [archetype]

## Część 3: Strategia Instagram
### Filary contentu
### Harmonogram publikacji
### Strategia hashtagów (tabela)
### Kluczowe przekazy

## Część 4: Kalendarz 4-tygodniowy

### Tydzień 1 — Temat: [temat ze szkieletu]
| Data | Dzień | Format | Filar | Hook (PL) | Opis treści | Hashtagi |
|------|-------|--------|-------|-----------|-------------|----------|
[wypełnij każdy post ze szkieletu — KONKRETNE polskie hooki, NIE ogólnikowe]

### Tydzień 2 — Temat: [temat]
[tabela]

### Tydzień 3 — Temat: [temat]
[tabela]

### Tydzień 4 — Temat: [temat]
[tabela]

## Część 5: Checkista 30 dni
[10-12 konkretnych działań do wykonania]

WAŻNE: Każdy hook w kalendarzu musi być po polsku, konkretny i chwytliwy. Żadnych ogólników."""

    print("Wywołanie API Claude...", flush=True)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}]
    )

    content = response.content[0].text
    tokens_in = response.usage.input_tokens
    tokens_out = response.usage.output_tokens
    print(f"✓ Odpowiedź: {tokens_in} tokenów wejść / {tokens_out} tokenów wyjść", flush=True)

    with open(STRATEGY_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✓ Strategia zapisana: {STRATEGY_FILE}", flush=True)
    return content


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print(f"\n{'='*60}", flush=True)
    print("  One Design — Agent Strategii Instagram", flush=True)
    print(f"  Data: {TODAY} | Start kalendarza: {START_DATE}", flush=True)
    print(f"{'='*60}", flush=True)

    try:
        data = phase1_collect()
        phase2_generate(data)
        print(f"\n{'='*60}", flush=True)
        print(f"  Gotowe! Plik: strategies/{TODAY}_strategia.md", flush=True)
        print(f"{'='*60}\n", flush=True)
    except Exception as e:
        import traceback
        print(f"\n[BŁĄD] {type(e).__name__}: {e}", flush=True)
        traceback.print_exc(file=sys.stdout)
        sys.stdout.flush()
        sys.exit(1)
