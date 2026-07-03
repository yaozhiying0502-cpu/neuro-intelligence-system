import os
import requests
import time

# =========================
# ENV
# =========================
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
# 1. PUBMED SEARCH
# =========================
def fetch_pubmed():

    try:
        url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"

        r = requests.get(url, params={
            "db": "pubmed",
            "term": "(Alzheimer OR MS OR microglia OR neuroinflammation OR aging)",
            "retmax": 5,
            "retmode": "json"
        }, timeout=10)

        data = r.json()
        ids = data.get("esearchresult", {}).get("idlist", [])

        print("PUBMED IDS:", ids)

        return ids

    except Exception as e:
        print("❌ PubMed error:", e)
        return []

# =========================
# 2. PAPER DETAILS
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
            "journal": j.get("source", ""),
            "affiliation": j.get("elocationid", "")  # fallback field
        }

    except Exception as e:
        print("❌ paper error:", e)
        return None

# =========================
# 3. PI ENRICHMENT
# =========================
def enrich_pi(name, paper):

    institution = "unknown"
    email = "unknown"

    aff = paper.get("affiliation", "")

    if aff:
        institution = aff

    # heuristic cleaning
    if institution != "unknown":
        institution = institution.split(";")[0]

    if institution != "unknown":
        domain = institution.lower().replace(" ", "").replace(",", "")
        email = f"{name.split()[-1].lower()}@{domain}.edu"

    return institution, email

# =========================
# 4. PI EXTRACTION
# =========================
def extract_pi(paper):

    authors = paper.get("authors", [])

    if not authors:
        return []

    pis = []

    last_author = authors[-1].get("name", "")

    institution, email = enrich_pi(last_author, paper)

    pis.append({
        "name": last_author,
        "institution": institution,
        "email": email,
        "paper": paper["title"],
        "journal": paper.get("journal", "")
    })

    return pis

# =========================
# 5. PI SCORING SYSTEM
# =========================
def score_pi(pi):

    score = 0

    text = (pi.get("paper","") + pi.get("journal","")).lower()

    # disease relevance
    if "alzheimer" in text:
        score += 30
    if "multiple sclerosis" in text:
        score += 30
    if "microglia" in text:
        score += 25
    if "neuroinflammation" in text:
        score += 25
    if "aging" in text:
        score += 15

    # institution quality
    inst = pi.get("institution","").lower()

    if "harvard" in inst:
        score += 25
    if "stanford" in inst:
        score += 25
    if "ucl" in inst:
        score += 15
    if "university" in inst:
        score += 10

    # email availability bonus
    if pi.get("email") != "unknown":
        score += 10

    return min(score, 100)

# =========================
# 6. CRITIQUE ENGINE
# =========================
def critique(paper):

    return f"""
Key Idea:
{paper['title']}

Strength:
- neuroimmunology relevance high
- translational potential exists

Limitation:
- model validation unclear
- sample size likely small

Follow-up questions:
- how does this relate to AD-MS comorbidity?
- is microglia activation causal or correlative?
"""

# =========================
# 7. OUTREACH EMAIL GENERATOR
# =========================
def generate_email(pi, paper):

    return f"""
Dear Dr. {pi['name']},

I recently read your work:
"{paper['title']}"

I found your study particularly interesting in the context of
neuroimmune mechanisms in Alzheimer’s disease and multiple sclerosis.

One question I had:
How do you distinguish aging-related microglial activation from disease-driven inflammation?

I would be very grateful for the opportunity to discuss your work further.

Best regards,
"""

# =========================
# 8. NOTION PUSH (SAFE)
# =========================
def push(db, props):

    try:
        url = "https://api.notion.com/v1/pages"

        r = requests.post(url, headers=HEADERS, json={
            "parent": {"database_id": db},
            "properties": props
        })

        print("NOTION STATUS:", r.status_code)
        print("NOTION RESPONSE:", r.text)

        return r.status_code == 200

    except Exception as e:
        print("❌ Notion error:", e)
        return False

# =========================
# 9. RANK PI LIST
# =========================
def rank_pis(pis):

    for p in pis:
        p["score"] = score_pi(p)

    return sorted(pis, key=lambda x: x["score"], reverse=True)

# =========================
# 10. MAIN PIPELINE
# =========================
def main():

    print("🚀 v5 FULL START")

    ids = fetch_pubmed()

    all_pis = []

    for pid in ids:

        paper = fetch_details(pid)

        if not paper:
            continue

        # =====================
        # WRITE PAPER
        # =====================
        push(DAILY_DB, {
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
        # PI PROCESSING
        # =====================
        pis = extract_pi(paper)

        for pi in pis:

            pi["score"] = score_pi(pi)
            all_pis.append(pi)

            push(PI_DB, {
                "PI Name": {
                    "title": [{"text": {"content": pi["name"]}}]
                },
                "Email": {
                    "rich_text": [{"text": {"content": pi["email"]}}]
                },
                "Institution": {
                    "rich_text": [{"text": {"content": pi["institution"]}}]
                },
                "Field": {
                    "rich_text": [{"text": {"content": pi["paper"]}}]
                }
            })

            # OPTIONAL: outreach draft
            email = generate_email(pi, paper)

            push(OUTREACH_DB, {
                "PI Name": {
                    "title": [{"text": {"content": pi["name"]}}]
                },
                "Email Draft": {
                    "rich_text": [{"text": {"content": email}}]
                },
                "Status": {
                    "rich_text": [{"text": {"content": "draft"}}]
                }
            })

        time.sleep(0.5)

    # =====================
    # RANKING OUTPUT
    # =====================
    ranked = rank_pis(all_pis)

    print("\n🔥 TOP PIs TODAY")

    for p in ranked[:5]:
        print(p["name"], p["score"], p["institution"])

    print("✅ v5 FULL DONE")

if __name__ == "__main__":
    main()
