import os
import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DAILY_DB = os.environ["DAILY_DB"]

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def push():
    url = "https://api.notion.com/v1/pages"

    data = {
        "parent": {"database_id": DAILY_DB},
        "properties": {
            "Paper Title": {
                "title": [{"text": {"content": "Test Paper from Codex"}}]
            }
        }
    }

    r = requests.post(url, headers=HEADERS, json=data)
    print(r.status_code, r.text)

if __name__ == "__main__":
    push()
