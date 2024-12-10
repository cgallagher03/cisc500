"""
This script first produces a set of formatted comments for each PR in a dataframe e.g.

(review comment from reviewer) [2023-04-25T07:58:37Z] We can just implement the `native_value` property method instead in this case.
(review comment from reviewer) [2023-04-25T08:30:54Z] If we never use the key in the `NUMBER_TYPES` dict, it doesn't need to be a dict. It could be a tuple, eg.
(review comment from reviewer) [2023-04-25T20:29:26Z] We don't seem to need the check. We can just return the value regardless if it's None or not.
(review comment from author) [2023-04-25T20:35:18Z] 👍 just figured that out on my own. Sorry for the commit spam, currently sitting in the train and the internet isn't fast enough to setup the full development environment on my work laptop... 
...
and subsequently uses the OpenAI API to categories the challenges in each PR *individually* based on these

The identified categories can then be used as a basis for developing a taxonomy to be applied to all PRs as a whole.
"""

import requests
from openai import OpenAI
from dotenv import load_dotenv
from os import environ
from pydantic import BaseModel
import pandas as pd
from typing import TypedDict

load_dotenv()
GITHUB_API_KEY = environ.get("GITHUB_PAT_1")
client = OpenAI()   # by default gets api key from env under OPENAI_API_KEY

class CommentCategoriesExtraction(BaseModel):
    categories: list[str]


class Comment(TypedDict):
    type: str
    timestamp: str  
    body: str
    is_from_author: bool


def fetch_issue_comments(pr_number: int, author: str) -> list[Comment]:
    response = requests.get(f"https://api.github.com/repos/home-assistant/core/issues/{pr_number}/comments", headers={"Authorization": f"Bearer {GITHUB_API_KEY}"})
    if response.status_code != 200:
        print(f"Failed to fetch issue comments for PR {pr_number}. Status code: {response.status_code}")
        return []
    
    return [{'type': 'issue', 'timestamp': comment['created_at'], 'body': comment['body'], 'is_from_author': comment['user']['login'] == author} for comment in response.json() if comment['user']['type'] != 'Bot']


def fetch_review_comments(pr_number: int, author: str) -> list[Comment]:
    response = requests.get(f"https://api.github.com/repos/home-assistant/core/pulls/{pr_number}/comments", headers={"Authorization": f"Bearer {GITHUB_API_KEY}"})
    return [{'type': 'review', 'timestamp': comment['created_at'], 'body': comment['body'], 'is_from_author': comment['user']['login'] == author} for comment in response.json()]


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


# generate ordered, formatted list of comments and add to dataframe
def add_all_pr_comments_to_df(df: pd.DataFrame) -> None:
    formatted_comments = []
    for pr_number, pr_author in zip(df['PR Number'], df['Author']):

        issue_comments = fetch_issue_comments(pr_number, pr_author)
        review_comments = fetch_review_comments(pr_number, pr_author)

        comments = merge_comments_of_pr(issue_comments, review_comments)
        formatted_bodies = [
            f"({comment['type']} comment from {'author' if comment['is_from_author'] else 'reviewer'}) [{comment['timestamp']}] {comment['body']}" 
            for comment in comments
        ]
        comment_string = "\n".join(formatted_bodies)
        formatted_comments.append(comment_string)

    df['Formatted Comments'] = formatted_comments



def gpt_categorize_challenges(comment_string: str) -> list[str]:
    if comment_string == "":
        return []

    try:
        chat_completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "You are a helpful assistant that analyzes pull request comments "
                    "within the Home Assistant repository to categorize challenges faced when developing device integrations, "
                    "and returns a list of them. If not categorizable, use 'Other'. If you can see that there's a long gap before or between a comment, "
                    "and it's likely that the gap is simply due to delay in a reviewer commenting, use 'Reviewer Delay' rather than inventing categories." 
                )},
                {"role": "user", "content": f"Analyze the following conversation:\n{comment_string}"},
                {"role": "assistant", "content": (
                    "categories=['Testing Issues', 'Naming/ID Issues', 'Code Structure Issues', "
                    "'Communication Issues', 'Review Process Issues', 'Other']"
                )},
                {"role": "user", "content": f"Can you make sure any Home Assistant/Smart home-specific concepts are captured:\n{comment_string}"}
            ],
            response_format=CommentCategoriesExtraction
        )
    except Exception as e: 
        print(e)
        return []
    
    response = chat_completion.choices[0].message.parsed
    categories = response.categories
    return categories


if __name__ == "__main__":
    df = pd.read_csv('data/pull_requests_complex_features.csv').head(50)

    add_all_pr_comments_to_df(df)

    df['Categorized Challenges'] = df['Formatted Comments'].apply(gpt_categorize_challenges)
    df.to_csv('data/pull_requests_complex_issues_categorized.csv', index=False)


