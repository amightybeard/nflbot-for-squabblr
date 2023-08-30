import requests
import csv
import os
from datetime import datetime

SQUABBLES_TOKEN = os.environ.get('SQUABBLES_TOKEN')
GIST_ID = "ef63fd2037741d41c2209b46da0779b8"

def fetch_schedule_from_gist():
    """Fetch the NFL schedule from the gist."""
    gist_url = f"https://api.github.com/gists/{GIST_ID}"
    response = requests.get(gist_url)
    raw_csv = response.json()['files']['nfl-schedule.csv']['content']
    reader = csv.DictReader(raw_csv.splitlines())
    return list(reader)

def post_game_thread(away_team, home_team, week, date_time, stadium, gamecast_link):
    headers = {
        'authorization': 'Bearer ' + SQUABBLES_TOKEN
    }
    title = f"[Game Thread] {away_team} at {home_team} - {week} - {date_time}"
    content = f"""## {away_team} at {home_team}

---------

- Kickoff: {date_time}
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
