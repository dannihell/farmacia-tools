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
    print("Access token obtido")
    return d["access_token"]

def query_zoho(token, sql):
    headers = {"Authorization": f"Zoho-oauthtoken {token}", "ZANALYTICS-ORGID": ORG_ID}
    config = {"sqlQuery": sql, "responseFormat": "json"}
    r = requests.get(f"{API_BASE}/bulk/workspaces/{WORKSPACE_ID}/data",
        params={"CONFIG": json.dumps(config)}, headers=headers)
    d = r.json()
    if d.get("status") != "success":
        raise Exception(f"Job creation error: {d}")
    job_id = d["data"]["jobId"]
    print(f"Job: {job_id}")
    for attempt in range(30):
        time.sleep(10)
        r = requests.get(f"{API_BASE}/bulk/workspaces/{WORKSPACE_ID}/exportjobs/{job_id}", headers=headers)
        status = r.json().get("data", {}).get("jobStatus", "UNKNOWN")
        print(f"Status {attempt+1}: {status}")
        if status == "JOB COMPLETED":
            break
        if status in ("JOB FAILED", "JOB CANCELLED"):
            raise Exception(f"Job falhou: {r.json()}")
    else:
        raise Exception("Timeout")
    r = requests.get(f"{API_BASE}/bulk/workspaces/{WORKSPACE_ID}/exportjobs/{job_id}/data", headers=headers)
    return r.json()

def to_float(v):
    if v is None:
        return 0.0
    return float(str(v).replace(',', '.').replace(' ', ''))

def main():
    print(datetime.now().strftime("%Y-%m-%d %H:%M"))
    token = get_access_token()
    os.makedirs("data", exist_ok=True)

    print("A carregar AROEIRA_PRODUCT_ANALYSIS...")
    result = query_zoho(token, "SELECT * FROM AROEIRA_PRODUCT_ANALYSIS")
    rows = result if isinstance(result, list) else result.get("data", [])
    print(f"{len(rows)} produtos")

    produtos = []
    for row in rows:
        row = {k.lstrip(chr(65279)): v for k, v in row.items()}
        produtos.append(row)

    produtos.sort(key=lambda x: to_float(x.get("TOTAL_QT", 0)), reverse=True)

    labs = sorted(set(
        (p.get("ENT_RESP_COMERC", ""), p.get("MARCA", ""))
        for p in produtos
        if p.get("ENT_RESP_COMERC")
    ), key=lambda x: x[0])
    laboratorios = [{"ENT_RESP_COMERC": l[0], "MARCA": l[1]} for l in labs]

    output = {
        "updated_at": datetime.now().isoformat(),
        "produtos": produtos,
        "laboratorios": laboratorios,
        "total_produtos": len(produtos)
    }

    with open("data/aroeira_brand.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    size_mb = os.path.getsize("data/aroeira_brand.json") / 1024 / 1024
    print(f"Guardado: {len(produtos)} produtos, {size_mb:.1f}MB")

if __name__ == "__main__":
    main()
