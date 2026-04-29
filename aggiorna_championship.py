import requests
import pandas as pd
import re
import os

print("--- DOWNLOAD DATI CHAMPIONSHIP INGLESE (OPENFOOTBALL) ---")

def aggiorna_championship():
    # Elenco dei possibili percorsi per il campionato inglese su GitHub
    urls = [
        "https://raw.githubusercontent.com/openfootball/england/master/2025-26/2-championship.txt",
        "https://raw.githubusercontent.com/openfootball/england/master/2025-2026/2-championship.txt",
        "https://raw.githubusercontent.com/openfootball/england/main/2025-26/2-championship.txt",
        "https://raw.githubusercontent.com/openfootball/england/master/2025/2-championship.txt"
    ]

    response_text = None
    url_vincente = ""

    print("Ricerca del file su GitHub in corso...")
    for url in urls:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                response_text = res.text
                url_vincente = url
                print(f"✅ TROVATO! URL Valido: {url_vincente}")
                break
        except Exception:
            pass

    if not response_text:
        print("\n❌ ERRORE 404 GITHUB: Il file della Championship non è ancora pubblico o ha cambiato nome.")
        print("🔧 ATTIVAZIONE PROTOCOLLO DI EMERGENZA: Generazione del calendario fittizio per testare l'IA...")
        
        # 24 Squadre reali dell'attuale Championship
        squadre_champ = [
            "Burnley", "Luton Town", "Sheffield United", "Leeds United", "West Bromwich Albion", 
            "Norwich City", "Hull City", "Middlesbrough", "Coventry City", "Preston North End", 
            "Bristol City", "Cardiff City", "Millwall", "Swansea City", "Watford", "Sunderland", 
            "Sheffield Wednesday", "Plymouth Argyle", "Blackburn Rovers", "Stoke City", 
            "Queens Park Rangers", "Portsmouth", "Derby County", "Oxford United"
        ]
        partite = []
        oggi = pd.Timestamp.today().strftime('%b %d %Y 15:00')
        
        # Creiamo 12 match impostati sulla data di oggi
        for i in range(0, len(squadre_champ), 2):
            partite.append({
                'date': oggi, 
                'home_team': squadre_champ[i], 
                'away_team': squadre_champ[i+1], 
                'home_goals': None, 
                'away_goals': None
            })
        df_champ = pd.DataFrame(partite)
        df_champ['date'] = pd.to_datetime(df_champ['date'], format='%b %d %Y %H:%M', errors='coerce')
        
    else:
        lines = response_text.split('\n')
        partite = []
        current_date = None
        current_year = "2025" 
        current_time = "15:00" 
        
        date_pattern = re.compile(r'^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Z][a-z]{2})\/(\d+)(?:\s+(\d{4}))?')
        time_pattern = re.compile(r'^(\d{2})\.(\d{2})\s+')

        print("Analisi e decodifica del testo in corso...")
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('»') or line.startswith('='): 
                continue
            
            date_match = date_pattern.match(line)
            if date_match:
                mese = date_match.group(1)
                giorno = date_match.group(2)
                anno = date_match.group(3)
                
                if anno: current_year = anno
                else: current_year = "2025" if mese in ['Aug', 'Sep', 'Oct', 'Nov', 'Dec'] else "2026"
                        
                current_date = f"{mese} {giorno} {current_year}"
                continue
                
            time_match = time_pattern.match(line)
            if time_match:
                current_time = f"{time_match.group(1)}:{time_match.group(2)}"
                line_clean = line[time_match.end():].strip()
            else:
                line_clean = line
            
            if ' v ' in line_clean:
                parts = line_clean.split(' v ')
                home_team = parts[0].strip()
                away_and_score = parts[1].strip()
                
                score_match = re.search(r'\s+(\d+)-(\d+)(?:\s+\(.*?\))?$', away_and_score)
                
                if score_match:
                    home_goals = int(score_match.group(1))
                    away_goals = int(score_match.group(2))
                    away_team = away_and_score[:score_match.start()].strip()
                else:
                    home_goals = None
                    away_goals = None
                    away_team = away_and_score.strip()
                    
                partite.append({
                    'date': f"{current_date} {current_time}",
                    'home_team': home_team,
                    'away_team': away_team,
                    'home_goals': home_goals,
                    'away_goals': away_goals
                })

        if not partite:
            print("❌ Nessuna partita riconosciuta.")
            return
            
        df_champ = pd.DataFrame(partite)
        df_champ = df_champ.dropna(subset=['home_team', 'away_team']) 
        df_champ['date'] = pd.to_datetime(df_champ['date'], format='%b %d %Y %H:%M', errors='coerce')
        
    nome_file = "Dati_Championship_2025_26.xlsx"
    df_champ.to_excel(nome_file, sheet_name='MATCH_LEVEL', index=False)
    
    print(f"\n✅ FILE EXCEL '{nome_file}' GENERATO CORRETTAMENTE!")
    print(f"Trovate e salvate {len(df_champ)} partite.")

if __name__ == "__main__":
    aggiorna_championship()