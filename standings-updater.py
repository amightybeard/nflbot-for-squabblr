import requests
import csv
import io
import os

# Constants
ESPN_API_URL = "https://cdn.espn.com/core/nfl/standings?xhr=1"
GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN = os.environ.get('NFLBOT_WRITE_TO_GIST')
GIST_ID_STANDINGS = os.environ.get('NFLBOT_STANDINGS_GIST')
GIST_FILENAME_STANDINGS = 'nfl-standings.csv'

def fetch_nfl_standings(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def parse_standings_data(standings_data):
    standings_list = []
    # Iterate over conferences in the 'groups' key
    for conference in standings_data['content']['standings']['groups']:
        # Iterate over divisions in the 'groups' key of each conference
        for division in conference['groups']:
            division_name = division['name']
            # Iterate over team entries in each division
            for team_entry in division['standings']['entries']:
                team_name = team_entry['team']['displayName']
                # Extract the stats in the expected order: Wins, Losses, Ties, Win %
                stats = [stat['displayValue'] for stat in team_entry['stats'][:4]]
                standings_list.append([conference['name'], division_name, team_name] + stats)
    return standings_list

def create_csv_content(standings_data):
    headers = ['Conference', 'Division', 'Team', 'Wins', 'Losses', 'Ties', 'Win %']
    csv_output = io.StringIO()
    csv_writer = csv.writer(csv_output)
    csv_writer.writerow(headers)
    for row in standings_data:
        csv_writer.writerow(row)
    return csv_output.getvalue()

def update_gist(github_token, gist_id, file_name, content):
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json',
    }
    url = f"{GITHUB_API_URL}/gists/{gist_id}"
    data = {
        'files': {
            file_name: {
                'content': content
            }
        }
    }
    response = requests.patch(url, headers=headers, json=data)
    response.raise_for_status()

# Run the update process
try:
    standings_data = fetch_nfl_standings(ESPN_API_URL)
    standings_list = parse_standings_data(standings_data)
    csv_content = create_csv_content(standings_list)
    update_gist(GITHUB_TOKEN, GIST_ID_STANDINGS, GIST_FILENAME_STANDINGS, csv_content)
    print("The Gist has been updated successfully.")
except requests.RequestException as e:
    print(f"An error occurred: {e}")
