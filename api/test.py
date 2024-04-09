import os
import json
import boto3
from fastapi import APIRouter, HTTPException, status
from supabase import create_client, Client
from pydantic import BaseModel
from dotenv import load_dotenv
import random
from log  import setup_logger
import json

logging = setup_logger()
load_dotenv()

supabase_url = os.getenv("supabase_url")
supabase_key = os.getenv("supabase_key")


supabase = create_client(supabase_url, supabase_key)

def calaucte_d_score(system_id:str):
    # Get system data
    try:
        system_data = supabase.table('system').select("*").eq('id', system_id).execute()
    except Exception as e:
        logging.error(f"Error with query: {e}")
        return HTTPException(status_code=500, detail="Internal Server Error")
    system_description = system_data.data[0]["system_description"]
    print(system_description)
    response = "high"
    if 'high' in response:
        response='H'
    elif 'medium' in response:
        response='M'
    elif 'low' in response:
        response='L'
    
    
    payload = {"d_score":response}
    insert_response = supabase.table('result').update([payload]).eq("system_id",system_id).execute()
    # insert_response = supabase.table('result').insert(payload, upsert=True).eq("system_id",system_id).execute()
    print(insert_response)

    # # if insert_response['status_code']==201:
    # #     print(f"Data for system ID {payload['system_id']} inserted successfully.")
    # #     logging.info(f"Data for system ID {payload['system_id']} inserted successfully.")
    # # else:
    # #     print(f"Failed to insert data for system ID {payload['system_id']}. Error:unable to upload the data to supabase")
    # #     logging.error(f"Failed to insert data for system ID {payload['system_id']}. Error: unable to upload the data to supabase")
    #     # return HTTPException(status_code=402, detail="Failed to store data")
    # return {"response":response,"status":"success"}

calaucte_d_score("af32cbb8-1d37-43c8-81e0-06a104e1cb45")