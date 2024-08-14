import os
import requests
import json
import logging
import traceback
import random

from dotenv import load_dotenv
from fastapi import HTTPException


import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

from azure.storage.queue import QueueServiceClient, QueueClient, QueueMessage

from utils.database import fetch_query_as_json, get_db_connection
from utils.security import create_jwt_token
from utils.database import fetch_query_as_json
from models.UserRegister import UserRegister


# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

azure_sak = os.getenv('AZURE_SAK')
queue_name = os.getenv('QUEUE_ACTIVATE')

queue_client = QueueClient.from_connection_string(azure_sak, queue_name)

# Inicializar la app de Firebase Admin
cred = credentials.Certificate("secrets/admin-firebasesdk.json")
firebase_admin.initialize_app(cred)

async def register_user_firebase(user: UserRegister):
    user_record = {}
    try:
        # Crear usuario en Firebase Authentication
        user_record = firebase_auth.create_user(
            email=user.email,
            password=user.password
        )

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error al registrar usuario: {e}"
        )

    query = f" exec otd.create_user @email = '{user.email}', @firstname = '{user.firstname}', @lastname = '{user.lastname}'"
    result = {}
    try:

        result_json = await fetch_query_as_json(query, is_procedure=True)
        result = json.loads(result_json)[0]

    except Exception as e:
        firebase_auth.delete_user(user_record.uid)
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    if result["status"] == 404:
        raise HTTPException(status_code=404, detail="Error al registrar usuario")

    queue_client.send_message(user.email)

    return result

async def generate_activation_code(email: str):

    code = random.randint(10000, 99999)
    query = f" exec otd.generate_activation_code @email = '{email}', @code = {code}"
    result = {}
    try:
        result_json = await fetch_query_as_json(query, is_procedure=True)
        result = json.loads(result_json)[0]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "message": "Código de activación generado exitosamente",
        "code": code
    }


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
                status_code=400,
                detail=f"Error al autenticar usuario: {response_data['error']['message']}"
            )

        query = f"SELECT active FROM otd.users WHERE email = '{user.email}'"

        try:
            logger.info(f"QUERY LIST")
            result_json = await fetch_query_as_json(query)
            result_dict = json.loads(result_json)
            return {
                "message": "Usuario autenticado exitosamente",
                "idToken": create_jwt_token(
                    user.email,
                    result_dict[0]["active"]
                )
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


    except Exception as e:
        error_detail = {
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc()
        }
        raise HTTPException(
            status_code=400,
            detail=f"Error al registrar usuario: {error_detail}"
        )