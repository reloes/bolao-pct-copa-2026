# -*- coding: utf-8 -*-
"""
Fonte ÚNICA de dados da tabela da Copa do Mundo 2026 (verificada).
- Times em inglês (canônico); use TEAM_PT para exibir em português.
- Datas e horários = horário LOCAL de cada sede.
- Fonte: Wikipédia (páginas por grupo + knockout stage), cruzada com NBC/ESPN.
  Grupos A e C reconferidos diretamente. Verificado em 2026-05-30.
Reutilizado por build_tabela_copa_2026.py e (futuramente) pelo motor de apuração.
"""

GROUPS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czechia"],
    "B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["United States", "Paraguay", "Australia", "Türkiye"],
    "E": ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

HOSTS = {"Mexico", "Canada", "United States"}

TEAM_PT = {
    "Mexico": "México", "South Africa": "África do Sul", "South Korea": "Coreia do Sul",
    "Czechia": "República Tcheca", "Canada": "Canadá", "Bosnia and Herzegovina": "Bósnia e Herzegovina",
    "Qatar": "Catar", "Switzerland": "Suíça", "Brazil": "Brasil", "Morocco": "Marrocos",
    "Haiti": "Haiti", "Scotland": "Escócia", "United States": "Estados Unidos", "Paraguay": "Paraguai",
    "Australia": "Austrália", "Türkiye": "Turquia", "Germany": "Alemanha", "Curaçao": "Curaçao",
    "Ivory Coast": "Costa do Marfim", "Ecuador": "Equador", "Netherlands": "Holanda", "Japan": "Japão",
    "Sweden": "Suécia", "Tunisia": "Tunísia", "Belgium": "Bélgica", "Egypt": "Egito", "Iran": "Irã",
    "New Zealand": "Nova Zelândia", "Spain": "Espanha", "Cape Verde": "Cabo Verde",
    "Saudi Arabia": "Arábia Saudita", "Uruguay": "Uruguai", "France": "França", "Senegal": "Senegal",
    "Iraq": "Iraque", "Norway": "Noruega", "Argentina": "Argentina", "Algeria": "Argélia",
    "Austria": "Áustria", "Jordan": "Jordânia", "Portugal": "Portugal", "DR Congo": "Congo (RD)",
    "Uzbekistan": "Uzbequistão", "Colombia": "Colômbia", "England": "Inglaterra", "Croatia": "Croácia",
    "Ghana": "Gana", "Panama": "Panamá",
}

# Ranking FIFA/Coca-Cola masculino — edição de 1º/abr/2026 (a mais recente antes da Copa;
# próxima edição: 11/jun/2026). Usado como critério FINAL de desempate (Art. 13), tanto na
# classificação dos grupos quanto na escolha dos 8 melhores terceiros. Menor nº = melhor.
# Fonte: FIFA/FotMob/whereig.com, cross-check (verificado 2026-05-30).
TEAM_FIFA_RANK = {
    "France": 1, "Spain": 2, "Argentina": 3, "England": 4, "Portugal": 5, "Brazil": 6,
    "Netherlands": 7, "Morocco": 8, "Belgium": 9, "Germany": 10, "Croatia": 11, "Colombia": 13,
    "Senegal": 14, "Mexico": 15, "United States": 16, "Uruguay": 17, "Japan": 18, "Switzerland": 19,
    "Iran": 21, "Türkiye": 22, "Ecuador": 23, "Austria": 24, "South Korea": 25, "Australia": 27,
    "Algeria": 28, "Egypt": 29, "Canada": 30, "Norway": 31, "Panama": 33, "Ivory Coast": 34,
    "Sweden": 38, "Paraguay": 40, "Czechia": 41, "Scotland": 43, "Tunisia": 44, "DR Congo": 46,
    "Uzbekistan": 50, "Qatar": 55, "Iraq": 57, "South Africa": 60, "Saudi Arabia": 61, "Jordan": 63,
    "Bosnia and Herzegovina": 65, "Cape Verde": 69, "Ghana": 74, "Curaçao": 82, "Haiti": 83,
    "New Zealand": 85,
}

STADIUM_CITY = {
    "Estadio Azteca": "Cidade do México", "Estadio Akron": "Guadalajara", "BMO Field": "Toronto",
    "SoFi Stadium": "Los Angeles", "Gillette Stadium": "Boston", "BC Place": "Vancouver",
    "MetLife Stadium": "Nova York/NJ", "Levi's Stadium": "São Francisco",
    "Lincoln Financial Field": "Filadélfia", "NRG Stadium": "Houston", "AT&T Stadium": "Dallas",
    "Estadio BBVA": "Monterrey", "Hard Rock Stadium": "Miami", "Mercedes-Benz Stadium": "Atlanta",
    "Lumen Field": "Seattle", "Arrowhead Stadium": "Kansas City",
}

# (num, data, hora_local, time1, time2, estadio)
GROUP_MATCHES = [
    (1,  "11/jun", "13:00", "Mexico", "South Africa", "Estadio Azteca"),
    (2,  "11/jun", "20:00", "South Korea", "Czechia", "Estadio Akron"),
    (3,  "12/jun", "15:00", "Canada", "Bosnia and Herzegovina", "BMO Field"),
    (4,  "12/jun", "18:00", "United States", "Paraguay", "SoFi Stadium"),
    (5,  "13/jun", "21:00", "Haiti", "Scotland", "Gillette Stadium"),
    (6,  "13/jun", "21:00", "Australia", "Türkiye", "BC Place"),
    (7,  "13/jun", "18:00", "Brazil", "Morocco", "MetLife Stadium"),
    (8,  "13/jun", "12:00", "Qatar", "Switzerland", "Levi's Stadium"),
    (9,  "14/jun", "19:00", "Ivory Coast", "Ecuador", "Lincoln Financial Field"),
    (10, "14/jun", "12:00", "Germany", "Curaçao", "NRG Stadium"),
    (11, "14/jun", "15:00", "Netherlands", "Japan", "AT&T Stadium"),
    (12, "14/jun", "20:00", "Sweden", "Tunisia", "Estadio BBVA"),
    (13, "15/jun", "18:00", "Saudi Arabia", "Uruguay", "Hard Rock Stadium"),
    (14, "15/jun", "12:00", "Spain", "Cape Verde", "Mercedes-Benz Stadium"),
    (15, "15/jun", "18:00", "Iran", "New Zealand", "SoFi Stadium"),
    (16, "15/jun", "12:00", "Belgium", "Egypt", "Lumen Field"),
    (17, "16/jun", "15:00", "France", "Senegal", "MetLife Stadium"),
    (18, "16/jun", "18:00", "Iraq", "Norway", "Gillette Stadium"),
    (19, "16/jun", "19:00", "Argentina", "Algeria", "Arrowhead Stadium"),
    (20, "16/jun", "21:00", "Austria", "Jordan", "Levi's Stadium"),
    (21, "17/jun", "19:00", "Ghana", "Panama", "BMO Field"),
    (22, "17/jun", "15:00", "England", "Croatia", "AT&T Stadium"),
    (23, "17/jun", "12:00", "Portugal", "DR Congo", "NRG Stadium"),
    (24, "17/jun", "20:00", "Uzbekistan", "Colombia", "Estadio Azteca"),
    (25, "18/jun", "12:00", "Czechia", "South Africa", "Mercedes-Benz Stadium"),
    (26, "18/jun", "12:00", "Switzerland", "Bosnia and Herzegovina", "SoFi Stadium"),
    (27, "18/jun", "15:00", "Canada", "Qatar", "BC Place"),
    (28, "18/jun", "19:00", "Mexico", "South Korea", "Estadio Akron"),
    (29, "19/jun", "20:30", "Brazil", "Haiti", "Lincoln Financial Field"),
    (30, "19/jun", "18:00", "Scotland", "Morocco", "Gillette Stadium"),
    (31, "19/jun", "20:00", "Türkiye", "Paraguay", "Levi's Stadium"),
    (32, "19/jun", "12:00", "United States", "Australia", "Lumen Field"),
    (33, "20/jun", "16:00", "Germany", "Ivory Coast", "BMO Field"),
    (34, "20/jun", "19:00", "Ecuador", "Curaçao", "Arrowhead Stadium"),
    (35, "20/jun", "12:00", "Netherlands", "Sweden", "NRG Stadium"),
    (36, "20/jun", "22:00", "Tunisia", "Japan", "Estadio BBVA"),
    (37, "21/jun", "18:00", "Uruguay", "Cape Verde", "Hard Rock Stadium"),
    (38, "21/jun", "12:00", "Spain", "Saudi Arabia", "Mercedes-Benz Stadium"),
    (39, "21/jun", "12:00", "Belgium", "Iran", "SoFi Stadium"),
    (40, "21/jun", "18:00", "New Zealand", "Egypt", "BC Place"),
    (41, "22/jun", "20:00", "Norway", "Senegal", "MetLife Stadium"),
    (42, "22/jun", "17:00", "France", "Iraq", "Lincoln Financial Field"),
    (43, "22/jun", "12:00", "Argentina", "Austria", "AT&T Stadium"),
    (44, "22/jun", "20:00", "Jordan", "Algeria", "Levi's Stadium"),
    (45, "23/jun", "16:00", "England", "Ghana", "Gillette Stadium"),
    (46, "23/jun", "19:00", "Panama", "Croatia", "BMO Field"),
    (47, "23/jun", "12:00", "Portugal", "Uzbekistan", "NRG Stadium"),
    (48, "23/jun", "20:00", "Colombia", "DR Congo", "Estadio Akron"),
    (49, "24/jun", "18:00", "Scotland", "Brazil", "Hard Rock Stadium"),
    (50, "24/jun", "18:00", "Morocco", "Haiti", "Mercedes-Benz Stadium"),
    (51, "24/jun", "12:00", "Switzerland", "Canada", "BC Place"),
    (52, "24/jun", "12:00", "Bosnia and Herzegovina", "Qatar", "Lumen Field"),
    (53, "24/jun", "19:00", "Czechia", "Mexico", "Estadio Azteca"),
    (54, "24/jun", "19:00", "South Africa", "South Korea", "Estadio BBVA"),
    (55, "25/jun", "16:00", "Curaçao", "Ivory Coast", "Lincoln Financial Field"),
    (56, "25/jun", "16:00", "Ecuador", "Germany", "MetLife Stadium"),
    (57, "25/jun", "18:00", "Japan", "Sweden", "AT&T Stadium"),
    (58, "25/jun", "18:00", "Tunisia", "Netherlands", "Arrowhead Stadium"),
    (59, "25/jun", "19:00", "Türkiye", "United States", "SoFi Stadium"),
    (60, "25/jun", "19:00", "Paraguay", "Australia", "Levi's Stadium"),
    (61, "26/jun", "15:00", "Norway", "France", "Gillette Stadium"),
    (62, "26/jun", "15:00", "Senegal", "Iraq", "BMO Field"),
    (63, "26/jun", "20:00", "Egypt", "Iran", "Lumen Field"),
    (64, "26/jun", "20:00", "New Zealand", "Belgium", "BC Place"),
    (65, "26/jun", "19:00", "Cape Verde", "Saudi Arabia", "NRG Stadium"),
    (66, "26/jun", "18:00", "Uruguay", "Spain", "Estadio Akron"),
    (67, "27/jun", "17:00", "Panama", "England", "MetLife Stadium"),
    (68, "27/jun", "17:00", "Croatia", "Ghana", "Lincoln Financial Field"),
    (69, "27/jun", "21:00", "Algeria", "Austria", "Arrowhead Stadium"),
    (70, "27/jun", "21:00", "Jordan", "Argentina", "AT&T Stadium"),
    (71, "27/jun", "19:30", "Colombia", "Portugal", "Hard Rock Stadium"),
    (72, "27/jun", "19:30", "DR Congo", "Uzbekistan", "Mercedes-Benz Stadium"),
]

# (num, fase, data, estadio, slot1, slot2)   fase in {R32,R16,QF,SF,3P,F}
KO_MATCHES = [
    (73,  "R32", "28/jun", "SoFi Stadium", "2A", "2B"),
    (74,  "R32", "29/jun", "Gillette Stadium", "1E", "3(A/B/C/D/F)"),
    (75,  "R32", "29/jun", "Estadio BBVA", "1F", "2C"),
    (76,  "R32", "29/jun", "NRG Stadium", "1C", "2F"),
    (77,  "R32", "30/jun", "MetLife Stadium", "1I", "3(C/D/F/G/H)"),
    (78,  "R32", "30/jun", "AT&T Stadium", "2E", "2I"),
    (79,  "R32", "30/jun", "Estadio Azteca", "1A", "3(C/E/F/H/I)"),
    (80,  "R32", "01/jul", "Mercedes-Benz Stadium", "1L", "3(E/H/I/J/K)"),
    (81,  "R32", "01/jul", "Levi's Stadium", "1D", "3(B/E/F/I/J)"),
    (82,  "R32", "01/jul", "Lumen Field", "1G", "3(A/E/H/I/J)"),
    (83,  "R32", "02/jul", "BMO Field", "2K", "2L"),
    (84,  "R32", "02/jul", "SoFi Stadium", "1H", "2J"),
    (85,  "R32", "02/jul", "BC Place", "1B", "3(E/F/G/I/J)"),
    (86,  "R32", "03/jul", "Hard Rock Stadium", "1J", "2H"),
    (87,  "R32", "03/jul", "Arrowhead Stadium", "1K", "3(D/E/I/J/L)"),
    (88,  "R32", "03/jul", "AT&T Stadium", "2D", "2G"),
    (89,  "R16", "04/jul", "Lincoln Financial Field", "W74", "W77"),
    (90,  "R16", "04/jul", "NRG Stadium", "W73", "W75"),
    (91,  "R16", "05/jul", "MetLife Stadium", "W76", "W78"),
    (92,  "R16", "05/jul", "Estadio Azteca", "W79", "W80"),
    (93,  "R16", "06/jul", "AT&T Stadium", "W83", "W84"),
    (94,  "R16", "06/jul", "Lumen Field", "W81", "W82"),
    (95,  "R16", "07/jul", "Mercedes-Benz Stadium", "W86", "W88"),
    (96,  "R16", "07/jul", "BC Place", "W85", "W87"),
    (97,  "QF",  "09/jul", "Gillette Stadium", "W89", "W90"),
    (98,  "QF",  "10/jul", "SoFi Stadium", "W93", "W94"),
    (99,  "QF",  "11/jul", "Hard Rock Stadium", "W91", "W92"),
    (100, "QF",  "11/jul", "Arrowhead Stadium", "W95", "W96"),
    (101, "SF",  "14/jul", "AT&T Stadium", "W97", "W98"),
    (102, "SF",  "15/jul", "Mercedes-Benz Stadium", "W99", "W100"),
    (103, "3P",  "18/jul", "Hard Rock Stadium", "L101", "L102"),
    (104, "F",   "19/jul", "MetLife Stadium", "W101", "W102"),
]
