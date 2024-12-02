import requests
from openai import OpenAI
from dotenv import load_dotenv
from os import environ
from pydantic import BaseModel
import pandas as pd

load_dotenv()

GITHUB_API_KEY = environ.get("GITHUB_PAT_1")
client = OpenAI()   # automatically gets api key from env under OPENAI_API_KEY

author = 'YogevBokobza'

def fetch_issue_comments():
    response = requests.get("https://api.github.com/repos/home-assistant/core/issues/127277/comments", headers={"Authorization": f"Bearer {GITHUB_API_KEY}"})
    issue_comment_data = response.json()
    return [{'type': 'issue', 'timestamp': comment['created_at'], 'body': comment['body'], 'is_from_author': comment['user']['login'] == author} for comment in issue_comment_data if comment['user']['type'] != 'Bot']

def fetch_review_comments():
    response = requests.get("https://api.github.com/repos/home-assistant/core/pulls/127277/comments", headers={"Authorization": f"Bearer {GITHUB_API_KEY}"})
    review_comment_data = response.json()
    return [{'type': 'review', 'timestamp': comment['created_at'], 'body': comment['body'], 'is_from_author': comment['user']['login'] == author} for comment in review_comment_data]

def merge_comments(issue_comments, review_comments):
    merged = []
    i, j = 0, 0
    
    # merge while both lists have elements
    while i < len(review_comments) and j < len(issue_comments):
        if review_comments[i]['timestamp'] <= issue_comments[j]['timestamp']:
            merged.append(review_comments[i])
            i += 1
        else:
            merged.append(issue_comments[j])
            j += 1

    # add remaining elements from non-exhausted list
    merged.extend(review_comments[i:])
    merged.extend(issue_comments[j:])
    
    return merged

issue_comments = fetch_issue_comments()
review_comments = fetch_review_comments()

comments = merge_comments(issue_comments, review_comments)
formatted_bodies = [
    f"({comment['type']} comment from {'author' if comment['is_from_author'] else 'reviewer'}) [{comment['timestamp']}] {comment['body']}" 
    for comment in comments
]
prompt_body = "\n".join(formatted_bodies)

class CommentCategoriesExtraction(BaseModel):
    categories: list[str]

chat_response = client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that analyzes pull request comments within the Home Assistant repository to categorize challenges faced when developing device integrations, and returns a list of them. If not categorizable, use 'Other'."},
        {"role": "user", "content": f"{prompt_body}"},
        {"role": "assistant", "content": "categories=['Testing Issues', 'Naming/ID Issues', 'Code Structure Issues', 'Communication Issues', 'Review Process Issues', 'Other']"},
        {"role": "user", "content": f"Can you make sure any Home Assistant/Smart home specific concepts are captured: {prompt_body}"}
    ],
    response_format=CommentCategoriesExtraction
)

print(chat_response.choices[0].message.parsed)

# Example Outputs:
# categories=['Testing Issues', 'Naming/ID Issues', 'Entity Creation Issues', 'Code Structure Issues', 'Device Category Issues', 'Ecosystem Dependency Issues', 'Communication Issues', 'Review Process Issues', 'Other']
# categories=['Testing Issues', 'Naming/ID Issues', 'Device Category Confusion (e.g., light, cover)', 'Code Structure Issues', 'Communication Issues', 'Integration Dependencies (e.g., aioswitcher)', 'Review Process Issues', 'Device-Specific Implementation Issues', 'Other']
# categories=['Testing Issues', 'Naming/ID Issues', 'Entity Management Issues', 'Device Category Management', 'Code Architecture Issues', 'Device Type Complexity', 'Communication Issues', 'Review Process Issues', 'Other']
# categories=['Testing Issues', 'Naming/ID Issues', 'Entity Creation and Management Issues', 'Communication Issues', 'Code Structure Issues', 'Review Process Issues', "Conceptual Issues (e.g., device categories like 'cover', 'light')", 'Other']
# categories=['Testing Issues', 'Naming/ID Issues', 'Device Entity Issues', 'Class Structure Issues', 'Communication Issues', 'Review Process Issues', 'Other']
