
import requests
import csv

def fetch_nfl_schedule_for_week(week_number):
    # Define the API URL
    url = f"https://site.web.api.espn.com/apis/v2/scoreboard/header?sport=football&league=nfl&region=us&lang=en&contentorigin=espn&buyWindow=1m&showAirings=buy%2Clive%2Creplay&showZipLookup=true&tz=America%2FNew_York"
    
    # Fetch the data
    response = requests.get(url)
    data = response.json()
    events = data['sports'][0]['leagues'][0]['events']
    
    # List to hold the game details
    games = []
    
    for event in events:
        # Extract necessary information
        game_details = {
            'Week': event['weekText'],
            'Date & Time': event['fullStatus']['type']['detail'],
            'Stadium': event['location'],
            'Gamecast Link': event['link']
        }
        
        for competitor in event['competitors']:
            if competitor['homeAway'] == 'home':
                game_details['Home Team'] = competitor['displayName']
            else:
                game_details['Away Team'] = competitor['displayName']
        
        games.append(game_details)
    
    return games

def main():
    # Loop through all weeks (1 to 18) and fetch the schedule
    all_games = []
    for week in range(1, 19):
        all_games.extend(fetch_nfl_schedule_for_week(week))
    
    # Write the fetched data to csv/nfl-schedule.csv
    with open('csv/nfl-schedule.csv', 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['Week', 'Date & Time', 'Stadium', 'Home Team', 'Away Team', 'Gamecast Link'])
        writer.writeheader()
        for game in all_games:
            writer.writerow(game)

if __name__ == "__main__":
    main()
