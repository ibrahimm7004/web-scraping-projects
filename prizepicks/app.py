import requests
import pandas as pd
import time
import pytz
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv
from flask import Flask

# Load environment variables
load_dotenv()

# Flask app initialization
app = Flask(__name__)

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

firebase_credentials = {
    "type": os.getenv("FIREBASE_TYPE"),
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL"),
}

cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred)
db = firestore.client()


@app.route("/")
def home():
    return "Player Scraper is running!"


# Discord integration
def send_to_discord(message):
    payload = {"content": message}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(
            DISCORD_WEBHOOK_URL, json=payload, headers=headers
        )
        if response.status_code == 204:
            print(f"Message sent successfully to Discord: {message[:50]}...")
        else:
            print(
                f"Failed to send message: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending message to Discord: {e}")


# Player existence check
def is_new_player(player_id):
    try:
        # Check if the player ID exists in Firebase
        doc_ref = db.collection("players").document(player_id)
        doc = doc_ref.get()
        return not doc.exists
    except Exception as e:
        print(f"Error checking player in Firebase: {e}")
        return False


# Saving player data
def save_player_to_firebase(player_id, player_data):
    try:
        doc_ref = db.collection("players").document(player_id)
        doc_ref.set(player_data)
        print(f"Player {player_id} saved to Firebase.")
    except Exception as e:
        print(f"Error saving player to Firebase: {e}")


# Extracting data from the endpoint with exceptional handling
def call_endpoint(url, max_level=3, include_player_info=False, retry_delay=10):
    while True:
        try:
            # Attempt to fetch data from the API
            response = requests.get(url)
            response.raise_for_status()  # Raise an HTTPError for bad responses (e.g., 4xx, 5xx)

            resp = response.json()
            data = pd.json_normalize(resp.get("data", []), max_level=max_level)

            if include_player_info and "included" in resp:
                included = pd.json_normalize(
                    resp.get("included", []), max_level=max_level)
                player_info = included[included["type"] == "new_player"][
                    ["id", "attributes.name", "attributes.team", "attributes.position"]
                ]
                data = data.merge(
                    player_info,
                    how="left",
                    left_on="relationships.new_player.data.id",
                    right_on="id",
                    suffixes=("", "_player"),
                )

            # Successfully fetched data
            print("Data successfully fetched from API.")
            return pd.DataFrame(data)

        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            print(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)


# Processing data
def fetch_and_process_data():
    league_id = 82
    url = f"https://partner-api.prizepicks.com/projections?league_id={league_id}&per_page=1000"
    data = call_endpoint(url, max_level=3, include_player_info=True)

    if data.empty:
        print("No data fetched from the PrizePicks API.")
        return

    # Only new player iterated
    for _, row in data.iterrows():
        player_id = row["id"]  # this is unique for every entry in the data
        if is_new_player(player_id):
            player_name = row.get("attributes.name", "Unknown")
            team = row.get("attributes.team", "N/A")
            position = row.get("attributes.position", "N/A")
            score = row.get("attributes.line_score", "N/A")
            stat = row.get("attributes.stat_type", "N/A")
            start_time = row.get("attributes.start_time", "N/A")
            updated_at_time = row.get("attributes.updated_at", "N/A")

            # Formatting start time
            try:
                if start_time != "N/A":
                    datetime_obj = datetime.fromisoformat(start_time)
                    pacific = pytz.timezone("US/Pacific")
                    datetime_pst = datetime_obj.astimezone(pacific)
                    start_time_formatted = datetime_pst.strftime(
                        "%Y-%m-%d | %I:%M:%S %p")
                else:
                    start_time_formatted = "N/A"
            except Exception as e:
                print(f"Error formatting start time: {e}")
                start_time_formatted = "N/A"

            # Formatting updated_at time
            try:
                if updated_at_time != "N/A":
                    datetime_obj = datetime.fromisoformat(updated_at_time)
                    pacific = pytz.timezone("US/Pacific")
                    datetime_pst = datetime_obj.astimezone(pacific)
                    updated_at_time_formatted = datetime_pst.strftime(
                        "%Y-%m-%d | %I:%M:%S %p"
                    )
                else:
                    updated_at_time_formatted = "N/A"
            except Exception as e:
                print(f"Error formatting updated_at time: {e}")
                updated_at_time_formatted = "N/A"

            player_data = {
                "name": player_name,
                "team": team,
                "position": position,
                "score": score,
                "stat": stat,
                "start_time": start_time_formatted,
                "updated_at": updated_at_time_formatted,
            }

            save_player_to_firebase(player_id, player_data)

            message = (
                f"New Player Update:\n"
                f"- Name: {player_name}\n"
                f"- Team: {team}\n"
                f"- Position: {position}\n"
                f"- Score: {score}\n"
                f"- Stat: {stat}\n"
                f"- Start Date/Time (PST): {start_time_formatted}\n"
                f"- Updated at Date/Time (PST): {updated_at_time_formatted}"
            )
            send_to_discord(message)


@app.route("/run-scraper")
def run_scraper():
    """Run the scraper once."""
    fetch_and_process_data()
    return "Scraper run completed!"


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
