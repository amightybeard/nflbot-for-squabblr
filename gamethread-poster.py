import os
import requests
import logging
from datetime import datetime, timedelta
from io import StringIO
import pandas as pd
import pytz

# 1. Initialization

# Setting up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants
SQUABBLR_TOKEN = os.environ.get('SQUABBLES_TOKEN')
GITHUB_TOKEN = os.environ.get('NFLBOT_WRITE_TO_GIST')
GIST_ID_SCHEDULES = os.environ.get('NFLBOT_SCHEDULES_GIST')
GIST_FILENAME_SCHEDULES = 'nfl-schedule.csv'
GIST_URL_SCHEDULES = f"https://gist.githubusercontent.com/amightybeard/{GIST_ID_SCHEDULES}/raw/{GIST_FILENAME_SCHEDULES}"
GIST_ID_STANDINGS = os.environ.get('NFLBOT_STANDINGS_GIST')
GIST_FILENAME_STANDINGS = 'nfl-standings.csv'
GIST_URL_STANDINGS = f"https://gist.githubusercontent.com/amightybeard/{GIST_ID_STANDINGS}/raw/{GIST_FILENAME_STANDINGS}"

# 2. Function Definitions

def fetch_csv_from_gist(gist_url):
    response = requests.get(gist_url)
    response.raise_for_status()  # Raise an exception for HTTP errors
    return pd.read_csv(StringIO(response.text))

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
    dt = datetime.strptime(dt_str, '%Y-%m-%dT%H:%M%SZ').replace(tzinfo=utc)
    
    # Convert the datetime to Eastern Time
    dt_eastern = dt.astimezone(eastern)
    
    date_part = f"{dt_eastern.strftime('%B')} {ordinal(dt_eastern.day)}, {dt_eastern.year}"
    time_part = dt_eastern.strftime('%I:%M%p ET')
    
    return f"{date_part} at {time_part}"

def filter_upcoming_games(df, hours=3):
    utc = pytz.utc
    now = datetime.now(utc)  # Make this timezone-aware in UTC
    end_time = now + timedelta(hours=hours)
    
    df['Date & Time'] = pd.to_datetime(df['Date & Time'])
    upcoming_games = df[(df['Date & Time'] >= now) & (df['Date & Time'] <= end_time) & (df['Status'] == 'STATUS_SCHEDULED')]
    
    return upcoming_games

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

def construct_post_content(row, standings_df):
    home_team = row['Home Team']
    away_team = row['Away Team']
    week = row['Week']
    date_str = row['Date & Time'].strftime('%Y-%m-%d')
    time_str = row['Date & Time'].strftime('%H:%M %p')
    stadium = row['Stadium']
    gamecast_link = row['Gamecast Link']
    home_team_short = row['Home Team Short']
    away_team_short = row['Away Team Short']

    kickoff_time = format_kickoff_datetime(row['Date & Time'])
    
    home_team_record = get_team_record(home_team, standings_df)
    away_team_record = get_team_record(away_team, standings_df)
    
    title = f"[Gamethread] {home_team} at {away_team} - {week}"
    content = f"""
#### {away_team} ({away_team_record}) vs. {home_team} ({home_team_record})
- **Kickoff**: {kickoff_time}
- **Location**: {stadium}
- [Join The Live Chat!](https://squabblr.co/s/nfl/chat)
- [ESPN Gamecast]({gamecast_link})
-----
| Team | 1Q | 2Q | 3Q | 4Q | OT | Total |
|---|---|---|---|---|---|---|
| **{home_team_short}** | 0 | 0 | 0 | 0 | 0 | 0 |
| **{away_team_short}** | 0 | 0 | 0 | 0 | 0 | 0 |
-----
I am a bot. Post your feedback to /s/ModBot
"""
    return title, content

def post_to_squabblr(title, content):
    logging.info(f"Posting article '{title}' to Squabblr.co...")
    headers = {
        'authorization': 'Bearer ' + SQUABBLR_TOKEN
    }
    response = requests.post('https://squabblr.co/api/new-post', data={
        "community_name": "test",
        "title": title,
        "content": content
    }, headers=headers)
    logging.info(f"Article '{title}' posted successfully.")
    return response.json()

# 3. Main Logic

# Load the CSV data from uploaded files
schedule_df = fetch_csv_from_gist(GIST_URL_SCHEDULES)
standings_df = fetch_csv_from_gist(GIST_URL_STANDINGS)
logging.info("Data loaded successfully.")

upcoming_games = filter_upcoming_games(schedule_df)
if not upcoming_games.empty:
    for _, game in upcoming_games.iterrows():
        title, content = construct_post_content(game, standings_df)
        
        # Post to Squabblr and get the hash_id
        response_data = post_to_squabblr(title, content)
        hash_id = response_data['data'][0]['hash_id']
        
        # Update the CSV
        schedule_df.loc[game.name, 'Squabblr Hash ID'] = hash_id
        schedule_df.loc[game.name, 'Status'] = 'STATUS_IN_PROGRESS'
        logging.info(f"Updated schedule CSV for game: {title}.")
        
        # Delay for 15 seconds before processing the next game
        time.sleep(15)

# 4. Finalization

logging.info("nfl-schedule.csv would be updated on GitHub Gist at this step.")
csv_content = schedule_df.to_csv(index=False)
update_gist_file(GIST_ID_SCHEDULES, GIST_FILENAME_SCHEDULES, csv_content, GITHUB_TOKEN)
logging.info("Script completed successfully.")
