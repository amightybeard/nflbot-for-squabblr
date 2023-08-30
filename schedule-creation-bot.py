import requests
import csv
import os
import json

GIST_ID = "ef63fd2037741d41c2209b46da0779b8"
GITHUB_TOKEN = os.environ.get('NFLBOT_WRITE_TO_GIST')

def fetch_nfl_schedule():
    # The new ESPN API endpoint for the entire season schedule
    url = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    
    # Fetch the data
    response = requests.get(url)
    data = response.json()
    games = []

    for event in data['events']:
        game_details = {
            'Week': event.get('weekText', 'N/A'),
            'Date & Time': event['status']['type'].get('detail', 'N/A'),
            'Stadium': event.get('location', "N/A"),
            'Gamecast Link': event['links'][0]['href'] if event.get('links') else "N/A",
            'Home Team': 'N/A',
            'Away Team': 'N/A'
        }
        
        competitors = event.get('competitors', [])
        for competitor in competitors:
            if competitor['homeAway'] == 'home':
                game_details['Home Team'] = competitor['team']['displayName']
            else:
                game_details['Away Team'] = competitor['team']['displayName']
        
        games.append(game_details)
    
    return games

def update_gist_with_schedule(games):
    # Convert the games list to CSV format
    csv_data = "Week,Date & Time,Stadium,Home Team,Away Team,Gamecast Link\n"
    for game in games:
        csv_data += f"{game['Week']},{game['Date & Time']},{game['Stadium']},{game['Home Team']},{game['Away Team']},{game['Gamecast Link']}\n"
    
    # Define the API URL for the Gist
    gist_url = f"https://api.github.com/gists/{GIST_ID}"
    
    # Define the headers, including authentication
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Define the payload
    payload = {
        "files": {
            "nfl-schedule.csv": {
                "content": csv_data
            }
        }
    }
    
    # Make the API request to update the Gist
    response = requests.patch(gist_url, headers=headers, json=payload)
    
    return response.status_code == 200

def main():
    # Fetch the entire season schedule from the new ESPN endpoint
    all_games = fetch_nfl_schedule()
    
    # Update the Gist with the fetched schedule
    success = update_gist_with_schedule(all_games)
    
    if success:
        print("Successfully updated the Gist!")
    else:
        print("Failed to update the Gist.")

if __name__ == "__main__":
    main()
