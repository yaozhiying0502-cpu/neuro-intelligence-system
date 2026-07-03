import os
import requests
import time

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
# 1. PUBMED FETCH (SAFE)
# =========================
def fetch_pubmed():

    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

    try:
        r = requests.get(url, params={
            "db": "pubmed",
            "term": "(Alzheimer OR MS OR microglia OR neuroinflammation OR aging)",
            "retmax": 5,
            "retmode": "json"
        }, timeout=10)

        data = r.json()
        ids = data.get("esearchresult", {}).get("idlist", [])

        if not ids:
            print("⚠️ No PubMed results")
            return []

        return ids

    except Exception as e:
        print("❌ PubMed error:", e)
        return []

# =========================
# 2. GET PAPER DETAILS
# =========================
def fetch_details(pid):

    try:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

        r = requests.get(url, params={
            "db": "pubmed",
            "id": pid,
            "retmode": "json"
        }, timeout=10)

        j = r.json().get("result", {}).get(pid, {})

        return {
            "title": j.get("title", "No title"),
            "link": f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
            "authors": j.get("authors", []),
            "journal": j.get("source", "")
        }

    except Exception as e:
        print("paper error:", e)
        return None

# =========================
# 3. PI EXTRACTION (FIXED v4.2)
# =========================
def extract_pi(paper):

    pis = []

    try:
        authors = paper.get("authors", [])

        for a in authors:

            name = a.get("name", "")

            # heuristic: last author = PI candidate
            if name and (len(name.split()) > 0):

                pis.append({
                    "name": name,
                    "email": "unknown",
                    "institution": "unknown",
                    "paper": paper["title"]
                })

        # keep only last author as PI (common academic rule)
        if pis:
            return [pis[-1]]

        return []

    except Exception as e:
        print("PI extract error:", e)
        return []

# =========================
# 4. NOTION SAFE WRITE (CRITICAL FIX)
# =========================
def notion_write(db, props):

    url = "https://api.notion.com/v1/pages"

    try:
        r = requests.post(url, headers=HEADERS, json={
            "parent": {"database_id": db},
            "properties": props
        })

        print("NOTION STATUS:", r.status_code)
        print("NOTION RESPONSE:", r.text)

        # 🔥 critical fix
        if r.status_code != 200:
            print("❌ Notion write failed")
            return False

        return True

    except Exception as e:
        print("❌ Notion exception:", e)
        return False

# =========================
# 5. MAIN PIPELINE (v4.2)
# =========================
def main():

    print("🚀 v4.2 running...")

    ids = fetch_pubmed()

    if not ids:
        print("❌ no ids")
        return

    all_papers = []

    for pid in ids:

        paper = fetch_details(pid)

        if not paper:
            continue

        all_papers.append(paper)

        # =====================
        # WRITE PAPER
        # =====================
        success = notion_write(DAILY_DB, {
            "Paper Title": {
                "title": [{"text": {"content": paper["title"]}}]
            },
            "Link": {
                "url": paper["link"]
            },
            "Summary": {
                "rich_text": [{"text": {"content": paper["journal"]}}]
            }
        })

        # =====================
        # EXTRACT PI
        # =====================
        pis = extract_pi(paper)

        print("PI FOUND:", len(pis))

        for pi in pis:

            notion_write(PI_DB, {
                "PI Name": {
                    "title": [{"text": {"content": pi["name"]}}]
                },
                "Email": {
                    "rich_text": [{"text": {"content": pi["email"]}}]
                },
                "Field": {
                    "rich_text": [{"text": {"content": pi["paper"]}}]
                }
            })

        time.sleep(0.5)

    print("✅ v4.2 done")

if __name__ == "__main__":
    main()
