import os
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
import requests

load_dotenv()


# Inicializar la app de Firebase Admin
cred = credentials.Certificate("secrets/firebase-adminsdk.json")
firebase_admin.initialize_app(cred)

app = FastAPI()

# Modelo de datos para la solicitud de registro y login
class UserRegister(BaseModel):
    email: str
    password: str

@app.put("/register")
async def register_user(user: UserRegister):
    try:
        # Crear usuario en Firebase Authentication
        user_record = firebase_auth.create_user(
            email=user.email,
            password=user.password
        )
        return {
            "message": "Usuario registrado exitosamente"
            , "user_id": user_record.uid
        }
    except Exception as e:
        raise HTTPException(
            status_code=400
            , detail=f"Error al registrar usuario: {e}"
        )

@app.put("/login")
async def login_user(user: UserRegister):
    try:
        # Autenticar usuario con Firebase Authentication usando la API REST
        api_key = os.getenv("FIREBASE_API_KEY")  # Reemplaza esto con tu apiKey de Firebase
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        payload = {
            "email": user.email,
            "password": user.password,
            "returnSecureToken": True
        }
        response = requests.post(url, json=payload)
        response_data = response.json()

        if "error" in response_data:
            raise HTTPException(
                status_code=400
                , detail=f"Error al autenticar usuario: {response_data['error']['message']}"
            )

        id_token = response_data["idToken"]
        return {
            "message": "Usuario autenticado exitosamente"
            , "idToken": id_token
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al autenticar usuario: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)