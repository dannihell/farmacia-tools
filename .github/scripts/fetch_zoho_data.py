import requests, json, os
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
    print("✓ Access token obtido")
    return d["access_token"]

def query_zoho(token, sql):
    r = requests.post(
        f"{API_BASE}/workspaces/{WORKSPACE_ID}/views/AROEIRA_BRAND_ANALYSIS/data",
        data={"sqlQuery": sql, "responseFormat": "json"},
        headers={"Authorization": f"Zoho-oauthtoken {token}",
                 "ZANALYTICS-ORGID": "67632106"})
    print(f"Status: {r.status_code}, Length: {len(r.text)}")
    print(f"Body[:300]: {r.text[:300]}")
    d = r.json()
    if d.get("status") != "success":
        raise Exception(f"Query error: {d}")
    return d["data"]

def main():
    print(datetime.now().strftime("%Y-%m-%d %H:%M"))
    token = get_access_token()
    print("📊 Query com endpoint correcto...")
    sql = "SELECT COD_PRD, DESIGNACAO, ENT_RESP_COMERC, STK_FARMACIA FROM AROEIRA_BRAND_ANALYSIS LIMIT 10"
    data = query_zoho(token, sql)
    print(f"✓ {data}")
    os.makedirs("data", exist_ok=True)
    with open("data/aroeira_brand.json", "w") as f:
        json.dump({"updated_at": datetime.now().isoformat(), "data": data}, f)
    print("✅ Guardado!")

if __name__ == "__main__":
    main()
