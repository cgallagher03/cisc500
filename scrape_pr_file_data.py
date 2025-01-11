
from datetime import datetime, timezone
import time
from dotenv import load_dotenv
from os import environ
import pandas as pd
import requests

load_dotenv()
tokens = environ.get("GITHUB_PATS").split(",")
current_token_index = 0

def rotate_token():
    global current_token_index
    current_token_index = (current_token_index + 1) % len(tokens)
    response = requests.get("https://api.github.com/rate_limit", headers={"Authorization": f"Bearer {tokens[current_token_index]}"})
    data = response.json()
    if (data.resources.core.remaining == 0):
        wait_time = (data.resources.core.reset - datetime.now(timezone.utc)).total_seconds()
        time.sleep(wait_time)

def fetch_loc_changed(pr_number: int) -> int:
    response = requests.get(f"https://api.github.com/repos/home-assistant/core/pulls/{pr_number}/files")
    if response.status_code == 200:
        return sum([file.changes for file in response.json()])
    if response.status_code in [403, 429]:  # rate limit reached
        rotate_token()
        return fetch_loc_changed(pr_number) # retry
    
    print(f"Failed to fetch LOC changed for PR {pr_number}. Status code: {response.status_code}")
    return -1


def add_loc_to_df(df: pd.DataFrame) -> None:
    batch_count = 0

    loc_changed = []
    for pr_number in df['PR Number']:
        try:
            changes = fetch_loc_changed(pr_number)
            loc_changed.append(changes)

            batch_count += 1
            if batch_count >= 100:
                df['LOC Changed'] = loc_changed
                df.to_csv('data/pull_requests_filtered.csv', index=False)
                batch_count = 0

        except Exception as e:
            print(f"Error occurred: {e}")
            df['LOC Changed'] = loc_changed
            df.to_csv('data/pull_requests_filtered.csv', index=False)

if __name__ == "__main__":
    df = pd.read_csv('data/pull_requests_filtered.csv')
    add_loc_to_df(df)
    df.to_csv('data/pull_requests_filtered.csv', index=False)   # final save for remaining records that didn't reach batch_count limit
