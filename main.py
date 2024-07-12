import os
import secrets
import hashlib
import base64
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2AuthorizationCodeBearer
from starlette.responses import RedirectResponse, JSONResponse
from msal import ConfidentialClientApplication
from dotenv import load_dotenv
from urllib.parse import urlencode
import requests

from firebase_admin import credentials, initialize_app, auth

load_dotenv()

app = FastAPI()

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
tenant_id = os.getenv("TENANT_ID")
redirect_uri = os.getenv("REDIRECT_URI")
pkce = os.getenv("PKCE")

# OAuth2 configuration
authorization_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"



google_client_id = os.getenv("GOOGLE_CLIENT_ID")
google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
google_redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
google_authorization_url = "https://accounts.google.com/o/oauth2/auth"
google_token_url = "https://oauth2.googleapis.com/token"
userinfo_url = "https://openidconnect.googleapis.com/v1/userinfo"




oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=authorization_url,
    tokenUrl=token_url,
)

google_oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=google_authorization_url,
    tokenUrl=google_token_url,
)


msal_app = ConfidentialClientApplication(
    client_id,
    authority=f"https://login.microsoftonline.com/{tenant_id}",
    client_credential=client_secret,
)

def generate_pkce_verifier():
    return secrets.token_urlsafe(32)

def generate_pkce_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode('ascii')

@app.get("/")
def read_root():
    return {"message": "Welcome to the FastAPI application with Office 365 SSO"}

@app.get("/login")
async def login(response: Response):
    # Generar PKCE verifier y challenge
    pkce_verifier = pkce
    pkce_challenge = generate_pkce_challenge(pkce_verifier)

    # Guardar el PKCE verifier en una cookie
    response.set_cookie(key="pkce_verifier", value=pkce_verifier, httponly=True)

    auth_url_params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": "User.Read",
        "code_challenge": pkce_challenge,
        "code_challenge_method": "S256"
    }
    auth_url = f"{authorization_url}?{urlencode(auth_url_params)}"
    return RedirectResponse(auth_url)

@app.get("/auth/callback")
async def auth_callback(request: Request, response: Response):
    code = request.query_params.get("code")

    print("Code:", code)
    print("PKCE:", pkce)

    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not found")

    # Realizar la solicitud para obtener el token de acceso
    token_data = {
        "client_id": client_id,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "code_verifier": pkce
    }

    token_response = requests.post(token_url, data=token_data)
    token_response_data = token_response.json()

    if "access_token" in token_response_data:
        return JSONResponse(content={"access_token": token_response_data["access_token"]})
    else:
        return JSONResponse(content={"error": token_response_data.get("error"), "error_description": token_response_data.get("error_description")}, status_code=400)

@app.get("/secure-endpoint")
async def secure_endpoint(token: str = Depends(oauth2_scheme)):
    return {"message": "This is a secure endpoint", "token": token}


@app.get("/login/google")
async def login():
    auth_url_params = {
        "client_id": google_client_id,
        "response_type": "code",
        "redirect_uri": google_redirect_uri,
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{google_authorization_url}?{urlencode(auth_url_params)}"
    return RedirectResponse(auth_url)

@app.get("/auth/google/callback")
async def auth_callback(request: Request, response: Response):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not found")

    token_data = {
        "client_id": google_client_id,
        "client_secret": google_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": google_redirect_uri,
    }

    token_response = requests.post(google_token_url, data=token_data)
    token_response_data = token_response.json()

    if "access_token" not in token_response_data:
        return JSONResponse(content={"error": token_response_data.get("error"), "error_description": token_response_data.get("error_description")}, status_code=400)

    access_token = token_response_data["access_token"]
    userinfo_response = requests.get(userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
    userinfo_data = userinfo_response.json()

    return JSONResponse(content={"userinfo": userinfo_data})

