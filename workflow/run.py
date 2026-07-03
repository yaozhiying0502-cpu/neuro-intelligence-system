import os
import requests

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
# 1. REAL PAPER FETCH (PubMed mock v2)
# =========================
def fetch_papers():
    # 后面可以换成 Entrez API / bioRxiv API
    return [
        {
            "title": "Microglial dysfunction in Alzheimer’s disease progression",
            "cn_title": "阿尔茨海默病进展中的小胶质细胞功能障碍",
            "link": "https://pubmed.ncbi.nlm.nih.gov/000000/",
            "summary": "Microglia regulate synaptic pruning and neuroinflammation in AD."
        },
        {
            "title": "Immune dysregulation in multiple sclerosis",
            "cn_title": "多发性硬化中的免疫失调",
            "link": "https://pubmed.ncbi.nlm.nih.gov/000001/",
            "summary": "T cell and microglia interaction drives demyelination."
        }
    ]

# =========================
# 2. PI EXTRACTION (mock intelligent layer)
# =========================
def extract_pis(papers):
    return [
        {
            "name": "Dr. Example Neuro",
            "institution": "Harvard Medical School",
            "email": "example@harvard.edu",
            "score": 88,
            "reason": "Microglia + AD + neuroinflammation match",
            "papers": papers
        }
    ]

# =========================
# 3. PAPER ANALYSIS (CN + critique)
# =========================
def analyze_paper(p):
    return {
        "summary_cn": f"该研究揭示{p['cn_title']}的重要机制。",
        "critique": "样本量有限，机制链条仍不完整。",
        "insight": "可结合单细胞RNA-seq进一步验证细胞亚群变化。",
        "future": "建议探索微胶质细胞与APOE4的交互机制。"
    }

# =========================
# 4. NOTION PUSH
# =========================
def push(db, properties):
    url = "https://api.notion.com/v1/pages"

    data = {
        "parent": {"database_id": db},
        "properties": properties
    }

    requests.post(url, headers=HEADERS, json=data)

# =========================
# 5. MAIN LOOP
# =========================
def main():

    papers = fetch_papers()

    # ---- papers to Notion
    for p in papers:
        a = analyze_paper(p)

        push(DAILY_DB, {
            "Paper Title": {
                "title": [{"text": {"content": p["title"]}}]
            },
            "CN Title": {
                "rich_text": [{"text": {"content": p["cn_title"]}}]
            },
            "Link": {
                "url": p["link"]
            },
            "Summary": {
                "rich_text": [{"text": {"content": a["summary_cn"]}}]
            }
        })

    # ---- PI generation
    pis = extract_pis(papers)

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

        # ---- auto email draft
        email = f"""
Dear {pi['name']},

I am very interested in your work on neuroimmunology and microglial dysfunction...

I recently read your studies related to:
{pi['reason']}

I would appreciate the opportunity to discuss potential PhD opportunities.

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
