import requests, json, os, csv, io, time
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

def query_zoho_csv(token, sql):
    headers = {"Authorization": f"Zoho-oauthtoken {token}", "ZANALYTICS-ORGID": ORG_ID}
    config = {"sqlQuery": sql, "responseFormat": "csv"}
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
    text = r.text.lstrip(chr(65279))
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)

def to_float(v):
    if v is None or v == '':
        return 0.0
    try:
        return float(str(v).replace(',', '.').replace(' ', ''))
    except:
        return 0.0

def month_offset(year, month, offset):
    m = month - offset
    y = year
    while m <= 0:
        m += 12
        y -= 1
    return y, m

def build_sql():
    today = datetime.now()
    cur_year = today.year
    prev_year = cur_year - 1
    cur_month = today.month

    v_cols = []
    for i in range(18):
        y, m = month_offset(cur_year, cur_month, i)
        v_cols.append(f"SUM(CASE WHEN ANO={y} AND MES={m} THEN QT ELSE 0 END) AS V{i}")

    v_sql = ",\n  ".join(v_cols)

    return f"""SELECT
  COD_PRD,
  DESIGNACAO,
  ENT_RESP_COMERC,
  MARCA,
  STK_FARMACIA,
  PCUSMED_PROD,
  PVP_PROD,
  FAM_ESTAT,
  SFAM_ESTAT,
  CATEGORIA_DESIGNACAO,
  MERCADO_DESIGNACAO,
  {v_sql},
  SUM(CASE WHEN ANO={cur_year} THEN VALOR_VENDA_SIVA ELSE 0 END) AS VENDAS_YTD,
  SUM(CASE WHEN ANO={cur_year} THEN VALOR_VENDA_SIVA - (QT * PCUSMED_PROD) ELSE 0 END) AS MARGEM_YTD,
  SUM(CASE WHEN ANO={prev_year} AND MES<={cur_month} THEN VALOR_VENDA_SIVA ELSE 0 END) AS VENDAS_ANO_ANT_YTD,
  SUM(QT) AS TOTAL_QT,
  SUM(CASE WHEN QT < 0 THEN ABS(QT * PCUSMED_PROD) ELSE 0 END) AS VALOR_QUEBRAS
FROM AROEIRA_BRAND_ANALYSIS
GROUP BY COD_PRD, DESIGNACAO, ENT_RESP_COMERC, MARCA, STK_FARMACIA, PCUSMED_PROD, PVP_PROD, FAM_ESTAT, SFAM_ESTAT, CATEGORIA_DESIGNACAO, MERCADO_DESIGNACAO
HAVING SUM(QT) > 0 OR MAX(STK_FARMACIA) > 0"""

def main():
    print(datetime.now().strftime("%Y-%m-%d %H:%M"))
    token = get_access_token()
    os.makedirs("data", exist_ok=True)

    print("A construir SQL com datas literais...")
    sql = build_sql()
    print(f"SQL pronto ({len(sql)} chars)")

    print("A carregar dados do Zoho...")
    rows = query_zoho_csv(token, sql)
    print(f"{len(rows)} produtos recebidos")

    if rows:
        print(f"DEBUG chaves: {list(rows[0].keys())[:8]}")
        print(f"DEBUG V0={rows[0].get('V0')} V1={rows[0].get('V1')} VENDAS_YTD={rows[0].get('VENDAS_YTD')}")

    produtos = []
    for row in rows:
        clean = {k.lstrip(chr(65279)): v for k, v in row.items()}
        produtos.append(clean)

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
