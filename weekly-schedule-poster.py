import requests
import csv
import os
from datetime import datetime, timedelta

SQUABBLES_TOKEN = os.environ.get('SQUABBLES_TOKEN')
GIST_ID = "ef63fd2037741d41c2209b46da0779b8"

def fetch_schedule_from_gist():
    """Fetch the NFL schedule from the gist."""
    print("Fetching schedule from gist...")
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
    """Convert the provided date time string into a more natural format."""
    dt_obj = datetime.strptime(dt_string, '%Y-%m-%dT%H:%MZ')
    
    # Adjust for Eastern Time (ET is UTC-4, but this doesn't account for daylight saving)
    dt_obj = dt_obj - timedelta(hours=4)
    
    # Extract date without year and time without leading zero for the hour
    date_format = dt_obj.strftime('%m/%d')
    time_format = dt_obj.strftime('%I:%M%p ET').lstrip('0')

    return date_format, time_format

def get_current_week(schedule):
    """Determine the current week of the NFL season."""
    print("Determining the current week...")
    today = datetime.today().date()
    for game in schedule:
        game_date = datetime.strptime(game['Date & Time'].split('T')[0], '%Y-%m-%d').date()
        if game_date >= today:
            return game['Week']

def fetch_games_for_week(week):
    schedule = fetch_schedule_from_gist()
    games = [game for game in schedule if game['Week'] == week]
    return games

def construct_weekly_schedule_post(games, week):
    """Construct and post the weekly schedule."""
    print("Constructing weekly schedule post...")
    table_header = "| Date & Time | Match Up | Live Thread |\n| ----- | ----- | ----- |\n"
    table_content = ""
        
    for game in games:
        game_date_str, game_time_str = convert_datetime_to_natural_format(game['Date & Time'])

        # Define away_team and home_team
        away_team = game['Away Team']
        home_team = game['Home Team']
        
        # Fetch the win-loss records for away and home teams
        away_team_wins, away_team_losses, away_team_ties = fetch_team_record(game['Away Team'])
        home_team_wins, home_team_losses, home_team_ties = fetch_team_record(game['Home Team'])

        # Format the win-loss-tie records for away and home teams
        away_team_record = f"{away_team_wins}-{away_team_losses}"
        if away_team_ties != '0':
            away_team_record += f"-{away_team_ties}"
    
        home_team_record = f"{home_team_wins}-{home_team_losses}"
        if home_team_ties != '0':
            home_team_record += f"-{home_team_ties}"
            
        matchup = f"{game['Away Team']} ({away_team_record}) at {game['Home Team']} ({home_team_record})"
        table_content += f"| {game_date_str} at {game_time_str} | {matchup} | Coming Soon |\n"
    
    start_date_str, _ = convert_datetime_to_natural_format(games[0]['Date & Time'])
    end_date_str, _ = convert_datetime_to_natural_format(games[-1]['Date & Time'])
    
    title = f"NFL 2023 Season - {week} Schedule - {start_date_str}-{end_date_str.split('/')[-1]}"
    content = f"Here is this week's schedule. **What games are you planning on watching?**\n\n{table_header}{table_content}\n-----\n\nI am a bot. Post your feedback on /s/ModBot"

    post_to_squabblr(title, content)

def post_to_squabblr(title, content):
    """Post the content to Squabblr."""
    print(f"Posting to Squabblr with title: {title}")
    headers = {
        'authorization': 'Bearer ' + SQUABBLES_TOKEN
    }
    resp = requests.post('https://squabblr.co/api/new-post', data={
        "community_name": "NFL",
        "title": title,
        "content": content
    }, headers=headers)

    print(f"Post response: {resp.json()}")

def main():
    schedule = fetch_schedule_from_gist()
    week = get_current_week(schedule)
    print(f"Current week: {week}")

    games = [game for game in schedule if game['Week'] == week]
    construct_weekly_schedule_post(games, week)

if __name__ == "__main__":
    main()
