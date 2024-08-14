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

from azure.storage.queue import QueueClient, BinaryBase64DecodePolicy, BinaryBase64EncodePolicy

from utils.database import fetch_query_as_json, get_db_connection
from utils.security import create_jwt_token
from utils.database import fetch_query_as_json

from models.UserRegister import UserRegister
from models.UserLogin import UserLogin
from models.UserActivation import UserActivation


# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar la app de Firebase Admin
cred = credentials.Certificate("secrets/admin-firebasesdk.json")
firebase_admin.initialize_app(cred)

load_dotenv()

azure_sak = os.getenv('AZURE_SAK')
queue_name = os.getenv('QUEUE_ACTIVATE')

queue_client = QueueClient.from_connection_string(azure_sak, queue_name)
queue_client.message_decode_policy = BinaryBase64DecodePolicy()
queue_client.message_encode_policy = BinaryBase64EncodePolicy()

async def inser_message_on_queue(message: str):
    message_bytes = message.encode('utf-8')
    queue_client.send_message(
        queue_client.message_encode_policy.encode(message_bytes)
    )

async def register_user_firebase(user: UserRegister):
    user_record = {}
    try:
        # Crear usuario en Firebase Authentication
        user_record = firebase_auth.create_user(
            email=user.email,
            password=user.password
        )

    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=400,
            detail=f"Error al registrar usuario: {e}"
        )

    query = f" exec otd.create_user @email = '{user.email}', @firstname = '{user.firstname}', @lastname = '{user.lastname}'"
    result = {}
    try:

        result_json = await fetch_query_as_json(query, is_procedure=True)
        ##result = json.loads(result_json)[0]

        await inser_message_on_queue(user.email)

        return {"message": "Usuario registrado exitosamente"}

    except Exception as e:
        firebase_auth.delete_user(user_record.uid)
        raise HTTPException(status_code=500, detail=str(e))


async def generate_activation_code(email: str):

    code = random.randint(100000, 999999)
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


async def login_user_firebase(user: UserLogin):
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

        query = f"""select 
                        email
                        , firstname
                        , lastname
                        , active
                    from [otd].[users]
                    where email = '{ user.email }'
                    """

        try:
            result_json = await fetch_query_as_json(query)
            result_dict = json.loads(result_json)
            return {
                "message": "Usuario autenticado exitosamente",
                "idToken": create_jwt_token(
                    result_dict[0]["firstname"],
                    result_dict[0]["lastname"],
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


async def activate_user(user: UserActivation):
    query = f"""
            select 
                email 
                , case
                    when GETDATE() between created_at and expired_at then 'active'
                    else 'expired'
                end as status
            from otd.activation_codes 
            where code = {user.code}
            and email = '{user.email}';
            """

    try:
        result_json = await fetch_query_as_json(query)
        result_dict = json.loads(result_json)
        if len(result_dict) == 0:
            raise HTTPException(status_code=404, detail="Código de activación no encontrado")

        if result_dict[0]["status"] == "expired":
            await inser_message_on_queue(user.email)
            raise HTTPException(status_code=400, detail="Código de activación expirado")

        query = f"""
                exec otd.activate_user @email = '{user.email}';
                """
        result_json = await fetch_query_as_json(query, is_procedure=True)

        return {
            "message": "Usuario activado exitosamente"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
