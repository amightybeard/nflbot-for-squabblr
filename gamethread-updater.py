import requests
import csv
import os
from datetime import datetime, timedelta
import time

SQUABBLES_TOKEN = os.environ.get('SQUABBLES_TOKEN')
GIST_ID = "ef63fd2037741d41c2209b46da0779b8"
GITHUB_TOKEN = os.environ.get('NFLBOT_WRITE_TO_GIST')

def fetch_schedule_from_gist():
    """Fetch the NFL schedule from the gist."""
    gist_url = f"https://api.github.com/gists/{GIST_ID}"
    response = requests.get(gist_url)
    raw_csv = response.json()['files']['nfl-schedule.csv']['content']
    reader = csv.DictReader(raw_csv.splitlines())
    return list(reader)

def fetch_team_record(team_name):
    """Fetch the win-loss-tie record of a team from the standings CSV."""
    with open('csv/nfl_standings.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['Team'] == team_name:
                return row['Wins'], row['Losses'], row['Ties']
    return '0', '0', '0'  # default if not found

def convert_datetime_to_natural_format(dt_string):
    # Convert the provided string into a datetime object
    dt_obj = datetime.strptime(dt_string, '%Y-%m-%dT%H:%MZ')
    
    # Adjust for Eastern Time (ET is UTC-4, but this doesn't account for daylight saving)
    dt_obj = dt_obj - timedelta(hours=4)
    
    # Extract date, time, and am/pm information
    date_format = dt_obj.strftime('%m/%d/%Y')
    time_format = dt_obj.strftime('%-I:%M%p ET')

    return date_format, time_format
    
def filter_games_for_update(schedule):
    today = datetime.today().date()
    games_for_update = []

    for game in schedule:
        game_date = datetime.strptime(game["Date & Time"], '%Y-%m-%dT%H:%MZ').date()

        # If the game is scheduled for today or the status is "STATUS_IN_PROGRESS"
        if game_date == today or game["Status"] == "STATUS_IN_PROGRESS":
            games_for_update.append(game)

    return games_for_update

def fetch_scoreboard_data():
    """Fetch the current scores and game statuses from the ESPN API."""
    ESPN_API_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
    response = requests.get(ESPN_API_URL)
    return response.json()

def fetch_matchup_data(game_id):
    url = f"https://cdn.espn.com/core/nfl/matchup?xhr=1&gameId={game_id}"
    response = requests.get(url)
    return response.json()

def extract_and_format_additional_data(matchup_data):
    # TODO: Extract and format the game stats and leaders using the provided data structure
    game_stats_content = "..."
    game_leaders_content = "..."
    return game_stats_content, game_leaders_content
    
def extract_game_data(game_data):
    """Extract relevant game data from the ESPN API response."""
    home_team_data = next(competitor for competitor in game_data['competitions'][0]['competitors'] if competitor['homeAway'] == 'home')
    away_team_data = next(competitor for competitor in game_data['competitions'][0]['competitors'] if competitor['homeAway'] == 'away')

    # Extract Last Update
    game_status_detail = game_data["status"]["type"]["detail"]

    # Extract scores
    home_team_score = home_team_data['score']
    away_team_score = away_team_data['score']

    # Extract linescores
    home_team_linescores = [int(item["value"]) for item in home_team_data["linescores"]]
    away_team_linescores = [int(item["value"]) for item in away_team_data["linescores"]]

    # Pad linescores with zeros to ensure we have scores for 4 quarters
    while len(home_team_linescores) < 4:
        home_team_linescores.append(0)
    while len(away_team_linescores) < 4:
        away_team_linescores.append(0)

    return {
        'home_team_score': home_team_score,
        'away_team_score': away_team_score,
        'home_team_linescores': home_team_linescores,
        'away_team_linescores': away_team_linescores,
        "game_status_detail": game_status_detail,
        'home_team_shortname': home_team_shortname,
        'away_team_shortname': away_team_shortname
    }

def update_schedule_with_status(gamecast_link, status, home_team_short, away_team_short):
    with open('nfl-schedule.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        schedule = list(reader)
        
    for game in schedule:
        if game["Gamecast Link"] == gamecast_link:
            game["Status"] = status
            game['Home Team Short'] = home_team_short
            game['Away Team Short'] = away_team_short
            break

    # Save the updated schedule back to CSV
    with open('nfl-schedule.csv', 'w', newline='') as csvfile:
        fieldnames = ['Week', 'Date & Time', 'Stadium', 'Home Team', 'Away Team', 'Home Team Short', 'Away Team Short', 'Gamecast Link', 'Squabblr Hash ID', 'Status']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for game in schedule:
            writer.writerow(game)
    
def update_game_thread(game, game_data_from_api):
    """
    Updates the game thread for a specific game based on the latest data from the ESPN API.

    Parameters:
    - game: A dictionary containing game details from the CSV file.
    - game_data_from_api: The specific game data extracted from the ESPN API.
    """
    
    # Extract the short team names from the schedule
    home_team_shortname = game['Home Team Short']
    away_team_shortname = game['Away Team Short']

    # Extract the relevant game data
    game_data = extract_game_data(game_data_from_api, home_team_shortname, away_team_shortname)

    # Fetch the win-loss records (assuming you want to keep this from the previous code)
    away_team_wins, away_team_losses, away_team_ties = fetch_team_record(game["Away Team"])
    home_team_wins, home_team_losses, home_team_ties = fetch_team_record(game["Home Team"])

    # Format the win-loss-tie records
    away_team_record = f"{away_team_wins}-{away_team_losses}"
    if away_team_ties != '0':
        away_team_record += f"-{away_team_ties}"
    
    home_team_record = f"{home_team_wins}-{home_team_losses}"
    if home_team_ties != '0':
        home_team_record += f"-{home_team_ties}"

    date_str, time_str = convert_datetime_to_natural_format(game["Date & Time"])

    # Game Time
    period = game_data["status"]["period"]
    ordinal = lambda n: "%d%s" % (n, "tsnrhtdd"[((n//10%10!=1)*(n%10<4)*n%10)::4])
    period_string = f"{ordinal(period)} Quarter"
    game_time = f"**Game Time**: {game_data['status']['displayClock']} left in the {period_string}"

    # Last Updated
    current_time = datetime.now().strftime('%-I:%M%p ET')
    last_updated = f"**Last Updated**: {current_time}"

    content = f"""##### {game['Away Team']} ({away_team_record}) at {game['Home Team']} ({home_team_record})

-----

- Kickoff: {time_str}
- Location: {game['Stadium']}
- [ESPN Gamecast]({game['Gamecast Link']})
- Game Time: {game_time}
- Last Updated: {last_updated}

| Team | 1Q | 2Q | 3Q | 4Q | Total |
|---|---|---|---|---|---|
| **{game['Home Team']}** | {game_data['home_team_linescores'][0]} | {game_data['home_team_linescores'][1]} | {game_data['home_team_linescores'][2]} | {game_data['home_team_linescores'][3]} | {game_data['home_team_score']} |
| **{game['Away Team']}** | {game_data['away_team_linescores'][0]} | {game_data['away_team_linescores'][1]} | {game_data['away_team_linescores'][2]} | {game_data['away_team_linescores'][3]} | {game_data['away_team_score']} |

-----

I am a bot. Post your feedback to /s/ModBot"""
    
    # Extract the game status
    game_status = game_data_from_api["status"]["type"]["name"]
    if game["Status"] != game_status:
        # Update the local CSV with the new status
        update_schedule_with_status(game["Gamecast Link"], game_status)
        # Sync the updated CSV to the Gist
        sync_csv_to_gist()

    # If the game is complete, append the additional data
    if game_status == "STATUS_FINAL" and "Game Stats" not in game["content"]:
        # Fetch additional data from the new API endpoint
        matchup_data = fetch_matchup_data(game["Gamecast Link"].split("gameId=")[-1])
        # Extract and format the game stats and leaders
        game_stats_content, game_leaders_content = extract_and_format_additional_data(matchup_data)
        # Append this data to the main content
        content += f"\n\n{game_stats_content}\n\n{game_leaders_content}"

    # Use the Squabblr API to update the game thread content
    update_url = f"https://squabblr.co/api/posts/{game['Squabblr Hash ID']}"
    headers = {
        'authorization': 'Bearer ' + SQUABBLES_TOKEN
    }
    payload = {
        "community_name": "NFL",
        "content": content
    }

    try:
        resp = requests.patch(update_url, data=payload, headers=headers)
        resp.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.RequestException as e:
        print(f"Failed to update game thread for {game['Away Team']} at {game['Home Team']}. Error: {e}")

def main():
    schedule = fetch_schedule_from_gist()
    games_to_update = filter_games_for_update(schedule)
    scoreboard_data = fetch_scoreboard_data()

    for game in games_to_update:
        game_id_from_csv = game["Gamecast Link"].rsplit("/", 1)[-1]
        
        # Log the game ID from the CSV
        print(f"Searching for game ID {game_id_from_csv} from CSV for game: {game['Away Team']} at {game['Home Team']}")
        
        game_data = None
        for event in scoreboard_data["events"]:
            # Log the game ID from the API
            print(f"Checking against game ID {event['id']} from API")
            
            if str(event['id']) == game_id_from_csv:
                game_data = event
                print(f"Match found for game ID {game_id_from_csv}.")
                break

        if not game_data:
            print(f"Could not find data for game: {game['Away Team']} at {game['Home Team']}")
            continue

        # Update the game thread
        if update_game_thread(game, game_data):
            print(f"Successfully updated game thread for: {game['Away Team']} at {game['Home Team']}")
        else:
            print(f"Failed to update game thread for: {game['Away Team']} at {game['Home Team']}")

        # Sleep to avoid hitting rate limits
        time.sleep(30)

if __name__ == "__main__":
    main()
