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
    """Fetch the win-loss record of a team from the standings CSV."""
    with open('csv/nfl_standings.csv', 'r', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            print(row)  # This will print each row
            if row['Team'] == team_name:
                wins = row['Wins']
                losses = row['Losses']
                ties = row['Ties']
                
                # Check if the team has any ties
                if int(ties) > 0:
                    return f"{wins}-{losses}-{ties}"
                else:
                    return f"{wins}-{losses}"
    return "0-0"  # default if not found
    
from datetime import datetime, timedelta

def convert_datetime_to_natural_format(dt_string):
    # Convert the provided string into a datetime object
    dt_obj = datetime.strptime(dt_string, '%Y-%m-%dT%H:%MZ')
    
    # Adjust for Eastern Time (ET is UTC-4, but this doesn't account for daylight saving)
    dt_obj = dt_obj - timedelta(hours=4)
    
    # Extract date, time, and am/pm information
    date_format = dt_obj.strftime('%m/%d/%Y')
    time_format = dt_obj.strftime('%I:%M%p ET').lower()

    return date_format, time_format
    
def post_game_thread(away_team, home_team, week, date_time, stadium, gamecast_link):
    date_str, time_str = convert_datetime_to_natural_format(date_time)
    
    away_team_record = fetch_team_record(away_team)
    home_team_record = fetch_team_record(home_team)
    
    headers = {
        'authorization': 'Bearer ' + SQUABBLES_TOKEN
    }
    title = f"[Game Thread] {away_team} at {home_team} - Week {week} - {date_str} at {time_str}"
    content = f"""## {away_team} ({away_team_record[0]}-{away_team_record[1]}) at {home_team} ({home_team_record[0]}-{home_team_record[1]})

---------

- Kickoff: {time_str}
- Location: {stadium}
- [ESPN Gamecast]({gamecast_link})

| Team | 1Q | 2Q | 3Q | 4Q | Final |
|---|---|---|---|---|---|
| **{home_team}** | 0 | 0 | 0 | 0 | 0 |
| **{away_team}** | 0 | 0 | 0 | 0 | 0 |"""

    resp = requests.post('https://squabblr.co/api/new-post', data={
        "community_id": 22,
        "community_name": "NFL",
        "title": title,
        "content": content
    }, headers=headers)

    return resp.json()

def main():
    schedule = fetch_schedule_from_gist()

    # Get the first game of the season (Week 1)
    first_game = next(game for game in schedule if game['Week'] == 'Week 1')

    post_game_thread(
        away_team=first_game['Away Team'],
        home_team=first_game['Home Team'],
        week=first_game['Week'],
        date_time=first_game['Date & Time'],
        stadium=first_game['Stadium'],
        gamecast_link=first_game['Gamecast Link']
    )

if __name__ == "__main__":
    main()
