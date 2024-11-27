import requests
from openai import OpenAI
from dotenv import load_dotenv
from os import environ
from pydantic import BaseModel
import pandas as pd

load_dotenv()

GITHUB_API_KEY = environ.get("GITHUB_PAT_1")
client = OpenAI()   # automatically gets api key from env under OPENAI_API_KEY

df = pd.read_csv('data/pull_requests_complex_features.csv').head(10)

issue_comments_list = []
review_comments_list = []

for pr_number in df['PR Number']:

    # issue comments
    issue_url = f"https://api.github.com/repos/home-assistant/core/issues/{pr_number}/comments"
    response = requests.get(issue_url, headers={"Authorization": f"Bearer {GITHUB_API_KEY}"})
    if response.status_code == 200:
        issue_comment_data = response.json()
        issue_comments = [comment['body'] for comment in issue_comment_data if comment['user']['type'] != 'Bot']
    else:
        issue_comments = [] 
    
    # review comments
    review_url = f"https://api.github.com/repos/home-assistant/core/pulls/{pr_number}/comments"
    response = requests.get(review_url, headers={"Authorization": f"Bearer {GITHUB_API_KEY}"})
    if response.status_code == 200:
        review_comment_data = response.json()
        review_comments = [comment['body'] for comment in review_comment_data]
    else:
        review_comments = []  
    
    issue_comments_list.append(issue_comments)
    review_comments_list.append(review_comments)

df['Issue Comments'] = issue_comments_list
df['Review Comments'] = review_comments_list

class CommentCategoriesExtraction(BaseModel):
    categories: list[str]

def categorize_comments(comments: list[str]) -> list[str]:
    combined_comments = "\n".join(comments)
    
    try:
        chat_completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "You are a helpful assistant that analyzes pull request comments "
                    "within the Home Assistant repository to categorize challenges faced when developing device integrations, "
                    "and returns a list of them. If not categorizable, use 'Other'."
                )},
                {"role": "user", "content": combined_comments},
                {"role": "assistant", "content": (
                    "categories=['Testing Issues', 'Naming/ID Issues', 'Code Structure Issues', "
                    "'Communication Issues', 'Review Process Issues', 'Other']"
                )},
                {"role": "user", "content": f"Can you make sure any Home Assistant/Smart home-specific concepts are captured: {combined_comments}"}
            ],
            response_format=CommentCategoriesExtraction
        )
    except Exception as e: 
        print(e)
        return []
    
    response = chat_completion.choices[0].message.parsed
    categories = response.categories
    return categories

categories_list = []

for index, row in df.iterrows():
    all_comments = row['Issue Comments'] + row['Review Comments']
    categories = categorize_comments(all_comments)
    categories_list.append(categories)

df['Categories'] = categories_list

print(df.head())
df.to_csv('data/pull_requests_with_categorized_comments.csv', index=False)
