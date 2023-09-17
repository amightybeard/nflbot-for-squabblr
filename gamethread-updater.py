import os
import requests
import pandas as pd
import time
from datetime import datetime
import pytz
from textwrap import dedent
import logging

# Constants
SQUABBLR_TOKEN = os.environ.get('SQUABBLES_TOKEN')
GITHUB_TOKEN = os.environ.get('NFLBOT_WRITE_TO_GIST')
GIST_ID_SCHEDULES = os.environ.get('NFLBOT_SCHEDULES_GIST')
GIST_FILENAME_SCHEDULES = 'nfl-schedule.csv'
GIST_URL_SCHEDULES = f"https://gist.githubusercontent.com/amightybeard/{GIST_ID_SCHEDULES}/raw/{GIST_FILENAME_SCHEDULES}"
GIST_ID_STANDINGS = os.environ.get('NFLBOT_STANDINGS_GIST')
GIST_FILENAME_STANDINGS = 'nfl-standings.csv'
GIST_URL_STANDINGS = f"https://gist.githubusercontent.com/amightybeard/{GIST_ID_STANDINGS}/raw/{GIST_FILENAME_STANDINGS}"

def ordinal(number):
    """Return the ordinal representation of a number."""
    if 10 <= number % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th')
    return f"{number}{suffix}"

def format_kickoff_datetime(dt_str):
    """Format the datetime string to the desired string representation."""
    utc = pytz.utc
    eastern = pytz.timezone('US/Eastern')
    
    # Parse the date string and set it to UTC
    dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S%z')
    
    # Convert the datetime to Eastern Time
    dt_eastern = dt.astimezone(eastern)
    
    date_part = f"{dt_eastern.strftime('%B')} {ordinal(dt_eastern.day)}, {dt_eastern.year}"
    time_part = dt_eastern.strftime('%I:%M%p ET')
    
    return f"{date_part} at {time_part}"

def get_team_record(team, standings_df):
    record = standings_df[standings_df['Team'] == team].iloc[0]
    wins = record['Wins']
    losses = record['Losses']
    ties = record['Ties']
    if ties == 0:
        return f"{wins}-{losses}"
    return f"{wins}-{losses}-{ties}"

def update_gist_file(gist_id, filename, content, token):
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    data = {
        'files': {
            filename: {
                'content': content
            }
        }
    }
    response = requests.patch(f'https://api.github.com/gists/{gist_id}', headers=headers, json=data)
    response.raise_for_status()  # Raise an exception for HTTP errors

# New and updated functions ...

def fetch_active_games(df):
    return df[df['Status'] == 'STATUS_IN_PROGRESS']

def fetch_game_data_from_espn(gamecast_link):
    game_id = gamecast_link.split('/')[-1]
    response = requests.get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard")
    data = response.json()
    
    for event in data['events']:
        if event['id'] == game_id:
            return event
    return None

def construct_post_content(game, standings_df, event_data):
    away_team = game['Away Team']
    home_team = game['Home Team']
    home_team_short = game['Home Team Short']
    away_team_short = game['Away Team Short']
    kickoff_time = format_kickoff_datetime(game['Date & Time'])
    stadium = game['Stadium']
    gamecast_link = game['Gamecast Link']

    home_team_record = get_team_record(home_team, standings_df)
    away_team_record = get_team_record(away_team, standings_df)

    # Extracting data from ESPN API
    displayClock = event_data['competitions'][0]['status']['displayClock']
    period = ordinal(event_data['competitions'][0]['status']['period'])
    current_time = datetime.now(pytz.utc).astimezone(pytz.timezone('US/Eastern')).strftime('%I:%M%p ET')

    # Extracting scores and linescores
    for competitor in event_data['competitions'][0]['competitors']:
        if competitor['homeAway'] == 'home':
            home_score = competitor['score']
            home_linescores = {}
            for index, item in enumerate(competitor['linescores']):
                home_linescores[index + 1] = item['value']

        else:
            away_score = competitor['score']
            away_linescores = {}
            for index, item in enumerate(competitor['linescores']):
                away_linescores[index + 1] = item['value']


    content = dedent(f"""
    #### {away_team} ({away_team_record}) vs. {home_team} ({home_team_record})
    - **Kickoff**: {kickoff_time}
    - **Location**: {stadium}
    - [ESPN Gamecast]({gamecast_link})
    - Game Time: {displayClock} left in the {period} Quarter.
    - Last Update: {current_time}

    ##### Join The Live Chat! https://squabblr.co/s/nfl/chat

    -----

    | Team | 1Q | 2Q | 3Q | 4Q | OT | Total |
    |---|---|---|---|---|---|---|
    | **{home_team_short}** | {home_linescores.get(1, '0')} | {home_linescores.get(2, '0')} | {home_linescores.get(3, '0')} | {home_linescores.get(4, '0')} | {home_linescores.get(5, '0')} | {home_score} |
    | **{away_team_short}** | {away_linescores.get(1, '0')} | {away_linescores.get(2, '0')} | {away_linescores.get(3, '0')} | {away_linescores.get(4, '0')} | {away_linescores.get(5, '0')} | {away_score} |

    *Scoreboard will be updated every 5-minutes.*
    
    -----

    I am a bot. Post your feedback to /s/ModBot
    """)
    return content

def update_gamethread_on_squabblr(content, hash_id):
    headers = {
        'Authorization': f"Bearer {SQUABBLR_TOKEN}",
        'Content-Type': 'application/json'
    }
    data = {
        'content': content
    }
    response = requests.patch(f"https://squabblr.co/api/posts/{hash_id}", headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def main():
    logging.info("Starting gamethread updater...")

    # Load the CSV data
    logging.info("Loading schedule and standings data...")
    schedule_df = pd.read_csv(GIST_URL_SCHEDULES)
    standings_df = pd.read_csv(GIST_URL_STANDINGS)
    logging.info("Data loaded successfully.")
    logging.info("Checking for games in progress...")

    active_games = fetch_active_games(schedule_df)
    # Check if there are no active games and log a message
    if active_games.empty:
        logging.info("No games are in progress.")
        logging.info("Gamethread updater finished.")
        return

    logging.info("Checking for games in progress...")
    
    for _, game in active_games.iterrows():
        logging.info(f"Fetching game data for {game['Away Team']} vs. {game['Home Team']} from ESPN...")
        event_data = fetch_game_data_from_espn(game['Gamecast Link'])

        if not event_data:
            logging.warning(f"Failed to fetch game data for {game['Away Team']} vs. {game['Home Team']} from ESPN.")
            continue

        content = construct_post_content(game, standings_df, event_data)
        
        logging.info(f"Updating gamethread for game: {game['Away Team']} vs {game['Home Team']}")
        update_gamethread_on_squabblr(content, game['Squabblr Hash ID'])
        logging.info(f"Successfully updated gamethread for game: {game['Away Team']} vs {game['Home Team']}")

        # Update the CSV if the game's status has changed to "STATUS_FINAL"
        if event_data['competitions'][0]['status']['type']['name'] == 'STATUS_FINAL':
            logging.info(f"Updating game status to 'STATUS_FINAL' for {game['Away Team']} vs. {game['Home Team']} in the CSV...")
            game['Status'] = 'STATUS_FINAL'
            update_gist(GIST_FILENAME_SCHEDULES, schedule_df.to_csv(index=False))
            logging.info(f"Game status updated to 'STATUS_FINAL' for {game['Away Team']} vs. {game['Home Team']}.")

        time.sleep(5)  # Delay to prevent rate-limiting and overlapping operations

    logging.info("Gamethread updater finished.")
    return

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
