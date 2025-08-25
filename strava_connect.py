import os
import requests

STRAVA_CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET")
STRAVA_ACCESS_TOKEN = os.environ.get("STRAVA_ACCESS_TOKEN")
STRAVA_REFRESH_TOKEN = os.environ.get("STRAVA_REFRESH_TOKEN")

STRAVA_API_BASE_URL = "https://www.strava.com/api/v3"

def get_headers():
    return {
        "Authorization": f"Bearer {STRAVA_ACCESS_TOKEN}"
    }

def get_athlete():
    url = f"{STRAVA_API_BASE_URL}/athlete"
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()
    return response.json()

if __name__ == "__main__":
    athlete = get_athlete()
    print("Authenticated athlete profile:")
    print(athlete)