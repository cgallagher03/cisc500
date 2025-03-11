import pandas as pd
import ast
import re
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from gensim.models import Word2Vec, KeyedVectors
from gensim.models.word2vec import LineSentence
from textsplit.tools import SimpleSentenceTokenizer
from textsplit.tools import get_penalty, get_segments
from textsplit.algorithm import split_optimal, split_greedy, get_total
from sklearn.feature_extraction.text import CountVectorizer
from nltk.tokenize import texttiling

def safe_literal_eval(val):
    if pd.isna(val):  
        return []     
    try:
        return ast.literal_eval(val)
    except (ValueError, SyntaxError):
        return [] 
    
def clean_text(text):
    # quotes
    # potential if we don't remove quotes to use them in grouping of topics later on
    text = re.sub(r"(?m)^\s*>.*(?:\r?\n|$)", "", text)

    #links and code
    # should we consider using LLM to generate short summary of the code snippets so we don't lose any context it could provide
    # or could use regex to detect patterns in the code and classify them e.g. detecting import statements, function definitions, or added/removed lines.
    pattern = r"```.*?```|http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    cleaned_text = re.sub(pattern, "", text, flags=re.DOTALL)

    # keep only alphanumeric characters and punctuation
    cleaned_text = re.sub(r"[^a-zA-Z0-9.,!?;:'\"(){}\[\]\-]", " ", cleaned_text)

    # remove extra spaces
    cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

    return cleaned_text
    
def preprocess_text(comments_sequence):
    all_comments = []
    for issue_comment in comments_sequence:
        body = clean_text(issue_comment['comment']['body'])
        all_comments.append(body)
    return all_comments

df= pd.read_csv('data/pull_requests_filtered_raw.csv')
df['comments'] = df['comments'].apply(safe_literal_eval)

df['issue_comments'] = df['comments'].apply(lambda comments: [item for item in comments if item['type'] == 'issue'] if type(comments) is not float else comments)
df = df[df['issue_comments'].apply(lambda x: isinstance(x, list) and len(x) > 0)]
df['processed_issue_comments'] = df['issue_comments'].apply(preprocess_text)

# df.head(100).to_csv('data/test.csv')

# ------------------------------------------------------------------------
# ATTEMPT AT TOPIC SEGMENTATION USING TEXTTILING ALGORITHM- TEXT TOO SHORT
# segments = []
# for issue_comments in df['processed_issue_comments'].head(10):
#     text = "\n\n".join(issue_comments)  # Double newline helps mark boundaries
#     tt = texttiling.TextTilingTokenizer()
#     segments = tt.tokenize(text)
#     print(segments)


# -------------------------------------------------------------------------------------------------------------------------------------
# ATTEMPT AT TOPIC SEGMENTATION USING CVS ALGORITHM, GREEDY SPLITTING (A. ALEMI, 2015)- NOT WORKING, SPLITS EVERY SENTENCE AS OWN TOPIC
# wrdvec_path = 'models/wrdvecs.bin'
# model = KeyedVectors.load_word2vec_format(wrdvec_path, binary=True)
# wrdvecs = pd.DataFrame(model.vectors, index=model.index_to_key)
# del model
# segment_len = 30  # segment target length in sentences

# segments = []
# for issue_comments in df['processed_issue_comments'].head(10):
#     vecr = CountVectorizer(vocabulary=wrdvecs.index)

#     comment_vectors = vecr.transform(issue_comments).dot(wrdvecs)
#     # print([comment_vectors][0].shape[0])

#     # penalty = get_penalty([comment_vectors], segment_len)

#     # optimal_segmentation = split_optimal(comment_vectors, penalty)
#     # segmented_text = get_segments(issue_comments, optimal_segmentation)
#     greedy_segmentation = split_greedy(comment_vectors, max_splits=5)
#     segmented_text = get_segments(issue_comments, greedy_segmentation)
#     segments.append(segmented_text)

# print(segments[5])


# ATTEMPT AT TOPIC SEGMENTATION USING CVS ALGORITHM, OPTIMAL SPLITTING (A. ALEMI, 2015)- NOT WORKING, DOCUMENTS TOO SHORT
# segments = []
# for issue_comments in df['processed_issue_comments'].head(100):
#     vecr = CountVectorizer(vocabulary=wrdvecs.index)

#     comment_vectors = vecr.transform(issue_comments).dot(wrdvecs)
#     print([comment_vectors][0].shape[0])

#     penalty = get_penalty([comment_vectors], segment_len)

#     optimal_segmentation = split_optimal(comment_vectors, penalty)
#     segmented_text = get_segments(issue_comments, optimal_segmentation)
#     segments.append(segmented_text)

# df['issue_comments_segmented'] = segments
# print(df.head(1)['processed_issue_comments'])

# -------------------------------------------------------------------------------------------
# ATTEMPT AT TOPIC SEGMENTING USING COSINE SIMILARITY WITH PREVIOUS COMMENT- NOT WORKING WELL
# def segment_issue_comments(issue_comments, model):
#     comment_embeddings = model.encode(issue_comments)

#     segments = []
#     current_segment = [issue_comments[0]]

#     for i in range(1, len(issue_comments)):
#         # compare current comment with previous comment
#         similarity = cosine_similarity([comment_embeddings[i]], [comment_embeddings[i-1]])[0][0]
        
#         if similarity < 0.5:  # can adjust threshold if needed
#             # comment is dissimilar from previous- start new segment
#             segments.append("\n".join(current_segment))
#             current_segment = []
#         current_segment.append(issue_comments[i])

#     # add last segment
#     segments.append("\n".join(current_segment))
#     return segments

# model = SentenceTransformer('all-MiniLM-L6-v2')
# df['segmented_issue_comments'] = df['processed_issue_comments'].head(100).apply(lambda x: segment_issue_comments(x, model))
