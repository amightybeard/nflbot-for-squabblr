import os
import requests
import logging
import time
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

def find_next_game_week(df):
    """Find the week of the next upcoming game."""
    now = datetime.now(pytz.timezone('US/Eastern'))
    next_game = df[df['Date & Time'] > now].iloc[0]
    return next_game['Week']

def filter_games_by_week(df, week):
    """Filter the games based on the week."""
    return df[df['Week'] == week]

def post_to_squabblr(title, content):
    logging.info(f"Posting article '{title}' to Squabblr.co...")
    headers = {
        'authorization': 'Bearer ' + SQUABBLR_TOKEN
    }
    response = requests.post('https://squabblr.co/api/new-post', data={
        "community_name": "NFL",
        "title": title,
        "content": content
    }, headers=headers)
    logging.info(f"Article '{title}' posted successfully.")
    return response.json()

# Load the CSV data
schedule_df = fetch_csv_from_gist(GIST_URL_SCHEDULES)
standings_df = fetch_csv_from_gist(GIST_URL_STANDINGS)
logging.info("Data loaded successfully.")

# 2. Processing

# Find the week of the next game
next_week = find_next_game_week(schedule_df)

# Filter the games of that week
games_of_the_week = filter_games_by_week(schedule_df, next_week)

# Construct the post content
title = f"{next_week} Schedule - NFL 2023 Season"
content_lines = [
    f"Here's what's on tap for {next_week} in the NFL 2023 Season!",
    "",
    "| Date & Time | Match Up |",
    "| --- | --- |"
]

for _, game in games_of_the_week.iterrows():
    home_team = game['Home Team']
    away_team = game['Away Team']
    kickoff_time = format_kickoff_datetime(game['Date & Time'])
    home_team_record = get_team_record(home_team, standings_df)
    away_team_record = get_team_record(away_team, standings_df)
    content_lines.append(f"| {kickoff_time} | {away_team} ({away_team_record}) vs. {home_team} ({home_team_record}) |")

content_lines.extend([
    "",
    "Join us in the live chat for every game! https://squabblr.co/s/nfl/chat",
    "",
    "----",
    "I am a bot. Post your feedback on /s/ModBot"
])
content = "\n".join(content_lines)
response_data = post_to_squabblr(title, content)

logging.info("Script completed successfully.")
