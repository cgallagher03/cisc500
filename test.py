import requests
from openai import OpenAI
from dotenv import load_dotenv
from os import environ
from pydantic import BaseModel

load_dotenv()

GITHUB_API = environ.get("GITHUB_PAT_1")
client = OpenAI()   # automatically gets api key from env under OPENAI_API_KEY

response = requests.get("https://api.github.com/repos/home-assistant/core/issues/127277/comments", headers={"Authorization": f"Bearer {GITHUB_API}"})
comment_data = response.json()

issue_comment_bodies = [comment['body'] for comment in comment_data if comment['user']['type'] != 'Bot']

response = requests.get("https://api.github.com/repos/home-assistant/core/pulls/127277/comments", headers={"Authorization": f"Bearer {GITHUB_API}"})
comment_data = response.json()

review_comment_bodies = [comment['body'] for comment in comment_data]

body = f"ISSUE COMMENT BODIES: \n{issue_comment_bodies}\n\nREVIEW COMMENT BODIES: \n{review_comment_bodies}"

class CommentCategoriesExtraction(BaseModel):
    categories: list[str]

chat_completion = client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that analyzes pull request comments within the Home Assistant repository to categorize challenges faced when developing device integrations, and returns a list of them. If not categorizable, use 'Other'."},
        {"role": "user", "content": f"{body}"},
        {"role": "assistant", "content": "categories=['Testing Issues', 'Naming/ID Issues', 'Code Structure Issues', 'Communication Issues', 'Review Process Issues', 'Other']"},
        {"role": "user", "content": f"Can you make sure any Home Assistant/Smart home specific concepts are captured: {body}"}
    ],
    response_format=CommentCategoriesExtraction
)

print(chat_completion.choices[0].message.parsed)
