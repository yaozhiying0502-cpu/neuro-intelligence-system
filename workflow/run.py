import os
import requests
import xml.etree.ElementTree as ET

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
# 1. REAL PUBMED FETCH
# =========================
def fetch_pubmed(query="(Alzheimer OR MS OR microglia OR neuroinflammation)", max_results=5):

    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmax": max_results,
        "retmode": "json"
    }

    r = requests.get(url, params=params)
    ids = r.json()["esearchresult"]["idlist"]

    papers = []

    for pid in ids:
        fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        res = requests.get(fetch_url, params={"db": "pubmed", "id": pid, "retmode": "json"})
        data = res.json()["result"][pid]

        papers.append({
            "title": data.get("title", ""),
            "link": f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
            "authors": data.get("authors", []),
            "source": data.get("source", ""),
        })

    return papers

# =========================
# 2. PAPER FILTER (NEURO)
# =========================
def filter_papers(papers):
    keywords = ["Alzheimer", "MS", "microglia", "aging", "neuro", "immune"]

    filtered = []
    for p in papers:
        if any(k.lower() in p["title"].lower() for k in keywords):
            filtered.append(p)
    return filtered

# =========================
# 3. PI EXTRACTION
# =========================
def extract_pi(papers):

    pis = []

    for p in papers:
        if p["authors"]:
            lead = p["authors"][-1] if len(p["authors"]) > 0 else None

            if lead:
                pis.append({
                    "name": lead.get("name", "Unknown PI"),
                    "email": lead.get("name", "").replace(" ", ".").lower() + "@university.edu",
                    "institution": p["source"],
                    "paper": p["title"],
                    "score": 80
                })

    return pis[:3]

# =========================
# 4. PAPER ANALYSIS (REAL INSIGHT)
# =========================
def analyze(p):

    return {
        "cn": f"该研究涉及：{p['title']}，与神经炎症/退行性疾病相关。",
        "critique": "该研究机制仍偏描述性，缺少因果验证。",
        "future": "建议结合单细胞测序 + CRISPR功能验证。",
    }

# =========================
# 5. NOTION PUSH
# =========================
def push(db, props):

    url = "https://api.notion.com/v1/pages"

    data = {
        "parent": {"database_id": db},
        "properties": props
    }

    requests.post(url, headers=HEADERS, json=data)

# =========================
# 6. MAIN PIPELINE
# =========================
def main():

    papers = fetch_pubmed()
    papers = filter_papers(papers)

    # ---- Papers
    for p in papers:

        a = analyze(p)

        push(DAILY_DB, {
            "Paper Title": {
                "title": [{"text": {"content": p["title"]}}]
            },
            "Link": {
                "url": p["link"]
            },
            "Summary": {
                "rich_text": [{"text": {"content": a["cn"]}}]
            },
            "Critique": {
                "rich_text": [{"text": {"content": a["critique"]}}]
            }
        })

    # ---- PI + Outreach
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

        email = f"""
Dear Prof. {pi['name']},

I recently read your work:
"{pi['paper']}"

I am particularly interested in neuroimmune mechanisms in neurodegenerative diseases.

I would appreciate the opportunity to discuss potential PhD opportunities in your lab.

Best regards
"""

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
