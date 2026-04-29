import soccerdata as sd
import pandas as pd
import numpy as np
import os
import time

LEAGUES = ['ITA-Serie A', 'ENG-Premier League', 'ESP-La Liga', 'FRA-Ligue 1', 'GER-Bundesliga']

# Stagioni ridotte per massima precisione
SEASON = ['2023', '2024', '2025']

print("--- DOWNLOAD DATI AVANZATI STABILI ---")

def scarica_con_ritentativi(funzione, nome_operazione, max_tentativi=4, attesa=5):
    print(f"Avvio: {nome_operazione}...")
    for tentativo in range(1, max_tentativi + 1):
        try:
            return funzione()
        except Exception as e:
            print(f"⚠️ Errore di connessione (Tentativo {tentativo}/{max_tentativi})")
            if tentativo < max_tentativi:
                print(f"⏳ Riprovo automaticamente tra {attesa} secondi...")
                time.sleep(attesa)
            else:
                raise Exception(f"Impossibile completare {nome_operazione}. Server offline.")

try:
    understat = sd.Understat(leagues=LEAGUES, seasons=SEASON)

    print("Scarico partite...")
    schedule_raw = scarica_con_ritentativi(understat.read_schedule, "Scarico partite")
    schedule = schedule_raw.reset_index()

    numeric_cols = ["home_goals", "away_goals", "home_xg", "away_xg"]
    for col in numeric_cols:
        if col in schedule.columns:
            schedule[col] = pd.to_numeric(schedule[col], errors="coerce")

    schedule["played"] = schedule["home_goals"].notna() & schedule["away_goals"].notna()
    schedule["home_points"] = 0
    schedule["away_points"] = 0

    mask = schedule["played"]
    schedule.loc[mask & (schedule["home_goals"] > schedule["away_goals"]), "home_points"] = 3
    schedule.loc[mask & (schedule["home_goals"] < schedule["away_goals"]), "away_points"] = 3
    schedule.loc[mask & (schedule["home_goals"] == schedule["away_goals"]), ["home_points", "away_points"]] = 1

    schedule["xg_diff"] = schedule["home_xg"] - schedule["away_xg"]
    
    # ======================================================
    # FIX FUSO ORARIO (Evita Partite Sfasate)
    # ======================================================
    schedule["date"] = pd.to_datetime(schedule["date"], errors="coerce")
    # Se il dato arriva pulito ma in UTC, forziamo la conversione all'ora di Roma
    if schedule["date"].dt.tz is None:
        schedule["date"] = schedule["date"].dt.tz_localize("UTC")
    schedule["date"] = schedule["date"].dt.tz_convert("Europe/Rome").dt.tz_localize(None)
    
    schedule = schedule.sort_values("date")

    print("Calcolo rolling form...")
    schedule["home_form_5"] = 0.0
    schedule["away_form_5"] = 0.0

    teams = pd.unique(schedule[["home_team", "away_team"]].values.ravel())
    for team in teams:
        mask_home = schedule["home_team"] == team
        mask_away = schedule["away_team"] == team
        schedule.loc[mask_home, "home_form_5"] = schedule.loc[mask_home, "home_points"].shift().rolling(5, min_periods=1).mean().fillna(0)
        schedule.loc[mask_away, "away_form_5"] = schedule.loc[mask_away, "away_points"].shift().rolling(5, min_periods=1).mean().fillna(0)

    print("Scarico statistiche giocatori...")
    players_raw = scarica_con_ritentativi(understat.read_player_season_stats, "Scarico statistiche giocatori")
    players = players_raw.reset_index()

    players["minutes"] = pd.to_numeric(players["minutes"], errors="coerce")
    players["xg"] = pd.to_numeric(players["xg"], errors="coerce")
    players["xa"] = pd.to_numeric(players["xa"], errors="coerce")
    players["goals"] = pd.to_numeric(players["goals"], errors="coerce")

    players["xg_per90"] = np.where(players["minutes"] > 0, players["xg"] / (players["minutes"] / 90), 0)
    players["xa_per90"] = np.where(players["minutes"] > 0, players["xa"] / (players["minutes"] / 90), 0)
    players["goals_per90"] = np.where(players["minutes"] > 0, players["goals"] / (players["minutes"] / 90), 0)

    players.replace([np.inf, -np.inf], 0, inplace=True)
    players.fillna(0, inplace=True) 

    print("Calcolo classifica...")
    played_matches = schedule[schedule["played"]]
    home_table = played_matches.groupby("home_team").agg({"home_points": "sum", "home_goals": "sum", "away_goals": "sum", "home_xg": "sum", "away_xg": "sum"})
    away_table = played_matches.groupby("away_team").agg({"away_points": "sum", "away_goals": "sum", "home_goals": "sum", "away_xg": "sum", "home_xg": "sum"})

    table = pd.DataFrame()
    table["points"] = home_table["home_points"] + away_table["away_points"]
    table["goals_scored"] = home_table["home_goals"] + away_table["away_goals"]
    table["goals_conceded"] = home_table["away_goals"] + away_table["home_goals"]
    table["xg"] = home_table["home_xg"] + away_table["away_xg"]
    table["xga"] = home_table["away_xg"] + away_table["home_xg"]
    table["goal_diff"] = table["goals_scored"] - table["goals_conceded"]
    table["xg_diff"] = table["xg"] - table["xga"]

    table = table.sort_values(["points", "goal_diff"], ascending=False).reset_index()
    table.rename(columns={"home_team": "team", "index": "team"}, inplace=True)

    print("Scarico statistiche avanzate di squadra...")
    team_stats_raw = scarica_con_ritentativi(understat.read_team_match_stats, "Scarico statistiche avanzate di squadra")
    team_stats = team_stats_raw.reset_index()
    team_stats.fillna(0, inplace=True)

    print("Salvataggio file Excel in corso...")
    nome_file = "Dati_Understat_Storico_2014_2026.xlsx"
    with pd.ExcelWriter(nome_file) as writer:
        schedule.to_excel(writer, sheet_name='MATCH_LEVEL', index=False)
        players.to_excel(writer, sheet_name='PLAYER_SEASON_STATS', index=False)
        table.to_excel(writer, sheet_name='LEAGUE_TABLES', index=False)
        team_stats.to_excel(writer, sheet_name='TEAM_MATCH_STATS', index=False)

    print(f"\n✅ FILE EXCEL '{nome_file}' GENERATO CORRETTAMENTE!")

except Exception as e:
    print(f"\n❌ ERRORE CRITICO FINALE: {e}")