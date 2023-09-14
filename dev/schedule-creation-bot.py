import requests
import csv
import os
import json
import io

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
            home_team_data = next(team for team in game['competitions'][0]['competitors'] if team["homeAway"] == "home")
            away_team_data = next(team for team in game['competitions'][0]['competitors'] if team["homeAway"] == "away")

            game_details = {
                'Week': f"Week {game['week']['number']}",
                'Date & Time': game['competitions'][0]['date'],
                'Stadium': game['competitions'][0]['venue']['fullName'],
                'Gamecast Link': game['links'][0]['href'],
                'Home Team': home_team_data["team"]["displayName"],
                'Away Team': away_team_data["team"]["displayName"],
                'Home Team Short': home_team_data["team"]["abbreviation"],
                'Away Team Short': away_team_data["team"]["abbreviation"]
            }
            games.append(game_details)
    
    return games

def update_gist_with_schedule(games):
    """Update the Gist with the fetched schedule."""
    gist_url = f"https://api.github.com/gists/{GIST_ID}"
    
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Content-Type': 'application/json',
    }

    # Convert games list to CSV format
    output = io.StringIO()
    fieldnames = ['Week', 'Date & Time', 'Stadium', 'Home Team', 'Away Team', 'Home Team Short', 'Away Team Short', 'Gamecast Link', 'Squabblr Hash ID', 'Status']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for game in games:
        writer.writerow(game)
    
    csv_content = output.getvalue()

    data = {
        "files": {
            "nfl-schedule.csv": {
                "content": csv_content
            }
        }
    }
    
    response = requests.patch(gist_url, headers=headers, json=data)
    if response.status_code != 200:
        print(f"Failed to update Gist. Status code: {response.status_code}. Response: {response.text}")
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
