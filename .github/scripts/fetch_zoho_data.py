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
    response = requests.post(
        "https://accounts.zoho.com/oauth/v2/token",
        data={"refresh_token": REFRESH_TOKEN, "client_id": CLIENT_ID,
              "client_secret": CLIENT_SECRET, "grant_type": "refresh_token"})
    data = response.json()
    if "access_token" not in data:
        raise Exception(f"Erro ao obter token: {data}")
    print(f"✓ Access token obtido")
    return data["access_token"]

def query_zoho(token, sql):
    config = {"sqlQuery": sql, "responseFormat": "json"}
    response = requests.get(
        f"{API_BASE}/bulk/workspaces/{WORKSPACE_ID}/data",
        params={"CONFIG": json.dumps(config)},
        headers={"Authorization": f"Zoho-oauthtoken {token}", "ZANALYTICS-ORGID": ORG_ID})
    data = response.json()
    if data.get("status") != "success":
        raise Exception(f"Erro na query: {data}")
    return data["data"]

def fetch_brand_analysis(token):
    sql = """SELECT COD_PRD, DESIGNACAO, ENT_RESP_COMERC, MARCA, STK_FARMACIA, PCUSMED_PROD, DUV, CATEGORIA_DESIGNACAO, MERCADO_DESIGNACAO, SUM(QT) AS TOTAL_QT, SUM(CASE WHEN MES = EXTRACT(MONTH FROM CURRENT_DATE) AND ANO = EXTRACT(YEAR FROM CURRENT_DATE) THEN QT ELSE 0 END) AS V0, SUM(CASE WHEN (ANO * 12 + MES) = (EXTRACT(YEAR FROM CURRENT_DATE) * 12 + EXTRACT(MONTH FROM CURRENT_DATE) - 1) THEN QT ELSE 0 END) AS V1, SUM(CASE WHEN (ANO * 12 + MES) = (EXTRACT(YEAR FROM CURRENT_DATE) * 12 + EXTRACT(MONTH FROM CURRENT_DATE) - 2) THEN QT ELSE 0 END) AS V2, SUM(CASE WHEN (ANO * 12 + MES) = (EXTRACT(YEAR FROM CURRENT_DATE) * 12 + EXTRACT(MONTH FROM CURRENT_DATE) - 3) THEN QT ELSE 0 END) AS V3, SUM(CASE WHEN (ANO * 12 + MES) = (EXTRACT(YEAR FROM CURRENT_DATE) * 12 + EXTRACT(MONTH FROM CURRENT_DATE) - 4) THEN QT ELSE 0 END) AS V4, SUM(CASE WHEN (ANO * 12 + MES) = (EXTRACT(YEAR FROM CURRENT_DATE) * 12 + EXTRACT(MONTH FROM CURRENT_DATE) - 5) THEN QT ELSE 0 END) AS V5, SUM(CASE WHEN (ANO * 12 + MES) = (EXTRACT(YEAR FROM CURRENT_DATE) * 12 + EXTRACT(MONTH FROM CURRENT_DATE) - 6) THEN QT ELSE 0 END) AS V6, SUM(CASE WHEN ANO = EXTRACT(YEAR FROM CURRENT_DATE) THEN VALOR_VENDA ELSE 0 END) AS VENDAS_YTD, SUM(CASE WHEN ANO = EXTRACT(YEAR FROM CURRENT_DATE) THEN MARGEM_EUROS ELSE 0 END) AS MARGEM_YTD, SUM(VALOR_QUEBRA) AS VALOR_QUEBRAS FROM AROEIRA_BRAND_ANALYSIS GROUP BY COD_PRD, DESIGNACAO, ENT_RESP_COMERC, MARCA, STK_FARMACIA, PCUSMED_PROD, DUV, CATEGORIA_DESIGNACAO, MERCADO_DESIGNACAO ORDER BY SUM(QT) DESC"""
    return query_zoho(token, sql)

def fetch_laboratorios(token):
    sql = "SELECT DISTINCT ENT_RESP_COMERC, MARCA FROM AROEIRA_BRAND_ANALYSIS WHERE ENT_RESP_COMERC IS NOT NULL ORDER BY ENT_RESP_COMERC"
    return query_zoho(token, sql)

def main():
    print(f"🚀 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    token = get_access_token()
    os.makedirs("data", exist_ok=True)

    print("📊 A carregar AROEIRA_BRAND_ANALYSIS...")
    brand_data = fetch_brand_analysis(token)
    columns = brand_data["columns"]
    produtos = [dict(zip([c.strip() for c in columns], row)) for row in brand_data["rows"]]
    print(f"✓ {len(produtos)} produtos carregados")

    print("🏭 A carregar laboratórios...")
    lab_data = fetch_laboratorios(token)
    lab_columns = lab_data["columns"]
    laboratorios = [dict(zip([c.strip() for c in lab_columns], row)) for row in lab_data["rows"]]
    print(f"✓ {len(laboratorios)} laboratórios carregados")

    output = {"updated_at": datetime.now().isoformat(), "produtos": produtos,
              "laboratorios": laboratorios, "total_produtos": len(produtos)}

    with open("data/aroeira_brand.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✅ data/aroeira_brand.json guardado ({len(produtos)} produtos)")

if __name__ == "__main__":
    main()
