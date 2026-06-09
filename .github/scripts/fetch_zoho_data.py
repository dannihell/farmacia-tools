import requests
import json
import os
from datetime import datetime

REFRESH_TOKEN = os.environ["ZOHO_REFRESH_TOKEN"]
CLIENT_ID = os.environ["ZOHO_CLIENT_ID"]
CLIENT_SECRET = os.environ["ZOHO_CLIENT_SECRET"]
WORKSPACE_ID = "1135564000002838003"
API_BASE = "https://analyticsapi.zoho.com/api/v2"

def get_access_token():
    response = requests.post(
        "https://accounts.zoho.com/oauth/v2/token",
        data={
            "refresh_token": REFRESH_TOKEN,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
        }
    )
    data = response.json()
    if "access_token" not in data:
        raise Exception(f"Erro ao obter token: {data}")
    print(f"✓ Access token obtido")
    return data["access_token"]

def query_zoho(token, sql):
    response = requests.post(
        f"{API_BASE}/workspaces/{WORKSPACE_ID}/views/data",
        params={"sqlQuery": sql},
        headers={
            "Authorization": f"Zoho-oauthtoken {token}",
            "ZANALYTICS-ORGID": "20085290558"
        }
    )
    print(f"HTTP Status: {response.status_code}")
    print(f"Response: {response.text[:2000]}")
    data = response.json()
    if data.get("status") != "success":
        raise Exception(f"Erro na query: {data}")
    return data["data"]

def main():
    print(f"🚀 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    token = get_access_token()
    print("📊 Teste LIMIT 5...")
    sql = 'SELECT "COD_PRD", "DESIGNACAO" FROM "AROEIRA_BRAND_ANALYSIS" LIMIT 5'
    query_zoho(token, sql)
    print("✅ OK!")

if __name__ == "__main__":
    main()
