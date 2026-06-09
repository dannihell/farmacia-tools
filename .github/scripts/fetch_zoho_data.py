import requests, os
from datetime import datetime

REFRESH_TOKEN = os.environ["ZOHO_REFRESH_TOKEN"]
CLIENT_ID = os.environ["ZOHO_CLIENT_ID"]
CLIENT_SECRET = os.environ["ZOHO_CLIENT_SECRET"]
WORKSPACE_ID = "1135564000002838003"
API_BASE = "https://analyticsapi.zoho.com/api/v2"

def get_access_token():
    r = requests.post("https://accounts.zoho.com/oauth/v2/token", data={
        "refresh_token": REFRESH_TOKEN, "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET, "grant_type": "refresh_token"})
    d = r.json()
    if "access_token" not in d:
        raise Exception(f"Token error: {d}")
    print("Access token OK")
    return d["access_token"]

def main():
    print(datetime.now().strftime("%Y-%m-%d %H:%M"))
    token = get_access_token()
    sql = "SELECT COD_PRD, DESIGNACAO FROM AROEIRA_BRAND_ANALYSIS LIMIT 5"
    r = requests.post(f"{API_BASE}/workspaces/{WORKSPACE_ID}/views/data",
        params={"sqlQuery": sql},
        headers={"Authorization": f"Zoho-oauthtoken {token}", "ZANALYTICS-ORGID": "20085290558"})
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text[:2000]}")

if __name__ == "__main__":
    main()
