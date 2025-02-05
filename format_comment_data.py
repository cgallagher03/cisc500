import pandas as pd
import ast

def createThreadStr(comments_sequence):
    formatted = "---BEGIN THREAD---\n"
    formatted += f"Diff Hunk:\n{comments_sequence['diff_hunk']}\n\n"

    comments = comments_sequence['replies']
    comments.insert(0, comments_sequence['comment'])

    formatted_comments = [
        f"(from {'author' if comment['is_from_author'] else 'reviewer'}) [{comment['timestamp']}] {comment['body']}" 
        for comment in comments
    ]
    formatted += "\n".join(formatted_comments)
    formatted += "\n---END THREAD---"

    return formatted

def createSingleStr(comments_sequence):
    comment = comments_sequence['comment']
    return f"(from {'author' if comment['is_from_author'] else 'reviewer'}) [{comment['timestamp']}] {comment['body']}"

def safe_literal_eval(val):
    if pd.isna(val):  
        return []     
    try:
        return ast.literal_eval(val)
    except (ValueError, SyntaxError):
        return [] 

if __name__ == "__main__":
    df = pd.read_csv('data/pull_requests_filtered.csv')
    df['temp'] = df['comments'].apply(safe_literal_eval)

    formatted_comments = []

    for pr_comments in df['temp']:
        comments_array = [createThreadStr(comments_sequence) if comments_sequence['type'] == "review" else createSingleStr(comments_sequence) for comments_sequence in pr_comments]
        formatted_comments.append("\n\n".join(comments_array))
        
    df['Formatted Comments'] = formatted_comments
    df = df.drop('temp', axis=1)
    df = df.drop('comments', axis=1)

    df.to_csv('data/pull_requests_filtered.csv', index=False)
