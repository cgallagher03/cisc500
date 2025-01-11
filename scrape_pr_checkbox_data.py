import csv
import requests
from bs4 import BeautifulSoup
import os

buffer = []  # Buffer for batching PR data
BATCH_SIZE = 100  # Save every x PRs

# Save buffered data to CSV
def save_buffered_data():
    print("Checkpoint reached")
    mode = ""
    if buffer:
        if os.path.exists("data/pull_requests_all_with_checkbox_data.csv"):
            mode = "a"  
            print("Found existing file.")
        else:
            mode = "w"
        with open("data/pull_requests_all_with_checkbox_data.csv", mode, newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            if mode == "w":
                writer.writerow(["PR Number", "Title", "Author", "Integration", "Created At", "Updated At", "State", 
                                 "Files Changed", "Decision Time", "Closed Date", "URL", "Type of Change"])
            writer.writerows(buffer)  # Write all buffered rows at once
        buffer.clear()  # Clear buffer after writing

# Scrape type of change checkboxes from PR HTML
def get_pr_checkbox_data(pr_html_url):
    response = requests.get(pr_html_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        type_of_change_section = soup.find('ul', class_='contains-task-list')
        if not type_of_change_section:
            return None

        checked_items = []
        for li in type_of_change_section.find_all('li'):
            checkbox = li.find('input', {'type': 'checkbox'})
            label = li.text.strip()
            if checkbox and checkbox.has_attr('checked'):
                checked_items.append(label)

        return ", ".join(checked_items) if checked_items else None
    else:
        print(f"Failed to retrieve {pr_html_url}. Status code: {response.status_code}")
        return None


# Load last PR number from output CSV if it exists, otherwise fallback to progress file
def get_last_processed_pr():
    last_pr = None
    if os.path.exists("data/pull_requests_all_with_checkbox_data.csv"):
        with open("data/pull_requests_all_with_checkbox_data.csv", mode="r", encoding="utf-8") as f:
            last_row = list(csv.reader(f))[-1]
            last_pr = int(last_row[0])
    return last_pr


# Process PRs and add checkbox data
def add_checkbox_data():
    last_processed_pr = get_last_processed_pr()
    
    # Read the CSV into a list and sort in descending order of PR numbers
    with open("data/pull_requests_all.csv", mode="r", encoding="utf-8") as infile:
        reader = list(csv.DictReader(infile))
        reader.sort(key=lambda row: int(row["PR Number"]), reverse=True)

    for row in reader:
        pr_number = int(row["PR Number"])

        # Skip PRs we've already processed
        if last_processed_pr and pr_number >= last_processed_pr:
            continue

        # Collect PR data and checkbox data
        try:
            type_of_change = get_pr_checkbox_data(row["URL"])
            pr_data = [
                pr_number,
                row["Title"],
                row["Author"],
                row["Integration"],
                row["Created At"],
                row["Updated At"],
                row["State"],
                row["Files Changed"],
                row["Decision Time"],
                row["Closed Date"],
                row["URL"],
                type_of_change,
            ]
            buffer.append(pr_data)  # Add PR data to buffer

            # Save buffer if it reaches the BATCH_SIZE
            if len(buffer) >= BATCH_SIZE:
                save_buffered_data()

        
        except Exception as e:
            print(f"Error occurred: {e}")
            save_buffered_data()


    # Final save after all processing
    save_buffered_data()

if __name__ == "__main__":
    print("Starting Part 2: Adding checkbox data to PR metadata...")
    add_checkbox_data()
    print("Checkbox data added. Results saved to data/pull_requests_all_with_checkbox_data.csv.")
