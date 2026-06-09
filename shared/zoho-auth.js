// Zoho OAuth Configuration - Farmacia Tools
const ZOHO_CONFIG = {
  clientId: "1000.Y81UHHQHGEOKDFRM3M96OJ2AXFVJWU",
  redirectUri: "https://dannihell.github.io/farmacia-tools/callback.html",
  authUrl: "https://accounts.zoho.eu/oauth/v2/auth",
  apiBase: "https://analyticsapi.zoho.eu/api/v2",
  workspaceId: "1135564000002838003",
  scope: "ZohoAnalytics.data.read",
};

// Store/retrieve access token
const ZohoAuth = {
  getToken() {
    return sessionStorage.getItem("zoho_access_token");
  },
  setToken(token) {
    sessionStorage.setItem("zoho_access_token", token);
  },
  clearToken() {
    sessionStorage.removeItem("zoho_access_token");
  },
  isAuthenticated() {
    return !!this.getToken();
  },
  login() {
    const params = new URLSearchParams({
      response_type: "token",
      client_id: ZOHO_CONFIG.clientId,
      scope: ZOHO_CONFIG.scope,
      redirect_uri: ZOHO_CONFIG.redirectUri,
      access_type: "online",
    });
    window.location.href = `${ZOHO_CONFIG.authUrl}?${params.toString()}`;
  },
};

// Query Zoho Analytics
async function queryZoho(sql) {
  const token = ZohoAuth.getToken();
  if (!token) throw new Error("Not authenticated");

  const url = `${ZOHO_CONFIG.apiBase}/workspaces/${ZOHO_CONFIG.workspaceId}/views/data`;
  const params = new URLSearchParams({ sqlQuery: sql });

  const response = await fetch(`${url}?${params}`, {
    headers: {
      Authorization: `Zoho-oauthtoken ${token}`,
      "Content-Type": "application/json",
    },
  });

  if (response.status === 401) {
    ZohoAuth.clearToken();
    throw new Error("Token expired");
  }

  const data = await response.json();
  if (data.status !== "success") throw new Error(data.message || "Query failed");
  return data.data;
}
