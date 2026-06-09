import requests, json, os, time, csv, io
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
    print("Access token OK")
    return d["access_token"]

def bulk_query(token, sql):
    headers = {"Authorization": f"Zoho-oauthtoken {token}", "ZANALYTICS-ORGID": ORG_ID}
    config = {"sqlQuery": sql, "responseFormat": "csv"}
    r = requests.get(f"{API_BASE}/bulk/workspaces/{WORKSPACE_ID}/data",
        params={"CONFIG": json.dumps(config)}, headers=headers)
    d = r.json()
    job_id = d["data"]["jobId"]
    print(f"Job: {job_id}")
    for i in range(20):
        time.sleep(5)
        s = requests.get(f"{API_BASE}/bulk/workspaces/{WORKSPACE_ID}/exportjobs/{job_id}", headers=headers).json()
        status = s.get("data", {}).get("jobStatus", "")
        print(f"Poll {i+1}: {status}")
        if status == "JOB COMPLETED":
            break
        if "FAIL" in status or "CANCEL" in status:
            raise Exception(f"Job failed: {s}")
    r = requests.get(f"{API_BASE}/bulk/workspaces/{WORKSPACE_ID}/exportjobs/{job_id}/data", headers=headers)
    return list(csv.DictReader(io.StringIO(r.text.lstrip(chr(65279)))))

def aggregate(rows):
    now = datetime.now()
    year, month = now.year, now.month
    months = []
    for i in range(7):
        m, y = month - i, year
        while m <= 0: m += 12; y -= 1
        months.append((y, m))
    prods = {}
    for row in rows:
        row = {k.lstrip(chr(65279)): v for k,v in row.items()}; cod = row.get("COD_PRD")
        if not cod: continue
        if cod not in prods:
            prods[cod] = {k: row.get(k) for k in ["COD_PRD","DESIGNACAO","ENT_RESP_COMERC","MARCA","STK_FARMACIA","PCUSMED_PROD","DUV","CATEGORIA_DESIGNACAO","MERCADO_DESIGNACAO"]}
            for i in range(7): prods[cod][f"V{i}"] = 0
            prods[cod].update({"VENDAS_YTD":0,"MARGEM_YTD":0,"VALOR_QUEBRAS":0,"TOTAL_QT":0})
        p = prods[cod]
        try:
            ano, mes = int(row.get("ANO",0)), int(row.get("MES",0))
            qt = float(row.get("QT") or 0)
            venda = float(row.get("VALOR_VENDA") or 0)
            margem = float(row.get("MARGEM_EUROS") or 0)
            quebra = float(row.get("VALOR_QUEBRA") or 0)
        except: continue
        p["TOTAL_QT"] += qt
        p["VALOR_QUEBRAS"] += quebra
        for i,(y,m) in enumerate(months):
            if ano==y and mes==m: p[f"V{i}"] += qt
        if ano == year:
            p["VENDAS_YTD"] += venda
            p["MARGEM_YTD"] += margem
    return sorted(prods.values(), key=lambda x: x.get("TOTAL_QT",0), reverse=True)

def main():
    print(datetime.now().strftime("%Y-%m-%d %H:%M"))
    token = get_access_token()
    os.makedirs("data", exist_ok=True)
    now = datetime.now()
    year, month = now.year, now.month
    min_m, min_y = month - 12, year
    while min_m <= 0: min_m += 12; min_y -= 1
    print("A carregar AROEIRA_BRAND_ANALYSIS (13 meses)...")
    sql = f"SELECT COD_PRD,DESIGNACAO,ENT_RESP_COMERC,MARCA,STK_FARMACIA,PCUSMED_PROD,DUV,CATEGORIA_DESIGNACAO,MERCADO_DESIGNACAO,QT,ANO,MES,VALOR_VENDA,MARGEM_EUROS,VALOR_QUEBRA FROM AROEIRA_BRAND_ANALYSIS WHERE (ANO*12+MES)>=({min_y}*12+{min_m})"
    rows = bulk_query(token, sql)
    print(f"{len(rows)} linhas raw")
    prods = aggregate(rows)
    print(f"{len(prods)} produtos unicos")
    labs = bulk_query(token, "SELECT DISTINCT ENT_RESP_COMERC,MARCA FROM AROEIRA_BRAND_ANALYSIS WHERE ENT_RESP_COMERC IS NOT NULL ORDER BY ENT_RESP_COMERC")
    out = {"updated_at": datetime.now().isoformat(), "produtos": prods, "laboratorios": labs, "total_produtos": len(prods)}
    with open("data/aroeira_brand.json","w",encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    mb = os.path.getsize("data/aroeira_brand.json")/1024/1024
    print(f"Guardado: {len(prods)} produtos, {mb:.1f}MB")

if __name__ == "__main__":
    main()
