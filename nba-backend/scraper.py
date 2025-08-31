import psycopg2
import cloudscraper
from bs4 import BeautifulSoup, Comment
import time
from datetime import datetime
import re
from tqdm import tqdm
import random
from fake_useragent import UserAgent
from pymongo import MongoClient
from datetime import datetime, date
import string
import pymongo
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGODB_URI"))


db = client["nba_stats"]

teams_collection = db['teams']
players_collection = db['players']
games_collection = db['games']
coaches_collection = db['coaches']

scraper = cloudscraper.create_scraper()

ua = UserAgent()

def get_headers():
    return {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.google.com/',
        'DNT': '1'
    }
# Database connection
def get_db_connection():
    return psycopg2.connect(
        dbname="nba_stats",
        user="nba_admin",
        password="basketball123",
        host="localhost"
    )

# Configure scraping


DELAY = 30  # seconds between requests

# Helper functions
def convert_height(height_str):
    """Convert '6-8' format to meters (2.03)"""
    try:
        feet, inches = map(int, height_str.split('-'))
        return round(feet * 0.3048 + inches * 0.0254, 2)
    except:
        return None

def safe_request(url, retries=5):
    wait_time = 240
    for attempt in range(retries):
        try:
            response = scraper.get(url, headers=get_headers(), timeout=10)
            if response.status_code == 429:
                print(f"429 Too Many Requests. Backing off for {wait_time} seconds...")
                time.sleep(wait_time)
                wait_time *= 2
                continue
            response.raise_for_status()
            return response
        except Exception as e:
            print(f"Request failed: {e}")
            time.sleep(wait_time)
            wait_time *= 2
    print("Max retries reached. Skipping URL.")
    return None
def scrape_teams():
    url = "https://www.basketball-reference.com/teams/"
    response = safe_request(url)
    if not response:
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    teams = []

    #print(soup.select('table#teams_active tbody tr:not(.thead)'))  # Debugging line to see the first 500 characters of the HTML

    # Use the 'teams' table which includes all franchises
    for row in soup.select('table#teams_active tbody tr:not(.thead)'):
        team_name_cell = row.find('th', {'data-stat': 'franch_name'})
        if not team_name_cell:
            continue

        team_link = team_name_cell.find('a')
        team_name = team_name_cell.text.strip()
        abbreviation = team_link['href'].split('/')[2] if team_link else None
        city = ' '.join(team_name.split()[:-1])

        def get_stat(stat_name):
            cell = row.find('td', {'data-stat': stat_name})
            return cell.text.strip() if cell else None

        year_min = get_stat('year_min')
        founded_year = int(year_min.split('-')[0]) if year_min and '-' in year_min else int(year_min) if year_min else None

        teams.append({
            'name': team_name,
            'abbreviation': abbreviation,
            'city': city,
            'founded_year': founded_year,
            'arena': None,  # still not present on this page
            'league': get_stat('lg_id'),
            'year_min': year_min,
            'year_max': get_stat('year_max'),
            'years': get_stat('years'),
            'games': get_stat('g'),
            'wins': get_stat('wins'),
            'losses': get_stat('losses'),
            'win_loss_pct': get_stat('win_loss_pct'),
            'years_playoffs': get_stat('years_playoffs'),
            'years_div_champs': get_stat('years_division_champion'),
            'years_conf_champs': get_stat('years_conference_champion'),
            'years_league_champs': get_stat('years_league_champion'),
        })
    #print(teams)
    return teams



def scrape_players():
    """Scrape all players in Basketball Reference history (~4,000)."""
    base_url = "https://www.basketball-reference.com/players/"
    players = []

    for letter in string.ascii_lowercase:
        url = f"{base_url}{letter}/"
        print(f"Scraping players starting with '{letter.upper()}'...")
        response = safe_request(url)
        if not response:
            continue
        
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'id': 'players'})

        if not table:
            continue

        for row in table.select('tbody tr'):
            # Some rows are headers for decades — skip them
            if 'class' in row.attrs and 'thead' in row.attrs['class']:
                continue
            
            try:
                name_cell = row.find('th', {'data-stat': 'player'})
                if not name_cell or not name_cell.a:
                    continue

                full_name = name_cell.a.text.strip()
                name_parts = full_name.split()
                first_name = ' '.join(name_parts[:-1])
                last_name = name_parts[-1] if name_parts else ''

                birth_date = None
                birth_cell = row.find('td', {'data-stat': 'birth_date'})
                if birth_cell and birth_cell.text.strip():
                    try:
                        birth_date = datetime.strptime(birth_cell.text.strip(), '%Y-%m-%d').date()
                    except ValueError:
                        pass

                players.append({
                    'first_name': first_name,
                    'last_name': last_name,
                    'birth_date': birth_date.isoformat() if birth_date else None,
                    'player_url': "https://www.basketball-reference.com" + name_cell.a['href']
                })
            except Exception as e:
                print(f"Error processing row: {e}")

    print(f"Total players scraped: {len(players)}")
    return players

def scrape_player_details(player):
    """
    Given a player document with 'player_url',
    scrapes every available table & stat from their Basketball Reference page.
    Missing data is stored as None.
    """
    try:
        url = player.get("player_url")
        if not url:
            print(f"No player_url for {player.get('first_name', '')} {player.get('last_name', '')}")
            return None

        response = safe_request(url)
        if not response:
            print(f"Failed to fetch {url}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        details = {
            "full_name": f"{player.get('first_name', '')} {player.get('last_name', '')}".strip(),
            "bio": {},
            "stats": {}
        }

        # === Bio / Metadata extraction ===
        meta = soup.find('div', {'id': 'meta'})
        if meta:
            for p in meta.find_all('p'):
                text = p.get_text(" ", strip=True)
                if ':' in text:
                    key, value = text.split(':', 1)
                    details["bio"][key.strip()] = value.strip()
        else:
            details["bio"] = None

        # === Extract ALL tables dynamically ===
        tables = soup.find_all('table')
        for table in tables:
            table_id = table.get('id', 'unknown_table')
            headers = [th.get_text(strip=True) for th in table.find_all('th')]
            rows_data = []

            for row in table.find_all('tr'):
                if row.get('class') and 'thead' in row.get('class'):
                    continue
                row_values = [cell.get_text(strip=True) or None for cell in row.find_all(['th', 'td'])]
                rows_data.append(row_values)

            details["stats"][table_id] = {
                "headers": headers,
                "rows": rows_data if rows_data else None
            }

        return details

    except Exception as e:
        print(f"Error scraping details for {player.get('first_name', '')} {player.get('last_name', '')}: {e}")
        return None


def update_player_details(player_id, details):
    """Update a single player's details in MongoDB."""
    players_collection.update_one(
        {"_id": player_id},
        {"$set": {"details": details}}
    )


def scrape_all_player_details():
    players = players_collection.find({
        "$or": [
            {"details": {"$exists": False}},
            {"details": None}
        ]
    })
    for player in players:
        try:
            print(f"Scraping details for {player.get('first_name')} {player.get('last_name')}...")
            details = scrape_player_details(player)
            if details:
                players_collection.update_one(
                    {"_id": player["_id"]},
                    {"$set": {"details": details}}
                )
            print(f"Successfully scraped details for {player.get('first_name')} {player.get('last_name')}")
        except Exception as e:
            print(f"Error scraping details for {player.get('first_name')} {player.get('last_name')}: {e}")


def scrape_and_upsert_schedule(start_year=1947, end_year=datetime.now().year):
    """
    Scrape NBA/BAA schedules from start_year to end_year and upsert into MongoDB.
    Handles the BAA prefix for 1947–1949.
    """
    for year in range(start_year, end_year + 1):
        prefix = "BAA" if year < 1950 else "NBA"
        print(f"Scraping {prefix} {year} schedule...")

        season_url = f"https://www.basketball-reference.com/leagues/{prefix}_{year}_games.html"

        try:
            response = safe_request(season_url)
            if not response:
                print(f"Could not fetch {season_url}, skipping...")
                continue
        except Exception as e:
            print(f"Skipping {year}: {e}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")

        # Find all month links dynamically
        month_links = [
            a['href']
            for a in soup.select("div#content div.filter a")
            if a['href'].endswith(".html")
        ]

        for link in month_links:
            month_url = f"https://www.basketball-reference.com{link}"
            try:
                month_response = safe_request(month_url)
                if not month_response:
                    continue
                month_soup = BeautifulSoup(month_response.text, "html.parser")

                for row in month_soup.select("table#schedule tbody tr"):
                    try:
                        date_cell = row.find("th", {"data-stat": "date_game"})
                        if not date_cell:
                            continue

                        away_team = row.find("td", {"data-stat": "visitor_team_name"}).find("a")["href"].split("/")[2].upper()
                        home_team = row.find("td", {"data-stat": "home_team_name"}).find("a")["href"].split("/")[2].upper()

                        away_score = row.find("td", {"data-stat": "visitor_pts"}).text
                        home_score = row.find("td", {"data-stat": "home_pts"}).text

                        game_data = {
                            "date": datetime.strptime(date_cell.text, "%a, %b %d, %Y"),  # full datetime
                            "away_team": away_team,
                            "home_team": home_team,
                            "away_score": int(away_score) if away_score else None,
                            "home_score": int(home_score) if home_score else None,
                            "season": year,
                            "league": prefix
                        }


                        # Upsert game
                        games_collection.update_one(
                            {
                                "date": game_data["date"],
                                "away_team": game_data["away_team"],
                                "home_team": game_data["home_team"]
                            },
                            {"$set": game_data},
                            upsert=True
                        )

                    except Exception as e:
                        print(f"Skipping malformed row in {month_url}: {e}")
                        continue
            except Exception as e:
                print(f"Skipping month page {month_url}: {e}")
                continue

    print("All available seasons scraped and upserted successfully.")





def insert_teams(teams):
    print("Upserting teams into MongoDB...")
    for team in teams:
        teams_collection.update_one(
            {"abbreviation": team["abbreviation"]},
            {"$set": team},
            upsert=True
        )



def insert_players(players):
    print(f"Upserting {len(players)} players into MongoDB...")
    for player in players:
        # Convert birth_date to ISO string if it's a date
        if isinstance(player.get("birth_date"), date):
            player["birth_date"] = player["birth_date"].isoformat()

        players_collection.update_one(
            {
                "first_name": player["first_name"],
                "last_name": player["last_name"],
                "birth_date": player["birth_date"]
            },
            {"$set": player},
            upsert=True
        )


def insert_games(games):
    print(f"Upserting {len(games)} games into MongoDB...")
    for game in games:
        if isinstance(game.get("date"), date):
            game["date"] = game["date"].isoformat()

        games_collection.update_one(
            {
                "date": game["date"],
                "home_team": game["home_team"],
                "away_team": game["away_team"]
            },
            {"$set": game},
            upsert=True
        )



def scrape_coach_details(coach_url, coach_name):
    """Scrape details for a single coach given their Basketball Reference URL."""
    response = safe_request(coach_url)
    if not response:
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    details = {
        "full_name": coach_name,
        "url": coach_url,
        "bio": {},
        "stats": {}
    }

    # === Bio / Meta (similar to players) ===
    meta = soup.find("div", {"id": "meta"})
    if meta:
        for p in meta.find_all("p"):
            text = p.get_text(" ", strip=True)
            if ":" in text:
                key, value = text.split(":", 1)
                details["bio"][key.strip()] = value.strip()
    else:
        details["bio"] = None

    # === Coaching tables ===
    tables = soup.find_all("table")
    for table in tables:
        table_id = table.get("id", "unknown_table")
        headers = [th.get_text(strip=True) for th in table.find_all("th")]
        rows_data = []

        for row in table.find_all("tr"):
            if row.get("class") and "thead" in row.get("class"):
                continue
            row_values = []
            for cell in row.find_all(["th", "td"]):
                val = cell.get_text(strip=True)
                row_values.append(val if val != "" else None)
            if any(row_values):
                rows_data.append(row_values)

        details["stats"][table_id] = {
            "headers": headers,
            "rows": rows_data if rows_data else None
        }

    return details


def scrape_all_coaches(db):
    """Scrape all coaches from Basketball Reference index page and upsert into MongoDB."""
    coaches_collection = db['coaches']
    index_url = "https://www.basketball-reference.com/coaches/"
    response = safe_request(index_url)
    if not response:
        print("Failed to fetch coaches index page.")
        return

    soup = BeautifulSoup(response.text, "html.parser")
    coach_links = soup.select("table#coaches a")

    for link in coach_links:
        coach_name = link.text.strip()
        coach_url = f"https://www.basketball-reference.com{link['href']}"

        try:
            details = scrape_coach_details(coach_url, coach_name)
            if details:
                coaches_collection.update_one(
                    {"url": coach_url},
                    {"$set": details},
                    upsert=True
                )
                print(f"✅ Scraped {coach_name}")
        except Exception as e:
            print(f"Error scraping {coach_name}: {e}")
            continue

    print("Finished scraping all coaches.")

# Main execution
def main():
    try:
        # Scrape and insert teams
        '''try:
            teams = scrape_teams()
            if teams:
                insert_teams(teams)
        except Exception as e:
            print(f"Error scraping/inserting teams: {e}")

        '''# Scrape and insert players
        '''try:
            players = scrape_players()
            if players:
                insert_players(players)  # No team_id needed now
        except Exception as e:
            print(f"Error scraping/inserting players: {e}")

        '''
        
        '''while True:
            try:
                scrape_all_player_details()
                break  # exit if finished successfully
            except pymongo.errors.CursorNotFound as e:
                print(f"CursorNotFound — restarting scrape: {e}")
                continue  # rerun from the top
            except Exception as e:
                print(f"Error scraping player details: {e}")
                break  # break on other errors
        '''
        # Scrape and insert games
        '''try:
            games = scrape_and_upsert_schedule()
            if games:
                insert_games(games)
        except Exception as e:
            print(f"Error scraping/inserting games: {e}")
        '''
        try:
            print("\n=== Scraping Coaches ===")
            scrape_all_coaches(db)
        except Exception as e:
            print(f"Error scraping coaches: {e}")
    
        
        print("Database population completed successfully.")
        
    except Exception as e:
        print(f"Fatal error: {e}")


if __name__ == "__main__":
    main()
