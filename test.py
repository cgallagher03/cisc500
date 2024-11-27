import requests
from openai import OpenAI
from dotenv import load_dotenv
from os import environ
from pydantic import BaseModel
import pandas as pd

load_dotenv()

GITHUB_API_KEY = environ.get("GITHUB_PAT_1")
client = OpenAI()   # automatically gets api key from env under OPENAI_API_KEY

df = pd.read_csv('data/pull_requests_complex_features.csv').head(30)

response = requests.get("https://api.github.com/repos/home-assistant/core/issues/127277/comments", headers={"Authorization": f"Bearer {GITHUB_API_KEY}"})
comment_data = response.json()
issue_comment_bodies = [comment['body'] for comment in comment_data if comment['user']['type'] != 'Bot']

response = requests.get("https://api.github.com/repos/home-assistant/core/pulls/127277/comments", headers={"Authorization": f"Bearer {GITHUB_API_KEY}"})
comment_data = response.json()
review_comment_bodies = [comment['body'] for comment in comment_data]

body = f"ISSUE COMMENT BODIES: \n{issue_comment_bodies}\n\nREVIEW COMMENT BODIES: \n{review_comment_bodies}"

class CommentCategoriesExtraction(BaseModel):
    categories: list[str]

chat_response = client.beta.chat.completions.parse(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant that analyzes pull request comments within the Home Assistant repository to categorize challenges faced when developing device integrations, and returns a list of them. If not categorizable, use 'Other'."},
        {"role": "user", "content": f"{body}"},
        {"role": "assistant", "content": "categories=['Testing Issues', 'Naming/ID Issues', 'Code Structure Issues', 'Communication Issues', 'Review Process Issues', 'Other']"},
        {"role": "user", "content": f"Can you make sure any Home Assistant/Smart home specific concepts are captured: {body}"}
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
