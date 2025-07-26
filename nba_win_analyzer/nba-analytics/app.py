from flask import Flask, request, jsonify
import requests
from openai import OpenAI
import json
from datetime import datetime
from collections import defaultdict
from flask_cors import CORS
import re
import time
from ratelimit import limits, sleep_and_retry


app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}}, supports_credentials=False)


# Configuration
BALLDONTLIE_API_KEY = "1e70e025-cf8a-44b0-90aa-06a9ea53343d"
OPENAI_API_KEY = "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"
HEADERS = {"Authorization": f"Bearer {BALLDONTLIE_API_KEY}"}
BASE_URL = "https://api.balldontlie.io/v1"
# Cache for team data
team_cache = {}

client = OpenAI(api_key=OPENAI_API_KEY)

REQUESTS_PER_MINUTE = 60  # Adjust as needed

#comment
@sleep_and_retry
@limits(calls=REQUESTS_PER_MINUTE, period=60)

def call_bdl_api(url, params=None, headers=None, **kwargs):
    response = requests.get(url, params=params, headers=headers, **kwargs)

    if response.status_code == 429:
        raise Exception("Rate limit exceeded.")

    return response
def extract_json(text):
    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    return text

def interpret_query_with_ai(query):
    prompt = f'''Analyze this NBA team wins query and return JSON with:
- team_names (array of strings)
- seasons (array of years)
- comparison_type ("standalone", "team_comparison", "league_average")
- visualization_type ("bar", "line", "pie") judge based on the query which visualization is most appropriate, unless specified in the query.

Query: {query}

Examples:
1. "Lakers wins in 2020" → {{
    "team_names": ["Los Angeles Lakers"],
    "seasons": [2020],
    "comparison_type": "standalone"
}}
2. "Compare Celtics and Warriors 2015-2023" → {{
    "team_names": ["Boston Celtics", "Golden State Warriors"],
    "seasons": [2015,2023],
    "comparison_type": "team_comparison",
}}

Convert all team names to full names as used in the API, e.g. "Los Angeles Lakers" instead of "Lakers".

Return ONLY valid JSON in the following format:
{{
  "team_names": [...],
  "seasons": [...],
  "comparison_type": "...",
  "visualization_type": "..."
}}
'''


    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages= [{"role": "user", "content": prompt}],
            temperature=0.3,
        )   
        raw_content = response.choices[0].message.content
        print("raw", repr(raw_content))
        cleaned = extract_json(raw_content)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            print("Json decode error:", e)
            return {
                "team_names": ["Los Angeles Lakers"],
                "seasons": [2023],
                "comparison_type": "standalone",
                "visualization_type": "bar"
            }
    except json.JSONDecodeError as e:
        print("JSON Decode Error:", e)
        return {"error": "Invalid JSON response from AI"}
    except Exception as e:
        print("Error interpreting query:", e)
        return {"error": str(e)}

def get_team_id(team_name):
    """Get team ID from name with caching"""
    if team_name in team_cache:
        return team_cache[team_name]
    
    response = call_bdl_api(f"{BASE_URL}/teams", headers=HEADERS)
    for team in response.json()['data']:
        team_cache[team['full_name']] = team['id']
        if team_name.lower() in team['full_name'].lower():
            return team['id']
    return None

def get_team_wins(team_id, season):
    """Calculate regular season wins for a team"""
    params = {
        'seasons[]': season,
        'team_ids[]': team_id,
        'per_page': 100
    }
    
    wins = 0
    page = 1

    while True:
        time.sleep(1.1) # Rate limit handling
        response = call_bdl_api(f"{BASE_URL}/games", headers=HEADERS, params=params)
        params['page'] = page

        # Retry logic (max 3 attempts)
        for attempt in range(3):
            time.sleep(2)  # backoff before retry
            params['page'] = page  # Reset page for retry
            response = call_bdl_api(f"{BASE_URL}/games", headers=HEADERS, params=params)

            if response.status_code == 429:
                print(f"Rate limited on season {season}, page {page}, retrying ({attempt+1}/3)...")
                time.sleep(2)  # backoff before retry
                continue
            elif response.status_code != 200:
                print(f"Failed to get games for team {team_id} in season {season} (page {page}): {response.status_code}")
                return wins
            else:
                break  # Success

        try:
            games = response.json()['data']
        except Exception as e:
            print(f"JSON decode error on team {team_id} season {season} page {page}: {e}")
            return wins

        # Process game data
        for game in games:
            if game['postseason']:
                continue
            if game['home_team']['id'] == team_id:
                wins += 1 if game['home_team_score'] > game['visitor_team_score'] else 0
            else:
                wins += 1 if game['visitor_team_score'] > game['home_team_score'] else 0

        # Stop condition — no more data
        if len(games) < 100:
            break
        page += 1

    print(f"Wins for team ID {team_id} in {season}: {wins}")
    return wins


def get_league_avg_wins(season):
    """Calculate average wins across all teams"""
    team_wins = defaultdict(int)
    params = {
        'seasons[]': season,
        'per_page': 100,
        'page': 1
    }

    while True:
        response = call_bdl_api(f"{BASE_URL}/games", headers=HEADERS, params=params)

        try:
            data = response.json()
        except Exception as e:
            print("JSON decode error:", e)
            break

        games = data.get('data', [])
        if not games:
            print(f"No games returned for season {season}, page {params['page']}")
            break

        for game in games:
            if game['postseason']:
                continue
            home_id = game['home_team']['id']
            visitor_id = game['visitor_team']['id']
            home_won = game['home_team_score'] > game['visitor_team_score']
            team_wins[home_id] += 1 if home_won else 0
            team_wins[visitor_id] += 0 if home_won else 1

        if len(games) < 100:
            break

        params['page'] += 1

    return sum(team_wins.values()) / len(team_wins) if team_wins else 0

@app.route('/api/analyze-team-wins', methods=['POST'])
def analyze_team_wins():
    try:
        query = request.json.get('query', '')
        print("Received query:", query)
        analysis = interpret_query_with_ai(query)
        
        results = {
            "analysis": {
                "visualization_type": analysis["visualization_type"],
            },
            "data": {},
            "league_averages": {}
        }
        
        # Process each team
        for team_name in analysis['team_names']:
            team_id = get_team_id(team_name)
            if not team_id:
                continue
                
            results['data'][team_name] = {}
            for season in range(analysis['seasons'][0], analysis['seasons'][-1] + 1):
                wins = get_team_wins(team_id, season)
                results['data'][team_name][season] = wins

        if analysis['comparison_type'] == 'league_average':
            season_range = sorted(set(analysis['seasons']))
            if len(season_range) == 2 and season_range[1] - season_range[0] >=1:
                season_range = list(range(season_range[0], season_range[1] + 1))
            for season in season_range:
                results['league_averages'][season] = get_league_avg_wins(season)
        return jsonify(results)
    
    except Exception as e:
        print(">>> ERROR:", str(e))
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=8000)