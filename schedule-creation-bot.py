import requests
import csv
import os
import json

GIST_ID = "ef63fd2037741d41c2209b46da0779b8"
GITHUB_TOKEN = os.environ.get('NFLBOT_WRITE_TO_GIST')

def fetch_nfl_schedule_for_week(week_number):
    """Fetches the NFL schedule for a given week."""
    url = f"https://cdn.espn.com/core/nfl/schedule?xhr=1&year=2023&week={week_number}"
    response = requests.get(url)
    data = response.json()
    schedule_data = data['content']['schedule']
    
    games = []
    for date, game_data in schedule_data.items():
        for game in game_data['games']:
            game_details = {
                'Week': f"Week {game['week']['number']}",
                'Date & Time': game['competitions'][0]['date'],
                'Stadium': game['competitions'][0]['venue']['fullName'],
                'Gamecast Link': game['links'][0]['href'],
                'Home Team': game['name'].split(" at ")[1],
                'Away Team': game['name'].split(" at ")[0]
            }
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
    
    # Make the request to update the gist
    response = requests.patch(gist_url, headers=headers, json=payload)
    return response.status_code

def main():
    all_games = []
    # Fetching schedule for weeks 1 to 17
    for week in range(1, 18):
        all_games.extend(fetch_nfl_schedule_for_week(week))
    
    # Updating the gist with the consolidated schedule
    status_code = update_gist_with_schedule(all_games)
    if status_code == 200:
        print("Gist updated successfully!")
    else:
        print(f"Failed to update gist. Status code: {status_code}")

if __name__ == "__main__":
    main()
