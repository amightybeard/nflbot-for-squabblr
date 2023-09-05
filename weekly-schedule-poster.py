import requests
import csv
import os
from datetime import datetime, timedelta

SQUABBLES_TOKEN = os.environ.get('SQUABBLES_TOKEN')
GIST_ID = "ef63fd2037741d41c2209b46da0779b8"

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
    time_format = dt_obj.strftime('%I:%M%p ET')

    return date_format, time_format
    
def post_game_thread(away_team, home_team, week, date_time, stadium, gamecast_link):
    headers = {
        'authorization': 'Bearer ' + SQUABBLES_TOKEN
    }

    # Fetch the win-loss records
    away_team_wins, away_team_losses, away_team_ties = fetch_team_record(away_team)
    home_team_wins, home_team_losses, home_team_ties = fetch_team_record(home_team)

    # Format the win-loss-tie records
    away_team_record = f"{away_team_wins}-{away_team_losses}"
    if away_team_ties != '0':
        away_team_record += f"-{away_team_ties}"
    
    home_team_record = f"{home_team_wins}-{home_team_losses}"
    if home_team_ties != '0':
        home_team_record += f"-{home_team_ties}"

    date_str, time_str = convert_datetime_to_natural_format(date_time)

    title = f"[GameThread] {away_team} at {home_team} - {week} - {date_str} at {time_str}"

    content = f"""##### {away_team} ({away_team_record}) at {home_team} ({home_team_record})

-----

- Kickoff: {time_str}
- Location: {stadium}
- [ESPN Gamecast]({gamecast_link})

| Team | 1Q | 2Q | 3Q | 4Q | Final |
|---|---|---|---|---|---|
| **{home_team}** | 0 | 0 | 0 | 0 | 0 |
| **{away_team}** | 0 | 0 | 0 | 0 | 0 |

-----

I am a bot. Post your feedback to /s/ModBot"""

    resp = requests.post('https://squabblr.co/api/new-post', data={
        "community_name": "NFL",
        "title": title,
        "content": content
    }, headers=headers)

    return resp.json()

def construct_weekly_schedule_post(games, week):
    # Get the start and end dates for the week's games
    start_date = datetime.strptime(games[0]['Date & Time'].split(' ')[0], '%m/%d').date()
    end_date = datetime.strptime(games[-1]['Date & Time'].split(' ')[0], '%m/%d').date()

    title = f"NFL 2023 Season - {week} Schedule - {start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}"
    
    content = "Here is this week's schedule. What games are you planning on watching?\n\n"
    content += "| Date & Time | Match Up | Live Thread | Gamecast |\n"
    content += "| ----- | ----- | ----- | ----- |\n"
    
    for game in games:
        game_date = datetime.strptime(game['Date & Time'].split(' ')[0], '%m/%d').date()
        game_time = game['Date & Time'].split(' ')[2] + " " + game['Date & Time'].split(' ')[3]
        content += f"| {game_date.strftime('%m/%d')} at {game_time} | {game['Away Team']} at {game['Home Team']} | Coming Soon | [Gamecast]({game['Gamecast Link']}) |\n"

    content += "\n-----\n\nI am a bot. Post your feedback on /s/ModBot"
    
    post_to_squabblr(title, content)

def main():
    # Assuming you'd like to run this weekly schedule creation as part of the main function
    week = get_current_week()
    games = fetch_games_for_week(week)
    construct_weekly_schedule_post(games, week)

if __name__ == "__main__":
    main()
