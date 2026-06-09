import requests
import json
import os
from datetime import datetime

REFRESH_TOKEN = os.environ["ZOHO_REFRESH_TOKEN"]
CLIENT_ID = os.environ["ZOHO_CLIENT_ID"]
CLIENT_SECRET = os.environ["ZOHO_CLIENT_SECRET"]
WORKSPACE_ID = "1135564000002838003"
ORG_ID = "67632106"
API_BASE = "https://analyticsapi.zoho.com/restapi/v2"

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
    config = {"sqlQuery": sql, "responseFormat": "json"}
    r = requests.get(f"{API_BASE}/bulk/workspaces/{WORKSPACE_ID}/data",
        params={"CONFIG": json.dumps(config)},
        headers={"Authorization": f"Zoho-oauthtoken {token}", "ZANALYTICS-ORGID": ORG_ID})
    d = r.json()
    if d.get("status") != "success":
        raise Exception(f"Query error: {d}")
    return d["data"]

def build_brand_sql():
    now = datetime.now()
    year, month = now.year, now.month
    months = []
    for i in range(7):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        months.append((y, m))
    cases = ", ".join([f"SUM(CASE WHEN ANO = {y} AND MES = {m} THEN QT ELSE 0 END) AS V{i}" for i, (y, m) in enumerate(months)])
    return f"""SELECT COD_PRD, DESIGNACAO, ENT_RESP_COMERC, MARCA, STK_FARMACIA, PCUSMED_PROD, DUV, CATEGORIA_DESIGNACAO, MERCADO_DESIGNACAO, SUM(QT) AS TOTAL_QT, {cases}, SUM(CASE WHEN ANO = {year} THEN VALOR_VENDA ELSE 0 END) AS VENDAS_YTD, SUM(CASE WHEN ANO = {year} THEN MARGEM_EUROS ELSE 0 END) AS MARGEM_YTD, SUM(VALOR_QUEBRA) AS VALOR_QUEBRAS FROM AROEIRA_BRAND_ANALYSIS GROUP BY COD_PRD, DESIGNACAO, ENT_RESP_COMERC, MARCA, STK_FARMACIA, PCUSMED_PROD, DUV, CATEGORIA_DESIGNACAO, MERCADO_DESIGNACAO ORDER BY SUM(QT) DESC"""

def main():
    print(f"🚀 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    token = get_access_token()
    os.makedirs("data", exist_ok=True)

    print("📊 A carregar AROEIRA_BRAND_ANALYSIS...")
    brand_data = query_zoho(token, build_brand_sql())
    columns = [c.strip() for c in brand_data["columns"]]
    produtos = [dict(zip(columns, row)) for row in brand_data["rows"]]
    print(f"✓ {len(produtos)} produtos carregados")

    print("🏭 A carregar laboratórios...")
    lab_data = query_zoho(token, "SELECT DISTINCT ENT_RESP_COMERC, MARCA FROM AROEIRA_BRAND_ANALYSIS WHERE ENT_RESP_COMERC IS NOT NULL ORDER BY ENT_RESP_COMERC")
    lab_columns = [c.strip() for c in lab_data["columns"]]
    laboratorios = [dict(zip(lab_columns, row)) for row in lab_data["rows"]]
    print(f"✓ {len(laboratorios)} laboratórios carregados")

    output = {"updated_at": datetime.now().isoformat(), "produtos": produtos,
              "laboratorios": laboratorios, "total_produtos": len(produtos)}

    with open("data/aroeira_brand.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ data/aroeira_brand.json guardado ({len(produtos)} produtos)")

if __name__ == "__main__":
    main()
