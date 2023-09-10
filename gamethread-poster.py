import requests
import csv
import os
from datetime import datetime, timedelta

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

def update_schedule_with_hash_id(schedule, game, hash_id):
    for row in schedule:
        if row['Gamecast Link'] == game['Gamecast Link']:
            row['Squabblr Hash ID'] = hash_id
            break

    # Save the updated schedule back to CSV
    with open('nfl-schedule.csv', 'w', newline='') as csvfile:
        fieldnames = ['Week', 'Date & Time', 'Stadium', 'Home Team', 'Away Team', 'Gamecast Link', 'Squabblr Hash ID']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in schedule:
            writer.writerow(row)

def sync_csv_to_gist():
    """Sync the updated local CSV to the Gist."""
    gist_url = f"https://api.github.com/gists/{GIST_ID}"
    
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Content-Type': 'application/json',
    }
    
    with open('nfl-schedule.csv', 'r') as csvfile:
        csv_content = csvfile.read()
    
    data = {
        "files": {
            "nfl-schedule.csv": {
                "content": csv_content
            }
        }
    }
    
    response = requests.patch(gist_url, headers=headers, json=data)
    if response.status_code != 200:
        print(f"Failed to update Gist. Status code: {response.status_code}")

def main():
    schedule = fetch_schedule_from_gist()
    
    # Assuming games are scheduled in the future, so we'll only post threads for games that are today or upcoming.
    today = datetime.today().date()

    for game in schedule:
        game_date = datetime.strptime(game["Date & Time"], '%Y-%m-%dT%H:%MZ').date()
        if game_date == today:
            post_game_thread(
                away_team=game["Away Team"],
                home_team=game["Home Team"],
                week=game["Week"],
                date_time=game["Date & Time"],
                stadium=game["Stadium"],
                gamecast_link=game["Gamecast Link"]
            )
            response = post_game_thread(
                away_team=game["Away Team"],
                home_team=game["Home Team"],
                week=game["Week"],
                date_time=game["Date & Time"],
                stadium=game["Stadium"],
                gamecast_link=game["Gamecast Link"]
            )
            hash_id = response['hash_id']
        
            # Update the local CSV with the hash_id
            update_schedule_with_hash_id(schedule, game, hash_id)
            
            # Sync the updated CSV to the Gist
            sync_csv_to_gist()  # This function will be responsible for updating the Gist with the latest CSV

if __name__ == "__main__":
    main()
