import requests
import pandas as pd
import re
import os

print("--- DOWNLOAD DATI SERIE B (OPENFOOTBALL) ---")

# L'URL corretto del database
URL = "https://raw.githubusercontent.com/openfootball/italy/master/2025-26/2-serieb.txt"

def aggiorna_serie_b():
    try:
        print(f"Connessione al database GitHub: {URL} ...")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(URL, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"❌ Errore scaricamento: Codice {response.status_code}.")
            return

        lines = response.text.split('\n')
        
        partite = []
        current_date = None
        current_year = "2025" # Anno di default alla partenza
        
        # Cerca le date formattate come "Sat Aug/23 2025" o "Sun Aug/24"
        date_pattern = re.compile(r'^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Z][a-z]{2})\/(\d+)(?:\s+(\d{4}))?')

        print("Analisi e decodifica del testo in corso...")
        for line in lines:
            line = line.strip()
            
            # Salta righe vuote, commenti o intestazioni di giornata
            if not line or line.startswith('#') or line.startswith('»') or line.startswith('='): 
                continue
            
            # --- 1. Controllo Data ---
            date_match = date_pattern.match(line)
            if date_match:
                mese = date_match.group(1)
                giorno = date_match.group(2)
                anno = date_match.group(3)
                
                if anno:
                    current_year = anno
                else:
                    # Deduzione automatica dell'anno se non è scritto
                    if mese in ['Aug', 'Sep', 'Oct', 'Nov', 'Dec']:
                        current_year = "2025"
                    else:
                        current_year = "2026"
                        
                current_date = f"{mese} {giorno} {current_year}"
                continue
                
            # --- 2. Controllo Partite ---
            # Rimuove l'orario a inizio riga se presente (es. "18.30  Genoa...")
            line_clean = re.sub(r'^\d{2}\.\d{2}\s+', '', line).strip()
            
            # Se la riga contiene il separatore " v " (versus), è una partita
            if ' v ' in line_clean:
                parts = line_clean.split(' v ')
                home_team = parts[0].strip()
                away_and_score = parts[1].strip()
                
                # Cerca il punteggio alla fine della stringa (es. "0-2 (0-1)" o "0-0")
                score_match = re.search(r'\s+(\d+)-(\d+)(?:\s+\(.*?\))?$', away_and_score)
                
                if score_match:
                    # Partita Giocata
                    home_goals = int(score_match.group(1))
                    away_goals = int(score_match.group(2))
                    # Il nome della squadra in trasferta è tutto quello che c'è prima del punteggio
                    away_team = away_and_score[:score_match.start()].strip()
                else:
                    # Partita Futura (Nessun punteggio trovato)
                    home_goals = None
                    away_goals = None
                    away_team = away_and_score.strip()
                    
                partite.append({
                    'date': current_date,
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_goals': home_goals,
                    'away_goals': away_goals
                })

        # --- 3. Costruzione Database ---
        if not partite:
            print("❌ Nessuna partita riconosciuta. Il database è vuoto.")
            return
            
        df_serieb = pd.DataFrame(partite)
        df_serieb = df_serieb.dropna(subset=['home_team', 'away_team']) 
        df_serieb['date'] = pd.to_datetime(df_serieb['date'], format='%b %d %Y', errors='coerce')
        
        # Salvataggio in Excel
        nome_file = "Dati_Serie_B_2025_26.xlsx"
        df_serieb.to_excel(nome_file, sheet_name='MATCH_LEVEL', index=False)
        
        print(f"\n✅ FILE EXCEL '{nome_file}' GENERATO CORRETTAMENTE!")
        print(f"Trovate e formattate {len(df_serieb)} partite (Giocate e Future).")
        print(f"Il file si trova in: {os.path.abspath('.')}")

    except Exception as e:
        print(f"❌ ERRORE CRITICO DURANTE L'ESECUZIONE: {e}")

if __name__ == "__main__":
    aggiorna_serie_b()