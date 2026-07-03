import os
import requests
from collections import defaultdict

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DAILY_DB = os.environ["DAILY_DB"]
PI_DB = os.environ["PI_DB"]
OUTREACH_DB = os.environ["OUTREACH_DB"]

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# =========================
# 1. REAL PAPER FETCH (PubMed)
# =========================
def fetch_papers():

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    params = {
        "db": "pubmed",
        "term": "(Alzheimer OR MS OR microglia OR neuroinflammation OR aging)",
        "retmax": 8,
        "retmode": "json"
    }

    r = requests.get(url, params=params)
    ids = r.json()["esearchresult"]["idlist"]

    papers = []

    for pid in ids:

        url2 = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        r2 = requests.get(url2, params={"db": "pubmed", "id": pid, "retmode": "json"})

        data = r2.json()["result"][pid]

        papers.append({
            "id": pid,
            "title": data.get("title", ""),
            "journal": data.get("source", ""),
            "link": f"https://pubmed.ncbi.nlm.nih.gov/{pid}/"
        })

    return papers

# =========================
# 2. PAPER SCORING ENGINE (v4核心)
# =========================
def score_paper(p):

    score = 0
    t = p["title"].lower()

    # disease relevance
    if "alzheimer" in t: score += 30
    if "multiple sclerosis" in t or "ms" in t: score += 30
    if "microglia" in t: score += 25
    if "neuroinflammation" in t: score += 25
    if "aging" in t: score += 20

    # journal proxy
    if "nature" in p["journal"].lower(): score += 20
    if "cell" in p["journal"].lower(): score += 20
    if "science" in p["journal"].lower(): score += 20

    return min(score, 100)

# =========================
# 3. TOPIC CLUSTERING
# =========================
def cluster(papers):

    clusters = defaultdict(list)

    for p in papers:
        t = p["title"].lower()

        if "alzheimer" in t:
            clusters["AD"].append(p)
        elif "multiple sclerosis" in t or "ms" in t:
            clusters["MS"].append(p)
        elif "aging" in t:
            clusters["Aging"].append(p)
        else:
            clusters["Neuroimmune"].append(p)

    return clusters

# =========================
# 4. PI EXTRACTION (v4 improved)
# =========================
def extract_pi(papers):

    pis = []

    for p in papers:

        # mock improved PI detection (v5可升级真实corresponding author)
        pi = {
            "name": "Lab of " + p["title"].split(" ")[0],
            "institution": p["journal"],
            "email": "lab@university.edu",
            "score": score_paper(p),
            "paper": p["title"]
        }

        pis.append(pi)

    return sorted(pis, key=lambda x: x["score"], reverse=True)[:3]

# =========================
# 5. NOTION PUSH
# =========================
def push(db, props):

    url = "https://api.notion.com/v1/pages"

    requests.post(url, headers=HEADERS, json={
        "parent": {"database_id": db},
        "properties": props
    })

# =========================
# 6. STRATEGY EMAIL ENGINE (v4核心)
# =========================
def generate_email(pi):

    if pi["score"] > 70:
        angle = "I am particularly interested in your recent high-impact work on neuroimmune mechanisms."
    else:
        angle = "I am interested in your research direction in neurobiology."

    return f"""
Dear Professor,

I recently read your paper: "{pi['paper']}"

{angle}

I would be very interested in discussing potential PhD opportunities in your lab.

Best regards
"""

# =========================
# 7. MAIN ENGINE
# =========================
def main():

    papers = fetch_papers()

    # scoring
    for p in papers:
        p["score"] = score_paper(p)

        push(DAILY_DB, {
            "Paper Title": {
                "title": [{"text": {"content": p["title"]}}]
            },
            "Link": {"url": p["link"]},
            "Summary": {
                "rich_text": [{"text": {"content": f"Relevance score: {p['score']}"}}]
            }
        })

    # clustering
    clusters = cluster(papers)

    # PI
    pis = extract_pi(papers)

    for pi in pis:

        push(PI_DB, {
            "PI Name": {
                "title": [{"text": {"content": pi["name"]}}]
            },
            "Institution": {
                "rich_text": [{"text": {"content": pi["institution"]}}]
            },
            "Email": {
                "rich_text": [{"text": {"content": pi["email"]}}]
            },
            "Match Score": {
                "number": pi["score"]
            }
        })

        email = generate_email(pi)

        push(OUTREACH_DB, {
            "PI Name": {
                "title": [{"text": {"content": pi["name"]}}]
            },
            "Email Draft": {
                "rich_text": [{"text": {"content": email}}]
            }
        })

if __name__ == "__main__":
    main()
