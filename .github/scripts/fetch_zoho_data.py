import requests, json, os, time
from datetime import datetime
from collections import defaultdict

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
    config = {"sqlQuery": sql, "responseFormat": "json"}
    r = requests.get(f"{API_BASE}/bulk/workspaces/{WORKSPACE_ID}/data",
        params={"CONFIG": json.dumps(config)}, headers=headers)
    d = r.json()
    if d.get("status") != "success":
        raise Exception(f"Job creation error: {d}")
    job_id = d["data"]["jobId"]
    print(f"  Job: {job_id}")
    for attempt in range(20):
        time.sleep(5)
        r = requests.get(f"{API_BASE}/bulk/workspaces/{WORKSPACE_ID}/exportjobs/{job_id}", headers=headers)
        status = r.json().get("data", {}).get("jobStatus", "UNKNOWN")
        print(f"  Status {attempt+1}: {status}")
        if status == "JOB COMPLETED":
            break
        if status in ("JOB FAILED", "JOB CANCELLED"):
            raise Exception(f"Job falhou: {r.json()}")
    else:
        raise Exception("Timeout")
    r = requests.get(f"{API_BASE}/bulk/workspaces/{WORKSPACE_ID}/exportjobs/{job_id}/data", headers=headers)
    return r.json()

def agregar_por_produto(rows):
    now = datetime.now()
    year, month = now.year, now.month

    # Calcular os 7 meses relevantes (V0=actual, V1..V6=anteriores)
    months = []
    for i in range(18):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        months.append((y, m))

    produtos = {}
    for row in rows:
        row={k.lstrip(chr(65279)):v for k,v in row.items()};cod=row.get("COD_PRD")
        if cod is None:
            continue
        if cod not in produtos:
            produtos[cod] = {
                "COD_PRD": cod,
                "DESIGNACAO": row.get("DESIGNACAO"),
                "ENT_RESP_COMERC": row.get("ENT_RESP_COMERC"),
                "MARCA": row.get("MARCA"),
                "STK_FARMACIA": row.get("STK_FARMACIA"),
                "PCUSMED_PROD": row.get("PCUSMED_PROD"),
                "DUV": row.get("DUV"),
                "CATEGORIA_DESIGNACAO": row.get("CATEGORIA_DESIGNACAO"),
                "MERCADO_DESIGNACAO": row.get("MERCADO_DESIGNACAO"),
                "V0": 0, "V1": 0, "V2": 0, "V3": 0, "V4": 0, "V5": 0, "V6": 0,
                "VENDAS_YTD": 0, "MARGEM_YTD": 0, "VALOR_QUEBRAS": 0, "TOTAL_QT": 0
            }
        p = produtos[cod]
        try:
            ano = int(row.get("ANO", 0))
            mes = int(row.get("MES", 0))
            qt = float(row.get("QT") or 0)
            venda = float(row.get("VALOR_VENDA") or 0)
            margem = float(row.get("MARGEM_EUROS") or 0)
            quebra = float(row.get("VALOR_QUEBRA") or 0)
        except (ValueError, TypeError):
            continue

        p["TOTAL_QT"] += qt
        p["VALOR_QUEBRAS"] += quebra

        for i, (y, m) in enumerate(months):
            if ano == y and mes == m:
                p[f"V{i}"] += qt

        if ano == year:
            p["VENDAS_YTD"] += venda
            p["MARGEM_YTD"] += margem

    return list(produtos.values())

def main():
    print(f"🚀 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    token = get_access_token()
    os.makedirs("data", exist_ok=True)

    # Só últimos 13 meses para limitar tamanho
    now = datetime.now()
    year, month = now.year, now.month
    min_m = month - 17
    min_y = year
    while min_m <= 0:
        min_m += 12
        min_y -= 1

    print("📊 A carregar AROEIRA_BRAND_ANALYSIS (últimos 13 meses)...")
    sql = f"""SELECT COD_PRD, DESIGNACAO, ENT_RESP_COMERC, MARCA, STK_FARMACIA, PCUSMED_PROD, DUV, CATEGORIA_DESIGNACAO, MERCADO_DESIGNACAO, QT, ANO, MES, VALOR_VENDA, MARGEM_EUROS, VALOR_QUEBRA FROM AROEIRA_BRAND_ANALYSIS WHERE (ANO * 12 + MES) >= ({min_y} * 12 + {min_m})"""

    result = query_zoho(token, sql)
    rows = result if isinstance(result, list) else result.get("data", [])
    print(f"✓ {len(rows)} linhas raw")

    print("📊 A agregar por produto...")
    produtos = agregar_por_produto(rows)
    produtos.sort(key=lambda x: x.get("TOTAL_QT", 0), reverse=True)
    print(f"✓ {len(produtos)} produtos únicos")

    print("🏭 A carregar laboratórios...")
    lab_result = query_zoho(token, "SELECT DISTINCT ENT_RESP_COMERC, MARCA FROM AROEIRA_BRAND_ANALYSIS WHERE ENT_RESP_COMERC IS NOT NULL ORDER BY ENT_RESP_COMERC")
    laboratorios = lab_result if isinstance(lab_result, list) else lab_result.get("data", [])

    output = {
        "updated_at": datetime.now().isoformat(),
        "produtos": produtos,
        "laboratorios": laboratorios,
        "total_produtos": len(produtos)
    }

    with open("data/aroeira_brand.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    size_mb = os.path.getsize("data/aroeira_brand.json") / 1024 / 1024
    print(f"✅ data/aroeira_brand.json guardado ({len(produtos)} produtos, {size_mb:.1f}MB)")

if __name__ == "__main__":
    main()
