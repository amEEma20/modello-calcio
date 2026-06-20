import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import time

# ========== CONFIGURAZIONE ==========
# Inserisci qui la tua chiave API di football-data.org (gratuita)
# Vai su https://www.football-data.org/client/register e registrati.
# Dopo il login, vai su "My Account" -> "API Token" e copialo.
FOOTBALL_DATA_API_KEY = st.secrets.get("FOOTBALL_DATA_API_KEY", "")  # meglio inserirla dopo

# ========== 1. DATI FIFA (live scraping con fallback) ==========
@st.cache_data(ttl=3600)  # Aggiorna ogni ora
def get_fifa_ranking():
    """Scarica il ranking FIFA attuale da un dataset pubblico aggiornato."""
    url = "https://raw.githubusercontent.com/martj42/international-football-results/main/fifa_rankings.csv"
    try:
        df = pd.read_csv(url)
        # Prendi il ranking più recente per ogni squadra
        latest_date = df["rank_date"].max()
        df = df[df["rank_date"] == latest_date]
        fifa_dict = dict(zip(df["country_full"], df["total_points"]))
        if not fifa_dict:
            raise ValueError("Vuoto")
        return fifa_dict
    except:
        # Fallback con dati statici (top 60)
        return {
            "Argentina": 1860.14, "Francia": 1845.44, "Spagna": 1792.64,
            "Belgio": 1787.44, "Brasile": 1784.09, "Inghilterra": 1774.19,
            "Paesi Bassi": 1742.71, "Portogallo": 1739.83, "Italia": 1718.82,
            "Germania": 1692.19, "Uruguay": 1665.96, "Croazia": 1660.55,
            "Marocco": 1658.49, "Colombia": 1646.59, "Giappone": 1614.18,
            "Stati Uniti": 1611.60, "Senegal": 1596.24, "Iran": 1571.11,
            "Messico": 1566.96, "Ucraina": 1554.94, "Danimarca": 1551.45,
            "Austria": 1529.47, "Nigeria": 1529.32, "Tunisia": 1519.21,
            "Norvegia": 1518.33, "Costa d'Avorio": 1497.03, "Arabia Saudita": 1437.26,
            "Iraq": 1313.20, # e così via... ne ho messe abbastanza per l'esempio
        }

# ========== 2. DATI BANCA MONDIALE (economia) ==========
@st.cache_data(ttl=86400)  # Una volta al giorno
def get_world_bank_data():
    """Scarica gli indicatori macro per tutti i paesi."""
    indicators = {
        "pop": "SP.POP.TOTL",
        "gdp_growth": "NY.GDP.MKTP.KD.ZG",
        "inflation": "FP.CPI.TOTL.ZG",
        "unemployment": "SL.UEM.TOTL.ZS",
        "lending_rate": "FR.INR.LEND",   # tasso interesse
        "debt_gdp": "GC.DOD.TOTL.GD.ZS"
    }
    eco_data = {}
    # Chiamata bulk per tutti i paesi
    for key, ind in indicators.items():
        url = f"http://api.worldbank.org/v2/country/all/indicator/{ind}?format=json&per_page=20000"
        try:
            resp = requests.get(url, timeout=30)
            data = resp.json()
            # Il secondo elemento contiene i record
            for record in data[1]:
                if record["value"] is not None:
                    iso3 = record["countryiso3code"]
                    year = record["date"]
                    value = record["value"]
                    if iso3 not in eco_data:
                        eco_data[iso3] = {}
                    if key not in eco_data[iso3] or year > eco_data[iso3].get(f"{key}_year", "0"):
                        eco_data[iso3][key] = value
                        eco_data[iso3][f"{key}_year"] = year
        except:
            pass
    # Mappatura ISO3 -> nome paese (per abbinare alle squadre)
    # Useremo una tabella di conversione
    return eco_data

# Paese -> ISO3 (solo per nazionali di calcio)
COUNTRY_ISO3 = {
    "Argentina": "ARG", "Australia": "AUS", "Austria": "AUT", "Belgio": "BEL",
    "Brasile": "BRA", "Camerun": "CMR", "Canada": "CAN", "Cile": "CHL",
    "Colombia": "COL", "Costa d'Avorio": "CIV", "Croazia": "HRV", "Danimarca": "DNK",
    "Ecuador": "ECU", "Egitto": "EGY", "Francia": "FRA", "Germania": "DEU",
    "Ghana": "GHA", "Giappone": "JPN", "Inghilterra": "GBR", "Iran": "IRN",
    "Iraq": "IRQ", "Italia": "ITA", "Marocco": "MAR", "Messico": "MEX",
    "Nigeria": "NGA", "Norvegia": "NOR", "Nuova Zelanda": "NZL", "Paesi Bassi": "NLD",
    "Paraguay": "PRY", "Perù": "PER", "Polonia": "POL", "Portogallo": "PRT",
    "Qatar": "QAT", "Romania": "ROU", "Russia": "RUS", "Arabia Saudita": "SAU",
    "Senegal": "SEN", "Serbia": "SRB", "Slovacchia": "SVK", "Slovenia": "SVN",
    "Spagna": "ESP", "Stati Uniti": "USA", "Sudafrica": "ZAF", "Svezia": "SWE",
    "Svizzera": "CHE", "Tunisia": "TUN", "Turchia": "TUR", "Ucraina": "UKR",
    "Uruguay": "URY", "Galles": "GBR", "Costa Rica": "CRI", "Corea del Sud": "KOR",
    "Algeria": "DZA", "Burkina Faso": "BFA", "Mali": "MLI", "Grecia": "GRC",
    "Repubblica Ceca": "CZE", "Ungheria": "HUN", "Scozia": "GBR", "Irlanda": "IRL",
    "Finlandia": "FIN", "Islanda": "ISL", "Slovacchia": "SVK", "Venezuela": "VEN",
    "Panama": "PAN", "Giamaica": "JAM", "Honduras": "HND", "El Salvador": "SLV",
    "Bolivia": "BOL", "Paraguay": "PRY", "Cina": "CHN", "India": "IND",
    "Sud Sudan": "SSD", "Kenya": "KEN", "Uganda": "UGA", "Tanzania": "TZA",
    "Zambia": "ZMB", "Capo Verde": "CPV", "Guinea": "GIN", "Gabon": "GAB",
    "Benin": "BEN", "Madagascar": "MDG", "Namibia": "NAM", "Sierra Leone": "SLE",
    "Togo": "TGO", "Angola": "AGO", "Mozambico": "MOZ", "Rep. Dominicana": "DOM",
    "Guatemala": "GTM", "Cuba": "CUB", "Haiti": "HTI", "Trinidad e Tobago": "TTO",
    "Libano": "LBN", "Siria": "SYR", "Giordania": "JOR", "Kuwait": "KWT",
    "Emirati Arabi Uniti": "ARE", "Bahrein": "BHR", "Oman": "OMN", "Yemen": "YEM",
    "Vietnam": "VNM", "Thailandia": "THA", "Indonesia": "IDN", "Filippine": "PHL",
    "Malaysia": "MYS", "Singapore": "SGP", "Uzbekistan": "UZB", "Kazakistan": "KAZ",
    "Turkmenistan": "TKM", "Kirghizistan": "KGZ", "Georgia": "GEO", "Armenia": "ARM",
    "Azerbaigian": "AZE", "Bielorussia": "BLR", "Moldavia": "MDA", "Estonia": "EST",
    "Lettonia": "LVA", "Lituania": "LTU", "Lussemburgo": "LUX", "Cipro": "CYP",
    "Malta": "MLT", "Israele": "ISR", "Palestina": "PSE", "Montenegro": "MNE",
    "Bosnia ed Erzegovina": "BIH", "Macedonia del Nord": "MKD", "Albania": "ALB",
    "Kosovo": "XKX", "Fær Øer": "FRO", "Andorra": "AND", "San Marino": "SMR",
    "Liechtenstein": "LIE", "Gibilterra": "GIB",
    # Aggiungi altri se necessario
}

# ========== 3. FORMA RECENTE (football-data.org) ==========
@st.cache_data(ttl=3600)
def get_team_id(country_name):
    """Restituisce l'ID Football-Data.org per una nazionale (da dizionario)."""
    mapping = {
        "Germania": 759, "Francia": 773, "Spagna": 760, "Belgio": 805,
        "Argentina": 762, "Brasile": 764, "Inghilterra": 770, "Italia": 784,
        "Paesi Bassi": 8601, "Portogallo": 765, "Croazia": 799, "Uruguay": 793,
        "Giappone": 766, "Stati Uniti": 781, "Messico": 769, "Senegal": 804,
        "Iran": 782, "Marocco": 815, "Tunisia": 816, "Costa d'Avorio": 811,
        "Nigeria": 806, "Norvegia": 808, "Austria": 783, "Arabia Saudita": 801,
        "Iraq": 832, "Corea del Sud": 772, "Australia": 779, "Serbia": 780,
        "Scozia": 814, "Galles": 833, "Ucraina": 790, "Turchia": 803,
        "Russia": 788, "Repubblica Ceca": 798, "Slovacchia": 768, "Ungheria": 795,
        "Romania": 796, "Bulgaria": 786, "Israele": 785, "Sudafrica": 812,
        "Egitto": 802, "Algeria": 791, "Camerun": 800, "Ghana": 807,
        "Mali": 826, "Burkina Faso": 825, "Senegal": 804, "Costa Rica": 821,
        "Canada": 828, "Panama": 829, "Honduras": 830, "Giamaica": 831,
        "Nuova Zelanda": 822, "Cina": 823, "India": 824,
    }
    return mapping.get(country_name, None)

def get_recent_form(team_name, api_key):
    """Recupera le ultime 5 partite e calcola media punti e diff reti."""
    team_id = get_team_id(team_name)
    if not team_id or not api_key:
        return (5, 0.0)  # valore neutro
    url = f"https://api.football-data.org/v4/teams/{team_id}/matches?limit=5&status=FINISHED"
    headers = {"X-Auth-Token": api_key}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        matches = data.get("matches", [])
        if not matches:
            return (5, 0.0)
        points = 0
        goal_diff = 0
        for m in matches:
            home = m["homeTeam"]["name"]
            away = m["awayTeam"]["name"]
            home_goals = m["score"]["fullTime"]["home"]
            away_goals = m["score"]["fullTime"]["away"]
            if home_goals is None or away_goals is None:
                continue
            is_home = (home == team_name or home in [team_name,])
            if is_home:
                scored = home_goals
                conceded = away_goals
            else:
                scored = away_goals
                conceded = home_goals
            goal_diff += (scored - conceded)
            if scored > conceded:
                points += 3
            elif scored == conceded:
                points += 1
        n = len(matches) if matches else 5
        avg_points = points / n * 3  # per portarlo a scala 0-9 (su 3 partite?) Ricalibriamo: punti su 15 possibili.
        # In realtà nelle ultime 5 partite, max 15 punti. Restituiamo i punti totali.
        return (points, goal_diff / n if n else 0.0)
    except:
        return (5, 0.0)

# ========== 4. CORREZIONE METEO (opzionale) ==========
def get_weather_penalty(city, country, match_date):
    """Restituisce un delta xG in base a temperatura e umidità."""
    if not city:
        return 0.0, 0.0
    # Geocoding città
    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=it"
    try:
        geo_resp = requests.get(geo_url, timeout=5)
        geo_data = geo_resp.json()
        if "results" not in geo_data or not geo_data["results"]:
            return 0.0, 0.0
        lat = geo_data["results"][0]["latitude"]
        lon = geo_data["results"][0]["longitude"]
    except:
        return 0.0, 0.0

    # Meteo per la data
    try:
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relativehumidity_2m&timezone=auto&start_date={match_date}&end_date={match_date}"
        w_resp = requests.get(weather_url, timeout=5)
        w_data = w_resp.json()
        temps = w_data["hourly"]["temperature_2m"]
        hums = w_data["hourly"]["relativehumidity_2m"]
        # Temperatura media nelle ore diurne (12-18 UTC)
        day_temps = [t for i, t in enumerate(temps) if 12 <= int(w_data["hourly"]["time"][i][-5:-3]) <= 18]
        if not day_temps:
            avg_temp = sum(temps)/len(temps)
        else:
            avg_temp = sum(day_temps)/len(day_temps)
        avg_hum = sum(hums)/len(hums)

        # Penalità: se temperatura > 30°C, piccolo malus a squadre abituate al freddo (da applicare dopo)
        # Per ora restituiamo (penalty_temp, penalty_hum) da usare manualmente.
        # Decidiamo: restituiamo la temperatura, poi nel modello assegneremo un delta in base alla nazionalità.
        return avg_temp, avg_hum
    except:
        return 0.0, 0.0

# ========== 5. MODELLO ==========
def normalize(value, min_val, max_val):
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)

def compute_eco_score(iso3, eco_data):
    """Calcola il punteggio economico da 0 a 1."""
    if iso3 not in eco_data:
        return 0.5  # neutro
    data = eco_data[iso3]
    # Valori di default se mancanti
    pop = data.get("pop", 50e6)
    gdp = data.get("gdp_growth", 2.0)
    infl = data.get("inflation", 3.0)
    unemp = data.get("unemployment", 6.0)
    lending = data.get("lending_rate", 5.0)
    debt = data.get("debt_gdp", 60.0)

    # Usiamo tutti i paesi disponibili per normalizzare (approssimiamo con range fissi)
    pop_score = min(1, pop / 1.5e9)  # max ~India
    gdp_score = max(0, min(1, (gdp + 10) / 20))  # range -10% a +10%
    infl_score = max(0, 1 - infl/50)  # 0% infl -> 1, 50% -> 0
    unemp_score = max(0, 1 - unemp/30)
    if lending <= 5:
        int_score = 1
    else:
        int_score = max(0, 1 - (lending - 5)/20)
    debt_score = max(0, 1 - debt/200)
    weights = [0.25, 0.25, 0.15, 0.15, 0.10, 0.10]
    score = (pop_score*weights[0] + gdp_score*weights[1] +
             infl_score*weights[2] + unemp_score*weights[3] +
             int_score*weights[4] + debt_score*weights[5])
    return max(0.01, min(0.99, score))

def get_strength(team, fifa_dict, eco_data):
    all_fifa = list(fifa_dict.values())
    fifa_min, fifa_max = min(all_fifa), max(all_fifa)
    fifa_score = normalize(fifa_dict.get(team, fifa_min), fifa_min, fifa_max)
    iso3 = COUNTRY_ISO3.get(team, None)
    eco_score = compute_eco_score(iso3, eco_data) if iso3 else 0.5
    return 0.5 * fifa_score + 0.5 * eco_score

def expected_goals(team_a, team_b, fifa, eco_data, form_a, form_b, weather_temp=None):
    strength_a = get_strength(team_a, fifa, eco_data)
    strength_b = get_strength(team_b, fifa, eco_data)
    diff = strength_a - strength_b
    xg_a = 1.2 + 1.1 * diff
    xg_b = 1.2 - 1.1 * diff

    # Forma recente: punti (max 15) e diff reti
    pts_a, gd_a = form_a
    pts_b, gd_b = form_b
    form_delta = (pts_a/15 - pts_b/15) * 0.4 + (gd_a - gd_b) * 0.1
    xg_a += form_delta
    xg_b -= form_delta

    # Clima: se temperatura >30°C, penalizza squadre nordiche (lista semplicistica)
    if weather_temp and weather_temp > 30:
        cold_teams = ["Norvegia", "Svezia", "Finlandia", "Islanda", "Russia", "Canada",
                      "Danimarca", "Inghilterra", "Scozia", "Galles", "Irlanda",
                      "Paesi Bassi", "Belgio", "Germania", "Polonia", "Ucraina",
                      "Repubblica Ceca", "Slovacchia", "Austria", "Svizzera"]
        if team_a in cold_teams:
            xg_a -= 0.15
        if team_b in cold_teams:
            xg_b -= 0.15

    xg_a = max(0.2, xg_a)
    xg_b = max(0.2, xg_b)
    return xg_a, xg_b

def simulate_match(xg_a, xg_b, n_sim=10000):
    goals_a = np.random.poisson(xg_a, n_sim)
    goals_b = np.random.poisson(xg_b, n_sim)
    results = {"1": 0, "X": 0, "2": 0, "GG": 0, "Over2.5": 0, "Under4.5": 0}
    for ga, gb in zip(goals_a, goals_b):
        if ga > gb:
            results["1"] += 1
        elif ga == gb:
            results["X"] += 1
        else:
            results["2"] += 1
        if ga > 0 and gb > 0:
            results["GG"] += 1
        if ga + gb > 2.5:
            results["Over2.5"] += 1
        if ga + gb < 4.5:
            results["Under4.5"] += 1
    return {k: v/n_sim for k, v in results.items()}

def best_bets(probs, xg_a, xg_b):
    advice = []
    if probs["1"] > 0.60:
        advice.append("1 (Vincente Squadra 1)")
    elif probs["2"] > 0.60:
        advice.append("2 (Vincente Squadra 2)")
    if probs["GG"] > 0.48:
        advice.append("Entrambe Segnano (GG)")
    if probs["Over2.5"] > 0.55:
        advice.append("Over 2.5")
    if probs["1"] > 0.70 and (xg_a - xg_b) > 1.5:
        advice.append("Squadra 1 -1.5")
    if probs["2"] > 0.70 and (xg_b - xg_a) > 1.5:
        advice.append("Squadra 2 -1.5")
    return advice if advice else ["Nessuna giocata forte"]

# ========== INTERFACCIA ==========
st.set_page_config(page_title="Modello Sullivan-Bissett", layout="wide")
st.title("⚽ Previsioni calcio con 50% FIFA + 50% Economia")
st.markdown("Dati reali da FIFA, Banca Mondiale, Football-Data.org e Open-Meteo.")

# Sidebar per chiavi e parametri
with st.sidebar:
    st.header("⚙️ Impostazioni")
    api_key = st.text_input("Football-Data.org API Key", value=FOOTBALL_DATA_API_KEY, type="password",
                            help="Registrati gratis su football-data.org -> My Account -> API Token")
    st.markdown("[Ottieni la chiave qui](https://www.football-data.org/client/register)")
    use_weather = st.checkbox("Considera meteo della città", value=False)
    if use_weather:
        city = st.text_input("Città della partita", "Milano")
        country = st.text_input("Paese", "Italia")
        match_date = st.date_input("Data partita", datetime.today())
    else:
        city = country = match_date = None

    st.markdown("---")
    st.caption("Modello basato su Sullivan-Bissett (50% ranking FIFA, 50% macroeconomia + forma + meteo)")

# Caricamento dati
fifa_ranking = get_fifa_ranking()
eco_data = get_world_bank_data()
teams = sorted(fifa_ranking.keys())

col1, col2, col3 = st.columns([2,1,2])
with col1:
    team_a = st.selectbox("Squadra 1", teams)
with col3:
    team_b = st.selectbox("Squadra 2", teams)

if team_a == team_b:
    st.error("Scegli due squadre diverse.")
else:
    with st.spinner("Calcolo in corso..."):
        # Forma recente
        form_a = get_recent_form(team_a, api_key) if api_key else (5, 0.0)
        form_b = get_recent_form(team_b, api_key) if api_key else (5, 0.0)

        # Meteo
        temp = None
        if use_weather and city and match_date:
            temp, hum = get_weather_penalty(city, country, match_date.isoformat())
            st.write(f"🌡️ Temperatura media diurna: {temp:.1f}°C, Umidità: {hum:.0f}%")

        xg_a, xg_b = expected_goals(team_a, team_b, fifa_ranking, eco_data,
                                    form_a, form_b, temp)
        probs = simulate_match(xg_a, xg_b)

    st.subheader(f"{team_a} vs {team_b}")
    c1, c2 = st.columns(2)
    c1.metric(f"xG {team_a}", round(xg_a, 2))
    c2.metric(f"xG {team_b}", round(xg_b, 2))

    st.write("### Probabilità (simulazione 10.000 partite)")
    prob_df = pd.DataFrame({
        "Esito": ["1", "X", "2", "Entrambe Segnano", "Over 2.5", "Under 4.5"],
        "%": [f"{probs['1']:.1%}", f"{probs['X']:.1%}", f"{probs['2']:.1%}",
              f"{probs['GG']:.1%}", f"{probs['Over2.5']:.1%}", f"{probs['Under4.5']:.1%}"]
    })
    st.table(prob_df)

    bets = best_bets(probs, xg_a, xg_b)
    st.success("**Giocate consigliate:** " + ", ".join(bets))

    # Mostra forza
    with st.expander("🔍 Dettaglio punteggi di forza"):
        str_a = get_strength(team_a, fifa_ranking, eco_data)
        str_b = get_strength(team_b, fifa_ranking, eco_data)
        st.write(f"{team_a}: {str_a:.3f}, {team_b}: {str_b:.3f}")
        st.caption("0=peggiore, 1=migliore combinazione FIFA+Economia.")
