import sys
import os
import json
import time
from datetime import datetime, timedelta
from anthropic import Anthropic

sys.stdout.reconfigure(encoding="utf-8")

try:
    from duckduckgo_search import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

client = Anthropic()

TODAY = datetime.now().strftime("%Y-%m-%d")
START_DATE = (datetime.now() + timedelta(days=(7 - datetime.now().weekday()))).strftime("%Y-%m-%d")

SYSTEM_PROMPT = """Jesteś starszym strategiem marketingu cyfrowego i dyrektorem ds. treści, specjalizującym się w polskim rynku luksusowego projektowania wnętrz. Pracujesz wyłącznie dla One Design (@onedesignpl) — warszawskiej pracowni projektowania wnętrz i kompleksowych wykończeń.

## Kontekst marki

**Klient docelowy:** Pary w wieku 35-55 lat z dziećmi, właściciele lub osoby remontujące nieruchomości o powierzchni 100m²+, zamożne rodziny z Warszawy i okolic, budżety projektowe 150 000–500 000 PLN.

**Estetyka One Design:** Ciepły luksus, orientacja na rodzinę, NIE zimny minimalizm. Wnętrza, w których chce się żyć — nie tylko fotografować. Naturalne materiały, ciepłe kolory, funkcjonalność połączona z elegancją.

**Psychologia klienta:**
- Chcą eksperta, który zdejmie z nich ciężar decyzji — nie 40 opcji do wyboru
- Motywatory: dziedzictwo rodzinne, status społeczny, spokój ducha, ochrona inwestycji
- Decydują emocjonalnie, racjonalizują logicznie
- Zajęci, zmęczeni decyzjami, ufają autorytetom

**Rzeczywistość platformy:** Instagram = kanał aspiracyjnego odkrycia; ta grupa wiekowa jest też na Facebooku, ale Instagram jest głównym narzędziem poszukiwań inspiracji designerskich. Treści często udostępniane przez DM, nie publicznie — optymalizuj pod "wyślij znajomemu".

**Czym NIE jest One Design:** Kolejnym polskim kontem designerskim z postami "Nowy projekt ✨" bez żadnego POV ani wartości dla odbiorcy.

**Różnicowanie od konkurencji:** Wyraźny punkt widzenia, edukacja klienta, transparentność procesu, głos eksperta — nie tylko piękne zdjęcia.

## Mandat operacyjny

Kiedy tworzysz strategię, MUSISZ wykonać następującą sekwencję używając dostępnych narzędzi:

1. Wywołaj `web_search` co najmniej 5 razy z różnymi zapytaniami: trendy projektowania wnętrz, rynek nieruchomości Warszawa, trendy Instagram dla luksusowego designu, styl życia Polaków 35-55 z dziećmi, trendy Japandi/biophilic 2026
2. Wywołaj `generate_client_persona` 3 razy z różnymi danymi demograficznymi — 3 odrębne archetypy
3. Wywołaj `build_instagram_strategy` 1 raz z zebranymi danymi
4. Wywołaj `create_content_calendar` 1 raz
5. Wywołaj `save_strategy_report` 1 raz z pełnym raportem w Markdown

NIE pomijaj kroków. NIE pytaj użytkownika o dane wejściowe w trakcie procesu.

## Standardy jakości

Każdy post w kalendarzu MUSI zawierać:
- Format (Reel/Karuzela/Stories)
- Hook po polsku (pierwsze zdanie przyciągające uwagę)
- Opis treści (2-3 zdania)
- Filar contentu
- Optymalny dzień publikacji
- Poziom hashtagów (niszowy/środkowy/szeroki)

Podsumowania trendów MUSZĄ cytować źródła. Wszystkie texty hooków i contentu po POLSKU. Strategia powinna być natychmiast wykonalna — nie ogólnikowa."""

TOOLS = [
    {
        "name": "web_search",
        "description": "Przeszukaj internet przez DuckDuckGo w poszukiwaniu aktualnych informacji o trendach w projektowaniu wnętrz, rynku warszawskim, trendach Instagram i stylu życia grupy docelowej. Wywołuj wielokrotnie z różnymi zapytaniami.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Zapytanie wyszukiwania. Bądź konkretny. W miarę możliwości uwzględnij rok (2025 lub 2026) i kontekst geograficzny (Polska/Warszawa)."
                },
                "max_results": {
                    "type": "integer",
                    "description": "Liczba wyników. Domyślnie 8, max 12.",
                    "default": 8
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "generate_client_persona",
        "description": "Wygeneruj szczegółowy profil klienta docelowego One Design. Wywołaj 3 razy z różnymi danymi, aby stworzyć 3 archetypy.",
        "input_schema": {
            "type": "object",
            "properties": {
                "archetype_label": {"type": "string", "description": "Krótka etykieta, np. 'mloda_ambitna_para', 'ugruntowana_rodzina', 'premium_upgrade'"},
                "age_range": {"type": "string", "description": "Przedział wiekowy, np. '35-40'"},
                "family_situation": {"type": "string", "description": "Sytuacja rodzinna, np. 'małżeństwo, 2 dzieci w wieku 6 i 9 lat'"},
                "property_type": {"type": "string", "description": "Typ nieruchomości, np. 'dom 140m² w Wilanowie'"},
                "budget_range_pln": {"type": "string", "description": "Budżet w PLN, np. '200 000-350 000 PLN'"},
                "renovation_trigger": {"type": "string", "description": "Co wyzwoliło potrzebę remontu, np. 'nowo zakupiona nieruchomość', 'drugie dziecko w drodze'"}
            },
            "required": ["archetype_label", "age_range", "family_situation", "property_type", "budget_range_pln", "renovation_trigger"]
        }
    },
    {
        "name": "build_instagram_strategy",
        "description": "Zsyntezuj dane o trendach i persony klientów w kompletną strategię Instagram dla @onedesignpl.",
        "input_schema": {
            "type": "object",
            "properties": {
                "trend_summary": {"type": "string", "description": "Zebrany opis wszystkich trendów z wywołań web_search. Uwzględnij konkretne dane i źródła."},
                "persona_labels": {"type": "array", "items": {"type": "string"}, "description": "Lista etykiet archetype_label z wywołań generate_client_persona"},
                "weeks": {"type": "integer", "description": "Liczba tygodni strategii. Powinno być 4.", "default": 4},
                "focus_quarter": {"type": "string", "description": "Kwartał/sezon, np. 'Q2 2026 (maj-czerwiec)'"}
            },
            "required": ["trend_summary", "persona_labels", "weeks", "focus_quarter"]
        }
    },
    {
        "name": "create_content_calendar",
        "description": "Wygeneruj szczegółowy 4-tygodniowy kalendarz treści ze szkieletem dat i formatów.",
        "input_schema": {
            "type": "object",
            "properties": {
                "strategy_json": {"type": "string", "description": "Pełny JSON zwrócony przez build_instagram_strategy."},
                "start_date": {"type": "string", "description": "Data ISO pierwszego poniedziałku kalendarza, np. '2026-05-11'"},
                "weeks": {"type": "integer", "description": "Liczba tygodni. Powinno być 4.", "default": 4},
                "posts_per_week": {"type": "integer", "description": "Posty na tydzień. Min 3, cel 5.", "default": 5}
            },
            "required": ["strategy_json", "start_date"]
        }
    },
    {
        "name": "save_strategy_report",
        "description": "Zapisz ukończoną strategię jako plik Markdown do folderu strategies/. Utwórz folder jeśli nie istnieje. Zwraca pełną ścieżkę pliku.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Pełna treść Markdown raportu strategicznego. MUSI zawierać wszystkie 5 części: Trendy, Persony, Strategia, Kalendarz 4-tygodniowy, Checkista."
                },
                "filename": {
                    "type": "string",
                    "description": "Nazwa pliku bez rozszerzenia, np. '2026-05-07_strategia'. Narzędzie automatycznie doda .md"
                }
            },
            "required": ["content", "filename"]
        }
    }
]


# ── Tool implementations ──────────────────────────────────────────────────────

def tool_web_search(inputs):
    if not HAS_DDGS:
        return json.dumps({"error": "duckduckgo_search not installed. Run: pip install duckduckgo-search"})
    query = inputs["query"]
    max_results = inputs.get("max_results", 8)
    try:
        time.sleep(1.5)
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


def tool_generate_persona(inputs):
    archetype = inputs["archetype_label"]
    age_range = inputs["age_range"]
    family = inputs["family_situation"]
    property_type = inputs["property_type"]
    budget = inputs["budget_range_pln"]
    trigger = inputs["renovation_trigger"]

    psychological_drivers = {
        "mloda_ambitna_para": {
            "primary_driver": "Status i aspiracja — chcą domu, który odzwierciedla ich sukces zawodowy",
            "fear": "Że zrobią błędy kosztujące ich czas i pieniądze przy pierwszym dużym remoncie",
            "instagram_behavior": "Scrollują wieczorami po pracy, zapisują posty do albumów, porównują style",
            "content_they_dm": "Posty z konkretnymi cenami i harmonogramem projektu, realistyczne 'zanim i po'",
            "objections": ["Czy projektant zrozumie nasz gust?", "Ile to naprawdę kosztuje?", "Jak długo potrwa?"],
            "communication_style": "Bezpośredni, konkretny, z liczbami i harmonogramami"
        },
        "ugruntowana_rodzina": {
            "primary_driver": "Dziedzictwo i komfort — dom ma służyć całej rodzinie przez dekady",
            "fear": "Że prace remontowe zakłócą codzienne życie dzieci i rodziny",
            "instagram_behavior": "Aktywni rano przed pracą, szukają funkcjonalności a nie tylko estetyki",
            "content_they_dm": "Rozwiązania dla rodzin z dziećmi, przestrzenie wielofunkcyjne, materiały odporne na zniszczenia",
            "objections": ["Jak zorganizować życie podczas remontu?", "Czy jest bezpieczne dla dzieci?", "Kto koordynuje wykonawców?"],
            "communication_style": "Rzeczowy, zorientowany na proces i logistykę, ciepły"
        },
        "premium_upgrade": {
            "primary_driver": "Jakość życia — po latach ciężkiej pracy zasługują na przestrzeń marzeń",
            "fear": "Że skończą z czymś modnym dziś, ale bezosobowym za 5 lat",
            "instagram_behavior": "Oglądają dłuższe treści, śledzą twórców z wyraźnym POV, cenią autentyczność",
            "content_they_dm": "Opowieści o procesie twórczym, filozofia designu, efekty 'wow' po zakończeniu projektu",
            "objections": ["Czy projektant ma wyraźną wizję?", "Jak zadbają o szczegóły?", "Referencje od klientów?"],
            "communication_style": "Narracyjny, inspiracyjny, skupiony na wizji i rzemieśle"
        }
    }

    matched = psychological_drivers.get(archetype, psychological_drivers["ugruntowana_rodzina"])

    persona = {
        "archetype_label": archetype,
        "demographics": {
            "age_range": age_range,
            "family_situation": family,
            "property_type": property_type,
            "budget_range_pln": budget,
            "renovation_trigger": trigger,
            "location": "Warszawa i okolice (Wilanów, Mokotów, Żoliborz, Ursynów)"
        },
        "psychology": {
            "primary_driver": matched["primary_driver"],
            "fear": matched["fear"],
            "objections": matched["objections"],
            "communication_style": matched["communication_style"]
        },
        "instagram_behavior": {
            "usage_pattern": matched["instagram_behavior"],
            "content_they_dm": matched["content_they_dm"],
            "content_they_save": "Inspiracje do albumów, konkretne rozwiązania problemów",
            "content_they_share_to_stories": "Rzadko — raczej DM do partnera lub znajomego"
        },
        "decision_journey": {
            "awareness": "Instagram, rekomendacje znajomych, Google 'projektant wnętrz Warszawa'",
            "consideration": "Oglądają portfolio, sprawdzają opinie, porównują 3-5 pracowni",
            "decision_trigger": "Jeden post lub rozmowa, która buduje zaufanie i rozwiewa ich główny lęk",
            "timeline": "3-6 miesięcy od pierwszego kontaktu do podpisania umowy"
        }
    }

    return json.dumps(persona, ensure_ascii=False, indent=2)


def tool_build_strategy(inputs):
    trend_summary = inputs["trend_summary"]
    persona_labels = inputs["persona_labels"]
    weeks = inputs.get("weeks", 4)
    focus_quarter = inputs.get("focus_quarter", "Q2 2026")

    strategy = {
        "meta": {
            "account": "@onedesignpl",
            "generated_for": focus_quarter,
            "weeks": weeks,
            "persona_labels": persona_labels
        },
        "brand_positioning": "One Design — projektujemy domy, w których chce się żyć. Nie galerie, nie showroomy. Przestrzenie dla rodzin z historią.",
        "content_pillars": [
            {
                "name": "Transformacja",
                "description": "Projekty przed/po z wyjaśnieniem decyzji projektowych. NIE tylko efekt końcowy — pokazuj DLACZEGO.",
                "weekly_posts": 2,
                "formats": ["Reel (time-lapse z narracją)", "Karuzela (etapy projektu)"],
                "kpi": "Zasięg, wyświetlenia Reels"
            },
            {
                "name": "Edukacja Klienta",
                "description": "Odpowiedzi na pytania klientów, obalanie mitów, transparentność kosztów i procesu. Buduje zaufanie i pozycjonuje jako eksperta.",
                "weekly_posts": 2,
                "formats": ["Karuzela (lista porad)", "Reel (krótkie Q&A)"],
                "kpi": "Zapisania, udostępnienia przez DM"
            },
            {
                "name": "Życie za Kulisami",
                "description": "Proces roboczy, wizyty na budowie, wybór materiałów, spotkania z klientami (za zgodą). Buduje autentyczność.",
                "weekly_posts": 1,
                "formats": ["Stories (codziennie)", "Reel (weekly highlight)"],
                "kpi": "Zaangażowanie w Stories, odpowiedzi na Stories"
            },
            {
                "name": "Głos Eksperta",
                "description": "Opinie o trendach, rekomendacje materiałów, komentarz do aktualnych trendów designerskich. Wyraźny POV.",
                "weekly_posts": 1,
                "formats": ["Karuzela (trend report)", "Reel (opinia eksperta)"],
                "kpi": "Komentarze, udostępnienia do Stories"
            }
        ],
        "posting_cadence": {
            "minimum_per_week": 3,
            "target_per_week": 5,
            "format_rotation": {
                "Poniedzialek": "Reel (motywacyjny start tygodnia / transformacja)",
                "Sroda": "Karuzela (edukacja / trendy)",
                "Piatek": "Reel lub Karuzela (projekt / CTA na weekend)",
                "Sobota": "Reel (krótki, inspiracyjny, szeroki zasięg)",
                "Stories": "Codziennie — backstage, ankiety, Q&A"
            },
            "optimal_times": {
                "weekdays": "07:00-09:00 lub 19:00-21:00",
                "weekend": "09:00-11:00"
            }
        },
        "hashtag_strategy": {
            "niche_5_15k": ["#projektwnetrz", "#wnetrzawarszawa", "#projektowaniewnetrz", "#architekturawnetrz", "#wykonczeniewnetrz"],
            "mid_50_500k": ["#wnetrza", "#interiordesignpoland", "#projektant", "#dommarzeń", "#wystrójwnetrz"],
            "broad_1m_plus": ["#interior", "#homedecor", "#interiordesign", "#homedesign", "#livingroom"],
            "branded": ["#onedesignpl", "#onedesign"],
            "usage_rule": "3-5 hashtagów na post: 2 niszowe + 1-2 środkowe + 1 brandowany"
        },
        "content_ratio": {
            "educational_value": "40%",
            "audience_connection_authenticity": "40%",
            "sales_cta": "20%"
        },
        "key_messages": [
            "Projektujemy domy, nie showroomy — przestrzenie dla prawdziwych rodzin",
            "Bierzemy odpowiedzialność za cały projekt — jeden punkt kontaktu, zero chaosu",
            "Inwestycja w dobry projekt to oszczędność na błędach kosztujących 2x więcej"
        ],
        "seasonal_hooks": {
            "maj": "Wiosenna metamorfoza — sezon startów remontowych, motyw odnowy i świeżego startu",
            "czerwiec": "Dom gotowy na lato — tarasy, ogrody, przestrzenie łączące wnętrze z zewnętrzem",
            "back_to_school": "Przestrzenie do nauki dla dzieci — biurka, kąciki, organizacja"
        },
        "trend_context": trend_summary[:500]
    }

    return json.dumps(strategy, ensure_ascii=False, indent=2)


def tool_create_calendar(inputs):
    strategy_json = inputs["strategy_json"]
    start_date_str = inputs.get("start_date", START_DATE)
    weeks = inputs.get("weeks", 4)
    posts_per_week = inputs.get("posts_per_week", 5)

    try:
        strategy = json.loads(strategy_json)
    except Exception:
        strategy = {}

    start = datetime.strptime(start_date_str, "%Y-%m-%d")

    format_rotation = [
        ("Poniedzialek", "Reel"),
        ("Sroda", "Karuzela"),
        ("Piatek", "Reel"),
        ("Sobota", "Reel (krótki)"),
        ("Wtorek", "Karuzela"),
    ]

    week_themes = [
        "Zanim zaczniesz remont — co musisz wiedzieć",
        "Metamorfoza — projekt od środka",
        "Dla kogo projektujemy — życie naszych klientów",
        "Trendy vs. Ponadczasowość — głos eksperta"
    ]

    calendar = {"weeks": [], "meta": {"start_date": start_date_str, "posts_per_week": posts_per_week}}

    day_offsets = {"Poniedzialek": 0, "Wtorek": 1, "Sroda": 2, "Piatek": 4, "Sobota": 5}

    for week_num in range(1, weeks + 1):
        week_start = start + timedelta(weeks=week_num - 1)
        week_end = week_start + timedelta(days=6)
        theme = week_themes[(week_num - 1) % len(week_themes)]
        posts = []

        for day_name, fmt in format_rotation[:posts_per_week]:
            offset = day_offsets.get(day_name, 0)
            post_date = week_start + timedelta(days=offset)
            posts.append({
                "date": post_date.strftime("%Y-%m-%d"),
                "day": day_name,
                "format": fmt,
                "pillar": "[do wypełnienia przez agenta]",
                "polish_hook": "[hook po polsku — do wypełnienia przez agenta]",
                "content_description": "[opis treści — do wypełnienia przez agenta]",
                "caption_opener": "[pierwsze zdanie opisu — do wypełnienia przez agenta]",
                "hashtag_tier": "2 niszowe + 1 środkowy + 1 brandowany",
                "stories_pairing": "[powiązane Stories tego dnia]"
            })

        calendar["weeks"].append({
            "week_number": week_num,
            "theme": theme,
            "dates": {
                "start": week_start.strftime("%Y-%m-%d"),
                "end": week_end.strftime("%Y-%m-%d")
            },
            "posts": posts
        })

    return json.dumps(calendar, ensure_ascii=False, indent=2)


def tool_save_report(inputs):
    content = inputs["content"]
    filename = inputs["filename"]
    if not filename.endswith(".md"):
        filename += ".md"

    output_dir = os.path.join(os.path.dirname(__file__), "strategies")
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"\n✓ Raport zapisany: {filepath}\n")
    return f"Zapisano do: {filepath}"


# ── Tool dispatcher ───────────────────────────────────────────────────────────

_step = 0
_step_labels = {
    "web_search": "Wyszukiwanie trendów",
    "generate_client_persona": "Generowanie persony klienta",
    "build_instagram_strategy": "Budowanie strategii",
    "create_content_calendar": "Tworzenie kalendarza",
    "save_strategy_report": "Zapisywanie raportu"
}

def run_tool(name, inputs):
    global _step
    _step += 1
    label = _step_labels.get(name, name)
    print(f"[Krok {_step}: {label} — {name}({list(inputs.keys())})]")

    if name == "web_search":
        return tool_web_search(inputs)
    if name == "generate_client_persona":
        return tool_generate_persona(inputs)
    if name == "build_instagram_strategy":
        return tool_build_strategy(inputs)
    if name == "create_content_calendar":
        return tool_create_calendar(inputs)
    if name == "save_strategy_report":
        return tool_save_report(inputs)
    return f"Błąd: nieznane narzędzie '{name}'"


# ── Agent loop ────────────────────────────────────────────────────────────────

TRIGGER = (
    f"Stwórz kompletną strategię Instagram dla @onedesignpl na kolejne 4 tygodnie "
    f"zaczynając od {START_DATE} (dziś jest {TODAY}, kwartał Q2 2026). "
    f"Najpierw wyszukaj aktualne trendy (co najmniej 5 wyszukiwań), wygeneruj 3 persony klientów, "
    f"zbuduj strategię, stwórz kalendarz treści i zapisz raport. "
    f"Pracuj autonomicznie przez wszystkie kroki bez pytania o dane wejściowe. "
    f"Nazwa pliku: '{TODAY}_strategia'. "
    f"WAŻNE: W save_strategy_report przekaż PEŁNY raport Markdown ze wszystkimi 5 częściami, "
    f"w tym konkretne polskie hooki dla każdego posta w kalendarzu."
)

def run_agent():
    print(f"\n{'='*60}")
    print("  One Design — Agent Strategii Instagram")
    print(f"  Data: {TODAY} | Start kalendarza: {START_DATE}")
    print(f"{'='*60}\n")

    messages = [{"role": "user", "content": TRIGGER}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8192,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    print(f"\nAgent: {block.text}")
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    run_agent()
