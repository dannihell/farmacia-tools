import requests, json, os, time
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
    headers = {"Authorization": f"Zoho-oauthtoken {token}", "ZANALYTICS-ORGID": ORG_ID}

    # 1. Criar job
    config = {"sqlQuery": sql, "responseFormat": "json"}
    r = requests.get(f"{API_BASE}/bulk/workspaces/{WORKSPACE_ID}/data",
        params={"CONFIG": json.dumps(config)}, headers=headers)
    d = r.json()
    if d.get("status") != "success":
        raise Exception(f"Job creation error: {d}")
    job_id = d["data"]["jobId"]
    print(f"  Job criado: {job_id}")

    # 2. Polling status - endpoint correcto
    for attempt in range(20):
        time.sleep(5)
        r = requests.get(f"{API_BASE}/bulk/workspaces/{WORKSPACE_ID}/exportjobs/{job_id}",
            headers=headers)
        d = r.json()
        status = d.get("data", {}).get("jobStatus", "UNKNOWN")
        print(f"  Poll {attempt+1}: {status}")
        if status == "JOB COMPLETED":
            break
        if status in ("JOB FAILED", "JOB CANCELLED"):
            raise Exception(f"Job falhou: {d}")
    else:
        raise Exception("Timeout aguardando job")

    # 3. Download resultado
    r = requests.get(f"{API_BASE}/bulk/workspaces/{WORKSPACE_ID}/exportjobs/{job_id}/data",
        headers=headers)
    return r.json()

def main():
    print(f"🚀 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    token = get_access_token()
    os.makedirs("data", exist_ok=True)

    print("📊 A carregar AROEIRA_BRAND_ANALYSIS...")
    sql = "SELECT COD_PRD, DESIGNACAO, ENT_RESP_COMERC, MARCA, STK_FARMACIA, PCUSMED_PROD, DUV, CATEGORIA_DESIGNACAO, MERCADO_DESIGNACAO, QT, ANO, MES, VALOR_VENDA, MARGEM_EUROS, VALOR_QUEBRA FROM AROEIRA_BRAND_ANALYSIS"
    result = query_zoho(token, sql)

    if isinstance(result, dict):
        rows = result.get("data", result)
    else:
        rows = result

    print(f"✓ {len(rows) if isinstance(rows, list) else 'N/A'} linhas")
    print(f"Preview: {str(result)[:300]}")

    with open("data/aroeira_brand.json", "w", encoding="utf-8") as f:
        json.dump({"updated_at": datetime.now().isoformat(), "result": result}, f, ensure_ascii=False, indent=2)

    print("✅ Guardado!")

if __name__ == "__main__":
    main()
