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
    
    # Assuming games are scheduled in the future, so we'll only post threads for games that are today or upcoming.
    today = datetime.today().date()

    for game in schedule:
        game_date = datetime.strptime(game['Date & Time'], '%a, %B %dth at %I:%M %p %Z').date()
        if game_date >= today:
            post_game_thread(
                away_team=game['Away Team'],
                home_team=game['Home Team'],
                week=game['Week'],
                date_time=game['Date & Time'],
                stadium=game['Stadium'],
                gamecast_link=game['Gamecast Link']
            )

if __name__ == "__main__":
    main()
