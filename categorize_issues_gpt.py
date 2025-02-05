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

from openai import OpenAI
from dotenv import load_dotenv
from os import environ
from pydantic import BaseModel
import pandas as pd

load_dotenv()
GITHUB_API_KEY = environ.get("GITHUB_PAT")
client = OpenAI()   # by default gets api key from env under OPENAI_API_KEY

class CommentCategoriesExtraction(BaseModel):
    categories: list[str]


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
    df = pd.read_csv('data/pull_requests_filtered.csv').head(50)

    df['Categorized Challenges'] = df['Formatted Comments'].apply(gpt_categorize_challenges)
    df.to_csv('data/pull_requests_filtered_issues_categorized.csv', index=False)


