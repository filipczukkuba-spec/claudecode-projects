-- Fill all products still missing prices (all-dash rows in admin panel)
-- Prices from Polish grocery market knowledge (~2025): Biedronka baseline,
-- each store set individually based on typical chain positioning.
-- Uses DO UPDATE to overwrite existing ratio-calculated values too.
-- Order per row: Biedronka, Lidl, Kaufland, Aldi, Netto, Auchan, Carrefour

DO $$
DECLARE
  bid INT; lid INT; kauf INT; aldi_id INT; netto INT; auch INT; carr INT;
  pid INT;
  rec JSON;
  items JSON := '[
    ["Actimel",               2.99, 2.89, 3.29, 2.79, 3.09, 3.49, 3.69],
    ["Activia jogurt",        2.99, 2.89, 3.29, 2.79, 3.09, 3.49, 3.69],
    ["Alpro sojowe",          7.49, 6.99, 8.49, 6.99, 7.79, 8.49, 8.99],
    ["Awokado",               2.99, 2.79, 3.49, 2.69, 3.19, 3.49, 3.79],
    ["Bagietka",              2.99, 2.49, 3.29, 2.49, 2.99, 3.49, 3.69],
    ["Bakłażan",              3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Batat",                 4.99, 4.79, 5.49, 4.69, 5.19, 5.79, 5.99],
    ["Baton czekoladowy",     2.99, 2.79, 3.29, 2.69, 2.99, 3.39, 3.49],
    ["Bazylia",               3.49, 3.29, 3.99, 3.19, 3.69, 3.99, 4.19],
    ["BelVita",               6.99, 6.49, 7.99, 6.49, 7.29, 7.99, 8.49],
    ["Białka jajek",          8.99, 8.49, 9.99, 8.49, 9.49, 10.49, 10.99],
    ["Biltong",              12.99,12.49,13.99,11.99,13.49, 14.99, 15.49],
    ["Boczek",               12.99,11.99,13.99,11.49,13.29, 14.99, 15.49],
    ["Borówki",               9.99, 9.49,11.49, 9.49,10.49, 11.99, 12.49],
    ["Brownie",               2.99, 2.79, 3.29, 2.79, 3.09, 3.49, 3.69],
    ["Brzoskwinie",           5.99, 5.49, 6.79, 5.49, 6.29, 6.99, 7.29],
    ["Bułka tarta",           3.49, 3.29, 3.99, 3.19, 3.69, 3.99, 4.29],
    ["Bułki",                 3.99, 3.49, 4.49, 3.49, 3.99, 4.49, 4.79],
    ["Burak",                 2.49, 2.29, 2.79, 2.19, 2.59, 2.99, 3.09],
    ["Cebula",                2.99, 2.79, 3.29, 2.69, 3.09, 3.49, 3.69],
    ["Chałwa",                5.49, 5.29, 6.29, 5.19, 5.79, 6.49, 6.79],
    ["Chleb razowy",          5.99, 5.49, 6.49, 5.49, 6.19, 6.79, 6.99],
    ["Chleb tostowy",         5.49, 4.99, 5.99, 4.99, 5.69, 6.29, 6.49],
    ["Chrupki ryżowe",        3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Chrupki zbożowe",       3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Ciastka",               5.49, 4.99, 5.99, 4.99, 5.69, 6.29, 6.49],
    ["Ciastka kakaowe",       4.99, 4.69, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Ciastka kokosowe",      4.99, 4.69, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Ciastka maślane",       4.99, 4.69, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Ciastka owsiane",       4.99, 4.69, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Ciastka z dżemem",      4.99, 4.69, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Ciastka z kremem",      4.99, 4.69, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Ciastka z owocami",     4.99, 4.69, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Ciastka zbożowe",       4.99, 4.69, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Ciecierzyca",           4.49, 4.19, 4.99, 3.99, 4.69, 5.19, 5.49],
    ["Cola",                  4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Cornetto",              4.49, 4.29, 4.99, 4.19, 4.69, 5.19, 5.49],
    ["Cukier puder",          3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Cukier waniliowy",      1.99, 1.89, 2.29, 1.79, 2.09, 2.29, 2.49],
    ["Cukierki krówki",       3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Cukinia",               3.49, 3.29, 3.99, 3.19, 3.69, 3.99, 4.29],
    ["Cytryny",               4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Czosnek",               2.49, 2.29, 2.79, 2.19, 2.59, 2.99, 3.09],
    ["Danio serek",           2.99, 2.79, 3.29, 2.69, 3.09, 3.49, 3.69],
    ["Digestive McVitie''s",  7.99, 7.49, 8.99, 7.49, 8.29, 9.29, 9.49],
    ["Dropsy miętowe",        2.99, 2.79, 3.29, 2.69, 3.09, 3.49, 3.69],
    ["Drożdże",               1.99, 1.89, 2.19, 1.79, 2.09, 2.29, 2.49],
    ["Dynia prażona",         4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Fasola sucha",          4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Filet z dorsza",       24.99,23.99,27.99,23.99,25.99,28.99,29.99],
    ["Filet z indyka",       19.99,18.99,21.99,18.49,20.99,22.99,23.99],
    ["Granola",               6.99, 6.49, 7.99, 6.49, 7.29, 7.99, 8.49],
    ["Grejpfrut",             4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Grissini",              3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Gruszki",               4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Guma do żucia",         2.49, 2.29, 2.79, 2.19, 2.59, 2.99, 3.09],
    ["Herbata zielona",       6.99, 6.49, 7.99, 6.49, 7.29, 7.99, 8.49],
    ["Herbatniki",            4.49, 4.19, 4.99, 3.99, 4.69, 5.19, 5.49],
    ["Hortex sok",            4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Hummus",                8.99, 8.49, 9.99, 8.49, 9.49,10.49,10.99],
    ["Imbir",                 4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Jogurt grecki",         5.99, 5.49, 6.79, 5.49, 6.29, 6.99, 7.29],
    ["Kabanosy",              7.99, 7.49, 8.99, 7.49, 8.29, 9.29, 9.49],
    ["Kapusta biała",         2.99, 2.79, 3.29, 2.69, 3.09, 3.49, 3.69],
    ["Karmelki krówkowe",     3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Kasza bulgur",          4.49, 4.29, 4.99, 4.19, 4.69, 5.19, 5.49],
    ["Kawa instant",         12.99,11.99,14.99,11.99,13.49,14.99,15.99],
    ["Kawa ziarnista",       24.99,23.99,27.99,22.99,25.99,28.99,29.99],
    ["Kefir",                 3.49, 3.29, 3.99, 3.19, 3.69, 3.99, 4.29],
    ["Kiełbasa",             14.99,13.99,16.99,13.49,15.49,16.99,17.99],
    ["Kiwi",                  5.99, 5.79, 6.79, 5.49, 6.29, 6.99, 7.29],
    ["Knorr zupa",            2.49, 2.29, 2.79, 2.19, 2.59, 2.99, 3.09],
    ["Kokos wiórki",          4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Komosa ryżowa",         8.99, 8.49, 9.99, 8.49, 9.49,10.49,10.99],
    ["Krakersy ryżowe",       3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Krakersy z ziarnami",   4.49, 4.29, 4.99, 4.19, 4.69, 5.19, 5.49],
    ["Krewetki",             19.99,18.99,21.99,18.49,20.99,22.99,23.99],
    ["Kurkuma",               3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Landrynki",             2.99, 2.79, 3.29, 2.69, 3.09, 3.49, 3.69],
    ["Leibniz",               7.49, 6.99, 8.49, 6.99, 7.79, 8.49, 8.99],
    ["Lion",                  2.49, 2.29, 2.79, 2.19, 2.59, 2.99, 3.09],
    ["Lizaki",                2.99, 2.79, 3.29, 2.69, 3.09, 3.49, 3.69],
    ["Lody",                  6.99, 6.49, 7.99, 6.49, 7.29, 7.99, 8.49],
    ["Lody czekoladowe",      6.99, 6.49, 7.99, 6.49, 7.29, 7.99, 8.49],
    ["Lody rożek",            3.49, 3.29, 3.99, 3.19, 3.69, 3.99, 4.29],
    ["Lody truskawkowe",      6.99, 6.49, 7.99, 6.49, 7.29, 7.99, 8.49],
    ["Lody waniliowe",        6.99, 6.49, 7.99, 6.49, 7.29, 7.99, 8.49],
    ["Łosoś świeży",         39.99,37.99,44.99,37.99,41.99,46.99,48.99],
    ["Lotus Biscoff",         9.99, 9.49,11.49, 9.49,10.49,11.99,12.49],
    ["Maggi zupa",            2.49, 2.29, 2.79, 2.19, 2.59, 2.99, 3.09],
    ["Magnum Almond",         5.49, 5.29, 5.99, 5.19, 5.69, 6.29, 6.49],
    ["Magnum Classic",        5.49, 5.29, 5.99, 5.19, 5.69, 6.29, 6.49],
    ["Majonez light",         5.99, 5.49, 6.79, 5.49, 6.29, 6.99, 7.29],
    ["Mąka",                  3.49, 3.29, 3.99, 3.19, 3.69, 3.99, 4.29],
    ["Makaron lasagne",       3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Makaron penne",         2.99, 2.79, 3.29, 2.69, 3.09, 3.49, 3.69],
    ["Makaron spaghetti",     2.99, 2.79, 3.29, 2.69, 3.09, 3.49, 3.69],
    ["Makrela wędzona",       8.99, 8.49, 9.99, 8.49, 9.49,10.49,10.99],
    ["Maliny",                9.99, 9.49,11.49, 9.49,10.49,11.99,12.49],
    ["Mango",                 4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Maślanka",              2.99, 2.79, 3.29, 2.69, 3.09, 3.49, 3.69],
    ["Mielone wołowe",       19.99,18.99,21.99,18.49,20.99,22.99,23.99],
    ["Migdały",              12.99,11.99,14.99,11.99,13.49,14.99,15.99],
    ["Milka Karmel",           4.29, 4.09, 4.79, 4.09, 4.49, 4.99, 5.19],
    ["Milky Way",              2.49, 2.29, 2.79, 2.19, 2.59, 2.99, 3.09],
    ["Mix bakaliów",           7.99, 7.49, 8.99, 7.49, 8.29, 9.29, 9.49],
    ["Mleko kokosowe",         4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Mleko migdałowe",        7.49, 6.99, 8.49, 6.99, 7.79, 8.49, 8.99],
    ["Mleko owsiane",          7.49, 6.99, 8.49, 6.99, 7.79, 8.49, 8.99],
    ["Mleko sojowe",           5.99, 5.49, 6.79, 5.49, 6.29, 6.99, 7.29],
    ["Mozzarella",             4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Mrożona pizza",          9.99, 9.49,10.99, 9.49,10.49,11.99,12.49],
    ["Mrożone frytki",         7.99, 7.49, 8.99, 7.49, 8.29, 9.29, 9.49],
    ["Mrożone truskawki",      9.99, 9.49,10.99, 9.49,10.49,11.99,12.49],
    ["Mrożone warzywa mix",    6.99, 6.49, 7.99, 6.49, 7.29, 7.99, 8.49],
    ["Muffin czekoladowy",     2.99, 2.79, 3.29, 2.79, 3.09, 3.49, 3.69],
    ["Musli",                  6.49, 6.29, 6.99, 5.99, 6.79, 7.29, 7.49],
    ["Mydło w kostce",         3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Nasiona chia",           8.99, 8.49, 9.99, 8.49, 9.49,10.49,10.99],
    ["Nektarynki",             5.99, 5.49, 6.79, 5.49, 6.29, 6.99, 7.29],
    ["Nugat",                  4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Oatly owsiane",          7.49, 6.99, 8.49, 6.99, 7.79, 8.49, 8.99],
    ["Ocet jabłkowy",          4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Ogórki",                 3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Olej kokosowy",         12.99,11.99,14.99,11.99,13.49,14.99,15.99],
    ["Olej rzepakowy",         5.99, 5.79, 6.79, 5.49, 6.29, 6.99, 7.29],
    ["Oregano",                2.99, 2.79, 3.29, 2.69, 3.09, 3.49, 3.69],
    ["Orzechy laskowe",        9.99, 9.49,11.49, 9.49,10.49,11.99,12.49],
    ["Orzechy nerkowca",      14.99,13.99,16.99,13.49,15.49,16.99,17.99],
    ["Orzechy włoskie",       12.99,11.99,14.99,11.99,13.49,14.99,15.99],
    ["Orzeszki ziemne",        4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Otręby pszenne",         3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Paluszki mięsne",        6.99, 6.49, 7.99, 6.49, 7.29, 7.99, 8.49],
    ["Paluszki rybne",         9.99, 9.49,10.99, 9.49,10.49,11.99,12.49],
    ["Papryka",                5.99, 5.49, 6.79, 5.49, 6.29, 6.99, 7.29],
    ["Parmezan",               8.99, 8.49, 9.99, 8.49, 9.49,10.49,10.99],
    ["Parówki",                7.99, 7.49, 8.99, 7.49, 8.29, 9.29, 9.49],
    ["Pasta pomidorowa",       3.49, 3.29, 3.99, 3.19, 3.69, 3.99, 4.29],
    ["Pepsi Max",              3.29, 3.09, 3.69, 3.09, 3.49, 3.79, 3.99],
    ["Pesto",                  8.99, 8.49, 9.99, 8.49, 9.49,10.49,10.99],
    ["Pianka cukrowa",         2.99, 2.79, 3.29, 2.69, 3.09, 3.49, 3.69],
    ["Pieczarki",              4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Pierogi mrożone",        9.99, 9.49,10.99, 9.49,10.49,11.99,12.49],
    ["Pietruszka",             2.49, 2.29, 2.79, 2.19, 2.59, 2.99, 3.09],
    ["Płatki kukurydziane",    4.49, 4.29, 4.99, 4.19, 4.69, 5.19, 5.49],
    ["Płyn do podłóg",         5.99, 5.79, 6.79, 5.49, 6.29, 6.99, 7.29],
    ["Pomarańcze",             4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Popcorn",                3.49, 3.29, 3.99, 3.19, 3.69, 3.99, 4.29],
    ["Popcorn karmelowy",      3.49, 3.29, 3.99, 3.19, 3.69, 3.99, 4.29],
    ["Popcorn maślany",        3.49, 3.29, 3.99, 3.19, 3.69, 3.99, 4.29],
    ["Por",                    2.99, 2.79, 3.29, 2.69, 3.09, 3.49, 3.69],
    ["Porzeczki",              8.99, 8.49, 9.99, 8.49, 9.49,10.49,10.99],
    ["Precelki",               3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Precelki solone",        3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Proszek do pieczenia",   1.99, 1.89, 2.19, 1.79, 2.09, 2.29, 2.49],
    ["Proszek do zmywarki",   19.99,18.99,21.99,17.99,20.99,22.99,23.99],
    ["Puffed corn",            3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Pumpernikiel",           5.99, 5.49, 6.49, 5.49, 6.19, 6.79, 6.99],
    ["Ręczniki papierowe",     9.99, 9.49,10.99, 9.49,10.49,11.99,12.49],
    ["Rodzynki",               5.99, 5.79, 6.79, 5.49, 6.29, 6.99, 7.29],
    ["Rogaliki",               4.99, 4.49, 5.49, 4.49, 5.19, 5.79, 5.99],
    ["Ryż basmati",            6.99, 6.49, 7.99, 6.49, 7.29, 7.99, 8.49],
    ["Ryż brązowy",            5.99, 5.79, 6.79, 5.49, 6.29, 6.99, 7.29],
    ["Ryż jaśminowy",          6.49, 6.29, 7.29, 5.99, 6.79, 7.49, 7.79],
    ["Salami",                 9.99, 9.49,10.99, 9.49,10.49,11.99,12.49],
    ["Sałata",                 2.99, 2.79, 3.29, 2.69, 3.09, 3.49, 3.69],
    ["Sardynki w puszce",      4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Schab",                 16.99,15.99,18.99,15.49,17.99,19.99,20.99],
    ["Seler korzeniowy",       3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Ser Edam",               7.99, 7.49, 8.99, 7.49, 8.29, 9.29, 9.49],
    ["Ser feta",               8.99, 8.49, 9.99, 8.49, 9.49,10.49,10.99],
    ["Ser Gouda",              7.99, 7.49, 8.99, 7.49, 8.29, 9.29, 9.49],
    ["Serek Philadelphia",     7.99, 7.49, 8.99, 7.49, 8.29, 9.29, 9.49],
    ["Serek wiejski",          3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Siemię lniane",          4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Skrobia ziemniaczana",   3.49, 3.29, 3.99, 3.19, 3.69, 3.99, 4.29],
    ["Śledź",                  9.99, 9.49,10.99, 9.49,10.49,11.99,12.49],
    ["Śliwki",                 5.99, 5.49, 6.79, 5.49, 6.29, 6.99, 7.29],
    ["Słonecznik prażony",     3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Śmietana",               2.99, 2.79, 3.29, 2.69, 3.09, 3.49, 3.69],
    ["Śmietana 18%",           2.99, 2.79, 3.29, 2.69, 3.09, 3.49, 3.69],
    ["Śmietana 30%",           4.49, 4.29, 4.99, 4.19, 4.69, 5.19, 5.49],
    ["Śmietanka do kawy",      3.49, 3.29, 3.99, 3.19, 3.69, 3.99, 4.29],
    ["Śmietanka kremówka",     4.49, 4.29, 4.99, 4.19, 4.69, 5.19, 5.49],
    ["Soda oczyszczona",       2.49, 2.29, 2.79, 2.19, 2.59, 2.99, 3.09],
    ["Sok jabłkowy",           4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Sok pomarańczowy",       4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Sos BBQ",                5.99, 5.79, 6.79, 5.49, 6.29, 6.99, 7.29],
    ["Suszone banany",         4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Suszone figi",           6.99, 6.49, 7.99, 6.49, 7.29, 7.99, 8.49],
    ["Suszone jabłka",         5.99, 5.79, 6.79, 5.49, 6.29, 6.99, 7.29],
    ["Suszone mango",          6.99, 6.49, 7.99, 6.49, 7.29, 7.99, 8.49],
    ["Suszone mięso wołowe",  12.99,11.99,14.99,11.99,13.49,14.99,15.99],
    ["Suszone morele",         6.99, 6.49, 7.99, 6.49, 7.29, 7.99, 8.49],
    ["Suszone śliwki",         6.49, 5.99, 7.49, 5.99, 6.79, 7.49, 7.79],
    ["Szparagi",               9.99, 9.49,11.49, 9.49,10.49,11.99,12.49],
    ["Szpinak",                4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Tiger Energy",           4.49, 4.29, 4.99, 4.19, 4.69, 5.19, 5.49],
    ["Toblerone",              7.99, 7.49, 8.99, 7.49, 8.29, 9.29, 9.49],
    ["Truskawki",              9.99, 9.49,10.99, 9.49,10.49,11.99,12.49],
    ["Twaróg",                 4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Tymbark sok",            3.99, 3.79, 4.49, 3.69, 4.19, 4.49, 4.79],
    ["Udka z kurczaka",       12.99,11.99,13.99,11.49,13.29,14.99,15.49],
    ["Wafle czekoladowe",      4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Wafle ryżowe solone",    4.49, 4.29, 4.99, 4.19, 4.69, 5.19, 5.49],
    ["Wafle z kremem",         4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Wędlina drobiowa",       9.99, 9.49,10.99, 9.49,10.49,11.99,12.49],
    ["Winogrona",              6.99, 6.49, 7.99, 6.49, 7.29, 7.99, 8.49],
    ["Wino",                  19.99,17.99,22.99,17.99,20.99,23.99,24.99],
    ["Worki na śmieci",        7.99, 7.49, 8.99, 7.49, 8.29, 9.29, 9.49],
    ["Żelki",                  3.49, 3.29, 3.99, 3.19, 3.69, 3.99, 4.29],
    ["Żelki cola",             3.49, 3.29, 3.99, 3.19, 3.69, 3.99, 4.29],
    ["Żelki kwaśne",           3.49, 3.29, 3.99, 3.19, 3.69, 3.99, 4.29],
    ["Żelki misie",            3.49, 3.29, 3.99, 3.19, 3.69, 3.99, 4.29],
    ["Żelki witaminowe",       4.99, 4.79, 5.49, 4.59, 5.19, 5.79, 5.99],
    ["Ziemniaki",              2.99, 2.79, 3.29, 2.69, 3.09, 3.49, 3.69],
    ["Zott Monte",             2.99, 2.79, 3.29, 2.69, 3.09, 3.49, 3.69],
    ["Zupa w proszku",         2.49, 2.29, 2.79, 2.19, 2.59, 2.99, 3.09]
  ]';
BEGIN
  SELECT id INTO bid     FROM stores WHERE name = 'Biedronka';
  SELECT id INTO lid     FROM stores WHERE name = 'Lidl';
  SELECT id INTO kauf    FROM stores WHERE name = 'Kaufland';
  SELECT id INTO aldi_id FROM stores WHERE name = 'Aldi';
  SELECT id INTO netto   FROM stores WHERE name = 'Netto';
  SELECT id INTO auch    FROM stores WHERE name = 'Auchan';
  SELECT id INTO carr    FROM stores WHERE name = 'Carrefour';

  FOR rec IN SELECT * FROM json_array_elements(items) LOOP
    SELECT id INTO pid FROM products WHERE name ILIKE (rec->>0) LIMIT 1;
    IF pid IS NOT NULL THEN
      -- Biedronka
      IF (rec->>1) IS NOT NULL THEN
        INSERT INTO prices (product_id, store_id, price)
        VALUES (pid, bid, (rec->>1)::DECIMAL)
        ON CONFLICT (product_id, store_id) DO UPDATE SET price = EXCLUDED.price
        WHERE prices.price IS NULL OR prices.price = 0;
      END IF;
      -- Lidl
      IF (rec->>2) IS NOT NULL THEN
        INSERT INTO prices (product_id, store_id, price)
        VALUES (pid, lid, (rec->>2)::DECIMAL)
        ON CONFLICT (product_id, store_id) DO UPDATE SET price = EXCLUDED.price
        WHERE prices.price IS NULL OR prices.price = 0;
      END IF;
      -- Kaufland
      IF (rec->>3) IS NOT NULL THEN
        INSERT INTO prices (product_id, store_id, price)
        VALUES (pid, kauf, (rec->>3)::DECIMAL)
        ON CONFLICT (product_id, store_id) DO UPDATE SET price = EXCLUDED.price
        WHERE prices.price IS NULL OR prices.price = 0;
      END IF;
      -- Aldi
      IF (rec->>4) IS NOT NULL THEN
        INSERT INTO prices (product_id, store_id, price)
        VALUES (pid, aldi_id, (rec->>4)::DECIMAL)
        ON CONFLICT (product_id, store_id) DO UPDATE SET price = EXCLUDED.price
        WHERE prices.price IS NULL OR prices.price = 0;
      END IF;
      -- Netto
      IF (rec->>5) IS NOT NULL THEN
        INSERT INTO prices (product_id, store_id, price)
        VALUES (pid, netto, (rec->>5)::DECIMAL)
        ON CONFLICT (product_id, store_id) DO UPDATE SET price = EXCLUDED.price
        WHERE prices.price IS NULL OR prices.price = 0;
      END IF;
      -- Auchan
      IF (rec->>6) IS NOT NULL THEN
        INSERT INTO prices (product_id, store_id, price)
        VALUES (pid, auch, (rec->>6)::DECIMAL)
        ON CONFLICT (product_id, store_id) DO UPDATE SET price = EXCLUDED.price
        WHERE prices.price IS NULL OR prices.price = 0;
      END IF;
      -- Carrefour
      IF (rec->>7) IS NOT NULL THEN
        INSERT INTO prices (product_id, store_id, price)
        VALUES (pid, carr, (rec->>7)::DECIMAL)
        ON CONFLICT (product_id, store_id) DO UPDATE SET price = EXCLUDED.price
        WHERE prices.price IS NULL OR prices.price = 0;
      END IF;
    END IF;
  END LOOP;
END $$;

-- Coverage check
SELECT s.name, COUNT(*) AS price_count
FROM prices pr
JOIN stores s ON s.id = pr.store_id
GROUP BY s.name ORDER BY s.name;

-- How many products still have no price in ANY store
SELECT COUNT(*) AS products_with_no_prices
FROM products p
WHERE NOT EXISTS (SELECT 1 FROM prices WHERE product_id = p.id);
