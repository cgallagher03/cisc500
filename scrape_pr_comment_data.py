
from datetime import datetime, timezone
import time
from typing import TypedDict
from dotenv import load_dotenv
from os import environ
import pandas as pd
import requests

load_dotenv()
tokens = environ.get("GITHUB_PATS").split(",")
current_token_index = 0

class Comment(TypedDict):
    type: str
    timestamp: str  
    body: str
    is_from_author: bool

def rotate_token():
    global current_token_index
    current_token_index = (current_token_index + 1) % len(tokens)
    response = requests.get("https://api.github.com/rate_limit", headers={"Authorization": f"Bearer {tokens[current_token_index]}"})
    data = response.json()
    if (data.resources.core.remaining == 0):
        wait_time = (data.resources.core.reset - datetime.now(timezone.utc)).total_seconds()
        time.sleep(wait_time)


def fetch_issue_comments(pr_number: int, author: str) -> list[Comment]:
    response = requests.get(f"https://api.github.com/repos/home-assistant/core/issues/{pr_number}/comments", headers={"Authorization": f"Bearer {tokens[current_token_index]}"})

    if response.status_code == 200:
        return [{'type': 'issue', 'timestamp': comment['created_at'], 'body': comment['body'], 'is_from_author': comment['user']['login'] == author} for comment in response.json() if comment['user']['type'] != 'Bot']
    if response.status_code in [403, 429]:  # rate limit reached
        rotate_token()
        return fetch_issue_comments(pr_number, author) # retry
    
    print(f"Failed to fetch issue comments for PR {pr_number}. Status code: {response.status_code}")
    return []


def fetch_review_comments(pr_number: int, author: str) -> list[Comment]:
    response = requests.get(f"https://api.github.com/repos/home-assistant/core/pulls/{pr_number}/comments", headers={"Authorization": f"Bearer {tokens[current_token_index]}"})

    if response.status_code == 200:
            return [{'type': 'review', 'timestamp': comment['created_at'], 'body': comment['body'], 'is_from_author': comment['user']['login'] == author} for comment in response.json() if comment['user']['type'] != 'Bot']
    if response.status_code in [403, 429]:  # rate limit reached
            rotate_token()
            return fetch_review_comments(pr_number, author) # retry
        
    print(f"Failed to fetch review comments for PR {pr_number}. Status code: {response.status_code}")
    return []


# merge review and issue comments in chronological order
def merge_comments_of_pr(issue_comments: list[str], review_comments: list[str]) -> list[Comment]:
    merged = []
    i, j = 0, 0
    
    # merge while both lists have elements
    # note that data from each API endpoint comes sorted in asc order by date
    while i < len(review_comments) and j < len(issue_comments):
        if review_comments[i]['timestamp'] <= issue_comments[j]['timestamp']:   # lexicographical comparison works for ISO 8601 format dates
            merged.append(review_comments[i])
            i += 1
        else:
            merged.append(issue_comments[j])
            j += 1

    # add remaining elements from non-exhausted list
    merged.extend(review_comments[i:])
    merged.extend(issue_comments[j:])
    
    return merged

def add_comments_to_df(df: pd.DataFrame) -> None:
    batch_count = 0

    formatted_comments = []
    comment_counts = []
    for pr_number, pr_author in zip(df['PR Number'], df['Author']):
        try:
            issue_comments = fetch_issue_comments(pr_number, pr_author)
            review_comments = fetch_review_comments(pr_number, pr_author)
            comment_counts.append(len(issue_comments) + len(review_comments))

            comments = merge_comments_of_pr(issue_comments, review_comments)
            formatted_bodies = [
                f"({comment['type']} comment from {'author' if comment['is_from_author'] else 'reviewer'}) [{comment['timestamp']}] {comment['body']}" 
                for comment in comments
            ]
            comment_string = "\n".join(formatted_bodies)
            formatted_comments.append(comment_string)

            batch_count += 1
            if batch_count >= 100:
                df['Total Comments'] = comment_counts
                df['Formatted Comments'] = formatted_comments
                df.to_csv('data/pull_requests_filtered.csv', index=False)
                batch_count = 0

        except Exception as e:
            print(f"Error occurred: {e}")
            df['Total Comments'] = comment_counts
            df['Formatted Comments'] = formatted_comments
            df.to_csv('data/pull_requests_filtered.csv', index=False)

    df['Total Comments'] = comment_counts
    df['Formatted Comments'] = formatted_comments

if __name__ == "__main__":
    df = pd.read_csv('data/pull_requests_filtered.csv').head(50)
    add_comments_to_df(df)
    df.to_csv('data/pull_requests_filtered.csv', index=False)   # final save for remaining records that didn't reach batch_count limit
