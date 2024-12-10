"""
This script uses the principle categories identified through use of the `categorize_issues_gpt` script to re-categorize PRs based on the defined taxonomy
"""

import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

from categorize_issues_gpt import CommentCategoriesExtraction

load_dotenv()
client = OpenAI()   # by default gets api key from env under OPENAI_API_KEY

def gpt_categorize_challenges(comment_string: str) -> list[str]:
    if comment_string == "":
        return []

    try:
        chat_completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "You are tasked with categorizing pull request challenges based on comments during their review process. The categories are: "
                    "1. **Process Delays**: Issues like reviewer delays, merge conflicts, or prolonged review times. Keywords: 'reviewer delay', 'merge conflict', 'waiting for review'. "
                    "2. **Technical Challenges**: Issues like code structure problems, integration difficulties, or test failures. Keywords: 'code structure', 'flaky tests', 'integration logic'. "
                    "3. **Documentation and Communication**: Problems with documentation or team communication. Keywords: 'documentation gaps', 'unclear docs', 'communication issues'. "
                    "4. **Specific Domain Challenges**: Ecosystem-specific problems like YAML schema errors or device API limitations. Keywords: 'YAML schema', 'device API limitation', 'sensor value'. "
                    "5. **User Experience**: Issues related to UI/UX or end-user impact. Keywords: 'UI feedback', 'user-facing bug'. "
                    "A pull request can fall into multiple categories."
                )},
                {"role": "user", "content": f"Categorize this PR:\n{comment_string}"},
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
    df = pd.read_csv('data/pull_requests_complex_features_with_comments.csv').head(20)

    df['Categorized Challenges'] = df['Formatted Comments'].apply(gpt_categorize_challenges)
    df.to_csv('data/pull_requests_complex_issues_categorized_refined.csv', index=False)