import json
import logging
import os
import aiofiles

from fastapi import HTTPException, Depends
from fastapi import FastAPI, File, UploadFile, HTTPException

from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

from datetime import datetime, timedelta
from dotenv import load_dotenv

from utils.database import fetch_query_as_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_SAK")
AZURE_STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER")

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)


async def fetch_cards(email: str):
    query = f"""
        with cts as (
            select 
                card_id
                , count( * ) as total
            from otd.card_files
            group by card_id
        )

        select
            id,
            title,
            description,
            u.firstname + ' ' + u.lastname as author,
            cast(c.created_at as nvarchar(100)) as created_at,
            cast(c.updated_at as nvarchar(100)) as updated_at,
            case
                when c.email = '{email}' THEN 'Mine'
                else 'Shared'
            end as access,
            ISNULL( cts.total, 0 ) as total_files
        from otd.cards c
        inner join otd.users u
        on c.email = u.email
        LEFT join cts 
        on c.id = cts.card_id
        order by updated_at desc
    """

    try:
        logger.info(f"QUERY LIST")
        result_json = await fetch_query_as_json(query)
        result_dict = json.loads(result_json)
        return result_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def fetch_card(id: int, email: str):
    query = f"""
        select
            id
            , title
            , description
        from otd.cards
        where id = {id}
        and email = '{email}'
    """
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

async def delete_card(id: int, email: str):
    query = f"EXEC otd.delete_card @email='{email}' ,@card_id = {id};"
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


async def fetch_create_card(email:str, title: str, description: str):
    query = f"EXEC otd.create_card @email='{email}',  @title = '{title}', @description = '{description}';"
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

async def fetch_upload_card_files( email: str, id: int, files: list[UploadFile] = File(...) ):
    try:
        for file in files:

            query = f" exec otd.sp_insert_card_files @card_id = {id}, @file_name = '{file.filename}', @email = '{email}'"
            result_json = await fetch_query_as_json(query, is_procedure=True)
            result = json.loads(result_json)[0]

            if result["status"] == 404:
                raise HTTPException(status_code=404, detail="Card not found")

            container_client = blob_service_client.get_blob_client(container=AZURE_STORAGE_CONTAINER, blob=f"{id}/{file.filename}")
            async with aiofiles.open(file.filename, 'wb') as f:
                await f.write(await file.read())
            with open(file.filename, "rb") as data:
                container_client.upload_blob(data, overwrite=True)


        return {"message": "File uploaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def fetch_download_card_files(id: int):
    sas_expiration = datetime.utcnow() + timedelta(minutes=2)

    query = f"""
        select
            id
            , card_id
            , file_name
            , cast(created_at as nvarchar(100)) as created_at
        from otd.card_files
        where card_id = {id}
    """

    try:
        result_json = await fetch_query_as_json(query)
        result_dict = json.loads(result_json)

        for file in result_dict:
            file_name = f"{ file['card_id'] }/{ file['file_name'] }"
            # Genera el SAS
            sas_token = generate_blob_sas(
                account_name=blob_service_client.account_name,
                container_name=AZURE_STORAGE_CONTAINER,
                blob_name=file_name,
                account_key=blob_service_client.credential.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=sas_expiration
            )

            file["url"] = f"https://{blob_service_client.account_name}.blob.core.windows.net/{AZURE_STORAGE_CONTAINER}/{file_name}?{sas_token}"

        return result_dict
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))