from datetime import datetime, timezone
import time
from typing import TypedDict, Dict, List
from dotenv import load_dotenv
from os import environ
import pandas as pd
import requests
from collections import defaultdict

load_dotenv()
tokens = environ.get("GITHUB_PATS").split(",")
current_token_index = 0

class Comment(TypedDict):
    id: int
    type: str
    timestamp: str  
    body: str
    is_from_author: bool
    diff_hunk: str

def rotate_token():
    global current_token_index
    current_token_index = (current_token_index + 1) % len(tokens)
    response = requests.get("https://api.github.com/rate_limit", headers={"Authorization": f"Bearer {tokens[current_token_index]}"})
    data = response.json()
    if (data['resources']['core']['remaining'] == 0):
        reset_time = datetime.fromtimestamp(data['resources']['core']['reset'], tz=timezone.utc)
        wait_time = (reset_time - datetime.now(timezone.utc)).total_seconds()
        print('reset time', reset_time)
        print('wait time', wait_time)
        time.sleep(wait_time)

def fetch_issue_comments(pr_number: int, author: str) -> list[Dict]:
    response = requests.get(f"https://api.github.com/repos/home-assistant/core/issues/{pr_number}/comments", headers={"Authorization": f"Bearer {tokens[current_token_index]}"})

    if response.status_code == 200:
        # return [{'type': 'issue', 'timestamp': comment['created_at'], 'body': comment['body'], 'is_from_author': comment['user']['login'] == author} for comment in response.json() if comment['user']['type'] != 'Bot']
        return [{**comment, 'is_from_author': comment['user']['login'] == author} for comment in response.json() if comment['user']['type'] != 'Bot']
    if response.status_code in [403, 429]:  # rate limit reached
        rotate_token()
        return fetch_issue_comments(pr_number, author) # retry
    
    print(f"Failed to fetch issue comments for PR {pr_number}. Status code: {response.status_code}")
    return []

def fetch_review_comments(pr_number: int, author: str) -> list[Dict]:
    response = requests.get(f"https://api.github.com/repos/home-assistant/core/pulls/{pr_number}/comments", headers={"Authorization": f"Bearer {tokens[current_token_index]}"})

    if response.status_code == 200:
        return [{**comment, 'is_from_author': comment['user']['login'] == author} for comment in response.json() if comment['user']['type'] != 'Bot']
    
    if response.status_code in [403, 429]:  # rate limit reached
        rotate_token()
        return fetch_review_comments(pr_number, author) # retry
        
    print(f"Failed to fetch review comments for PR {pr_number}. Status code: {response.status_code}")
    return []

def organize_review_comments(review_comments: List[Dict], reply_map: Dict[int, List[Comment]], top_level_comments: List[Dict]):
    for comment in review_comments:
        if 'in_reply_to_id' in comment:
            parent_id = comment['in_reply_to_id']
            reply_map[parent_id].append(
                {'id': comment['id'], 'type': 'review', 'timestamp': comment['created_at'], 'body': comment['body'], 'is_from_author': comment['is_from_author'], 'diff_hunk': comment['diff_hunk']}
            )
        else:
            top_level_comments.append(
                {'id': comment['id'], 'type': 'review', 'timestamp': comment['created_at'], 'body': comment['body'], 'is_from_author': comment['is_from_author'], 'diff_hunk': comment['diff_hunk']}
            )

def organize_issue_comments(issue_comments: List[Dict], top_level_comments: List[Comment]):
    for comment in issue_comments:
        top_level_comments.append(
            {'id': comment['id'], 'type': 'issue', 'timestamp': comment['created_at'], 'body': comment['body'], 'is_from_author': comment['is_from_author']}
        )

def build_reply_thread(comment: Comment, reply_map: Dict[int, List[Comment]]) -> Dict:
    thread = {
        'type': 'review',
        'diff_hunk': comment['diff_hunk'],
        'comment': {k: v for k, v in comment.items() if k not in ['diff_hunk', 'type']},
        'replies': []
    }

    if comment['id'] in reply_map:
        replies = sorted(
            reply_map[comment['id']],
            key=lambda comment: comment['timestamp']
        )

        for reply in replies:
            thread['replies'].append({k: v for k, v in reply.items() if k not in ['diff_hunk', 'type']})
            if reply['id'] in reply_map:
                thread['replies'].extend(build_reply_thread(reply, reply_map)['replies'])

    return thread

def add_ordered_comments_to_df(df: pd.DataFrame):
    comments = []
    comment_counts = []

    for pr_number, pr_author in zip(df['PR Number'], df['Author']):
        reply_map: Dict[int, List[Comment]] = defaultdict(list)
        top_level_comments: List[Comment] = []

        try:
            issue_comments = fetch_issue_comments(pr_number, pr_author)
            review_comments = fetch_review_comments(pr_number, pr_author)

            organize_review_comments(review_comments, reply_map, top_level_comments)
            organize_issue_comments(issue_comments, top_level_comments)

            top_level_comments.sort(key=lambda comment: comment['timestamp'])

            ordered_comments = []
            for comment in top_level_comments:
                if comment['type'] == 'review':
                    ordered_comments.append(build_reply_thread(comment, reply_map))
                else:
                    ordered_comments.append({'type': 'issue', 'comment': comment})

            comment_counts.append(len(issue_comments) + len(review_comments))
            comments.append(ordered_comments)

        except Exception as e:
            print(f"Error occurred: {e}")

    # df['Total Comments'] = comment_counts
    df['Comments'] = comments

if __name__ == "__main__":
    df = pd.read_csv('data/pull_requests_filtered.csv')
    add_ordered_comments_to_df(df)
    df.to_csv('data/pull_requests_filtered_test.csv', index=False)

    
    

    
