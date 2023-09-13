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

    title = f"[GameThread] {away_team} at {home_team} - {week}"

    content = f"""##### {away_team} ({away_team_record}) vs {home_team} ({home_team_record})

-----

- Kickoff: {date_str} at {time_str}
- Location: {stadium}
- [ESPN Gamecast]({gamecast_link})
- [Join The Live Chat!](https://squabblr.co/s/nfl/chat)

| Team | 1Q | 2Q | 3Q | 4Q | Total |
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
    
    resp_data = resp.json()

    # Check for HTTP success
    if resp.status_code in [200,201]:
        hash_id = resp.json().get("hash_id")
        if hash_id:
            return hash_id, title, content
        if 'data' in resp_data and len(resp_data['data']) > 0:
            return resp_data['data'][0]
        else:
            print(f"post_game_thread = Unexpected response structure after posting game thread for {away_team} at {home_team}. Response: {resp.text}")
            return None
    else:
        print(f"post_game_thread = Posted game thread for {away_team} at {home_team}. Hash ID: {resp_data}")
        return None
        
def update_schedule_with_hash_id(schedule, game, hash_id):
    print(f"Attempting to update schedule for game: {game['Away Team']} at {game['Home Team']} with hash_id: {hash_id}")
    
    game_found = False
    for row in schedule:
        if row['Gamecast Link'] == game['Gamecast Link']:
            row['Squabblr Hash ID'] = hash_id
            print(f"Updated hash_id for game: {row['Away Team']} at {row['Home Team']} with hash_id: {hash_id}")
            game_found = True
            break

    if not game_found:
        print(f"No matching game found for {game['Away Team']} at {game['Home Team']} in the schedule. Unable to update hash_id.")
        return

    try:
        # Save the updated schedule back to CSV
        with open('nfl-schedule.csv', 'w', newline='') as csvfile:
            fieldnames = ['Week', 'Date & Time', 'Stadium', 'Home Team', 'Away Team', 'Home Team Short', 'Away Team Short', 'Gamecast Link', 'Squabblr Hash ID', 'Status']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in schedule:
                writer.writerow(row)
        print(f"Successfully wrote to the CSV for game: {game['Away Team']} at {game['Home Team']}")
    except Exception as e:
        print(f"Error encountered while writing to the CSV: {str(e)}")

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
        print(f"Failed to update Gist. Status code: {response.status_code}. Response: {response.text}")
    print(f"Response from GitHub API: {response.text}")
    return response.status_code

def starts_within_next_4_hours(date_time_str):
    """Check if a game starts within the next 4 hours."""
    game_time = datetime.strptime(date_time_str, '%Y-%m-%dT%H:%MZ')
    current_time = datetime.utcnow()
    time_difference = game_time - current_time
    return 0 <= time_difference.total_seconds() <= 4 * 60 * 60  # 4 hours in seconds

def main():
    schedule = fetch_schedule_from_gist()
    
    # Assuming games are scheduled in the future, so we'll only post threads for games that are today or upcoming.
    today = datetime.today().date()

    for game in schedule:
        print(f"Processing game: {game['Away Team']} at {game['Home Team']}")
        game_date = datetime.strptime(game["Date & Time"], '%Y-%m-%dT%H:%MZ').date()
        if starts_within_next_4_hours(game["Date & Time"]):
            try:
                headers = {
                    'authorization': 'Bearer ' + SQUABBLES_TOKEN
                }
                away_team = game['Away Team']
                home_team = game['Home Team']
                week = game['Week']
                date_time = game['Date & Time']
                stadium = game['Stadium']
                gamecast_link = game['Gamecast Link']
                
                hash_id, title, content = post_game_thread(away_team, home_team, week, date_time, stadium, gamecast_link)
                
                resp = requests.post('https://squabblr.co/api/new-post', data={
                    "community_name": "NFL",
                    "title": title,
                    "content": content
                }, headers=headers)
            
                # Check if response exists and contains expected keys
                if resp and resp.status_code in [200, 201]:
                    hash_id = resp_data['data'][0]['hash_id']
                    
                    if not hash_id and 'data' in resp_data and len(resp_data['data']) > 0 and 'hash_id' in resp_data['data'][0]:
                        hash_id = resp_data['data'][0]['hash_id']
                        
                    if hash_id:
                        print(f"main = Successfully posted game thread for {away_team} at {home_team}. Hash ID: {hash_id}")
                        return hash_id
                    else:
                        print(f"main = Unexpected response structure after posting game thread for {away_team} at {home_team}. Response: {resp.text}")
                        return None
                    
                    print(f"Hash ID to be written to CSV: {hash_id}")
                    print("Updating local CSV with hash_id...")
                    update_schedule_with_hash_id(schedule, game, hash_id)
                    sync_csv_to_gist()
                    print("Local CSV updated.")
                else:
                    print(f"main = Failed to post game thread for {away_team} at {home_team}. Response: {resp.text}")
                    return None
            except requests.RequestException as e:
                print(f"Error while posting game thread for {away_team} at {home_team}. Error: {e}")
                
            # Sleep for 30 seconds between operations to ensure sequential execution
            print(f"Starting delay at {datetime.now().time()}")
            time.sleep(30)
            print(f"Ending delay at {datetime.now().time()}")

            
if __name__ == "__main__":
    main()
