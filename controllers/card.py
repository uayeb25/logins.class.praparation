import json
import logging


from dotenv import load_dotenv
from fastapi import HTTPException, Depends


import firebase_admin
from utils.database import fetch_query_as_json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_cards():
    query = f"select * from otd.cards order by id desc"

    try:
        logger.info(f"QUERY LIST")
        result_json = await fetch_query_as_json(query)
        result_dict = json.loads(result_json)
        return result_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def fetch_card(id: int):
    query = f"select * from otd.cards where id = {id}"
    result_dict = []
    try:
        logger.info(f"QUERY LIST")
        result_json = await fetch_query_as_json(query)
        result_dict = json.loads(result_json)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if len(result_dict) == 0:
            raise HTTPException(status_code=404, detail="Card not found")

    return result_dict[0]

async def delete_card(id: int):
    query = f"EXEC otd.delete_card @card_id = {id};"
    result = {}
    try:

        logger.info(f"QUERY DELETE")
        result_json = await fetch_query_as_json(query, is_procedure=True)
        result = json.loads(result_json)[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if result["status"] == 404:
        raise HTTPException(status_code=404, detail="Card not found")

    return result

async def fetch_update_card(id: int, title: str, description: str):
    query = f"EXEC otd.update_card @id = {id}, @title = '{title}', @description = '{description}';"
    result = {}
    try:

        logger.info(f"QUERY UPDATE")
        result_json = await fetch_query_as_json(query, is_procedure=True)
        result = json.loads(result_json)[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if result["status"] == 404:
        raise HTTPException(status_code=404, detail="Card not found")

    return result


async def fetch_create_card(title: str, description: str):
    query = f"EXEC otd.create_card @title = '{title}', @description = '{description}';"
    result = {}
    try:

        logger.info(f"QUERY UPDATE")
        result_json = await fetch_query_as_json(query, is_procedure=True)
        result = json.loads(result_json)[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if result["status"] == 404:
        raise HTTPException(status_code=404, detail="Card not found")

    return result