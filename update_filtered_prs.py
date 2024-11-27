import pandas as pd
import requests

df = pd.read_csv("data/pull_requests_filtered.csv")

GITHUB_TOKENS = []
token_index = 0

def get_next_token():
    global token_index
    token = GITHUB_TOKENS[token_index]
    token_index = (token_index + 1) % len(GITHUB_TOKENS)
    return token

def fetch_data_with_token_cycle(pr_number):
    try:

        api_url = f"https://api.github.com/repos/home-assistant/core/pulls/{pr_number}"

        headers = {"Authorization": f"token {get_next_token()}"}

        response = requests.get(api_url, headers=headers)

        if response.status_code == 200:
            pr_data = response.json()
            author = pr_data["user"]["login"]
            integration_name = next((label["name"].split(": ")[-1] for label in pr_data["labels"] if "integration:" in label["name"]), "")

            return integration_name, author
        else:
            return "", ""
    except Exception as e:
        print(e)
        return "", ""


df[["Integration", "Author"]] = pd.DataFrame(
    df["PR Number"].apply(fetch_data_with_token_cycle).tolist(), index=df.index
)

df.to_csv("pull_requests_filtered_1.csv", index=False)
