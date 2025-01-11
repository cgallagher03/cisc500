Setup:

1. Create a virtual environment into a folder called '.venv', and install required dependencies:
    Run `python -m venv .venv` to create venv
    Run `source .venv/bin/activate` to active venv
    Run `pip install -r requirements.txt` to install required packages  

2. Create a '.env' file, containing at least a key GITHUB_PAT_1 and value corresponding to your Github personal access token
e.g. GITHUB_PAT_1="my_access_token"
and also a key GITHUB_PATS which will be a comma-separated list of access token(s) (using multiple will assist with rate limits, but not compulsory)
e.g. GITHUB_PATS="my_token_1,my_token_2"

3. Usage:
   --> Run `python scrape_all_prs.py` to get all pull requests (can take multiple hours)
   --> Run `python scrape_pr_checkbox_data.py` to get associated checked boxes for each pull request (can take multiple hours)
   --> Run `python filter_prs.py` to filter down to integration related PRs
   --> Run `python scrape_pr_comment_data` to get ordered dialogue of PR comments
   --> Run `python scrape_pr_file_data` to get LOC changed of PRs

N.B: If additional packages are installed from pip, update requirements.txt file by running `pip3 freeze > requirements.txt`   