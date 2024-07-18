import os
import requests

from dotenv import load_dotenv

from fastapi import HTTPException


import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from utils.database import get_db_connection
from models.Userlogin import UserRegister


load_dotenv()


# Inicializar la app de Firebase Admin
cred = credentials.Certificate("secrets/admin-firebasesdk.json")
firebase_admin.initialize_app(cred)

async def register_user_firebase(user: UserRegister):
    try:
        # Crear usuario en Firebase Authentication
        user_record = firebase_auth.create_user(
            email=user.email,
            password=user.password
        )

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "EXEC otd.create_user @username = ?, @name = ?, @email = ?"
                , user_record.uid
                , user.name
                , user.email
            )
            conn.commit()
            return {
                "success": True
                , "message": "Usuario registrado exitosamente"
            }
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        raise HTTPException(
            status_code=400
            , detail=f"Error al registrar usuario: {e}"
        )


async def login_user_firebase(user: UserRegister):
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
        raise HTTPException(
            status_code=400
            , detail=f"Error al autenticar usuario: {e}"
        )