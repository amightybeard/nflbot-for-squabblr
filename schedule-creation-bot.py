import requests
import csv
import os
import json
import logging

logging.basicConfig(level=logging.INFO)

GIST_ID = "ef63fd2037741d41c2209b46da0779b8"
GITHUB_TOKEN = os.environ.get('NFLBOT_WRITE_TO_GIST')

def fetch_nfl_schedule_for_week(week_number):
    # Define the API URL
    url = f"https://site.web.api.espn.com/apis/v2/scoreboard/header?sport=football&league=nfl&region=us&lang=en&contentorigin=espn&buyWindow=1m&showAirings=buy%2Clive%2Creplay&showZipLookup=true&tz=America%2FNew_York"
    
    # Fetch the data
    response = requests.get(url)
    data = response.json()
    events = data['sports'][0]['leagues'][0]['events']
    
    # List to hold the game details
    games = []
    
    for event in events:
        # Extract necessary information
        game_details = {
            'Week': event['weekText'],
            'Date & Time': event['fullStatus']['type']['detail'],
            'Stadium': event['location'],
            'Gamecast Link': event['link']
        }
        
        for competitor in event['competitors']:
            if competitor['homeAway'] == 'home':
                game_details['Home Team'] = competitor['displayName']
            else:
                game_details['Away Team'] = competitor['displayName']
        
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
    # Loop through all weeks (1 to 18) and fetch the schedule
    all_games = []
    for week in range(1, 19):
        all_games.extend(fetch_nfl_schedule_for_week(week))
    
    # Update the Gist with the fetched schedule
    success = update_gist_with_schedule(all_games)
    
    if success:
        print("Successfully updated the Gist!")
    else:
        print("Failed to update the Gist.")

if __name__ == "__main__":
    main()
