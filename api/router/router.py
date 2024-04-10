from fastapi import Depends, FastAPI, File,  UploadFile, Form, File, APIRouter, HTTPException, Response, Query, status
# from log import setup_logger
from supabase import create_client
from pydantic import BaseModel
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
import boto3
from openai import OpenAI
import os
import json
from dotenv import load_dotenv
# from log import setup_logger
from typing import Dict, List

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


load_dotenv()

router = APIRouter()
# logging = setup_logger()

# Define your AWS credentials
aws_access_key_id = os.getenv("ACCESS_KEY")
aws_secret_access_key = os.getenv("SECRET_ACCESS_KEY")

# create a connection using supabase
supabase_url = os.getenv("supabase_url")
supabase_key = os.getenv("supabase_key")

# Create Supabase client
# print(supabase_key,supabase_url)
supabase = create_client(supabase_url, supabase_key)

os.environ['OPENAI_API_KEY'] = os.getenv('OPEN_API_KEY')
client = OpenAI()

# Create a client using your credentials
bedrock = boto3.client(
    service_name='bedrock-runtime',
    region_name='us-west-2',
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key
)

from datetime import datetime, timedelta

# @router.post('/GetSlotAvail/{agent_id}')
# def get_slot_time(agent_id:str):
#     agent_info = supabase.table('agent_availability').select('*').eq('agent_id',agent_id).execute()
#     agent_info=agent_info.data[0]
#     print(agent_info)
#     start_time = agent_info['login_at']
#     end_time = agent_info['logoff_at']
#     buffer_time= agent_info['buffer_time']
#     schedule = create_schedule(start_time, end_time,buffer_time)
#     return schedule
# def create_schedule(start_time, end_time,buffer_time):
#     # Convert string inputs to datetime objects
#     start_time = datetime.strptime(start_time, "%H:%M:%S")
#     end_time = datetime.strptime(end_time, "%H:%M:%S")

#     schedule = []

#     current_time = start_time
#     while current_time < end_time:
#         # Add 30-minute time slot
#         slot_start = current_time.strftime("%H:%M:%S")
#         slot_end = (current_time + timedelta(minutes=buffer_time)).strftime("%H:%M:%S")
#         schedule.append((slot_start, slot_end))

#         # Add 5-minute break
#         current_time += timedelta(minutes=35)

#     # Add 1-hour lunch break
#     lunch_start = current_time.strftime("%H:%M:%S")
#     lunch_end = (current_time + timedelta(hours=1)).strftime("%H:%M:%S")
#     schedule.append(("Lunch", lunch_start, lunch_end))

#     return schedule

from datetime import datetime, timedelta

@router.post('/GetSlotAvail/{agent_id}')
def get_available_slots(agent_id:str):
    """
    This function generates a JSON object with available slots for an agent
    based on the provided schema data, considering weekend preferences and
    correct slot time with buffer.

    Args:
        data: A dictionary containing the agent's schema data:
            - agent_id (int): The agent's ID.
            - working_on_sat (str): "Yes" or "No" indicating working on Saturday.
            - working_on_sun (str): "Yes" or "No" indicating working on Sunday.
            - leave_from (str): Start date of leave period (optional).
            - leave_to (str): End date of leave period (optional).
            - consulting_duration_from (str): Start time for consultations (e.g., "09:00:00").
            - consulting_duration_to (str): End time for consultations (e.g., "06:00:00").
            - slot_time (int): Duration of each appointment slot (minutes).
            - buffer_time (int): Buffer time between appointments (minutes).

    Returns:
        A dictionary representing the JSON output:
            - agent_id (int): The agent's ID.
            - available_slots (dict): Available slots mapped to dates.
    """
    agent_info = supabase.table('agent_availability').select('*').eq('agent_id',agent_id).execute()
    data=agent_info.data[0]
    # Convert working on Sat/Sun and time strings to appropriate data types
    working_on_sat = data['working_on_sat'] == True
    working_on_sun = data['working_on_sun'] == True
    consulting_from = datetime.strptime(data['login_at'], "%H:%M:%S").time()
    consulting_to = datetime.strptime(data['logoff_at'], "%H:%M:%S").time()

    # Define slot and buffer durations as timedelta objects
    slot_time = timedelta(minutes=data['slot_time'])
    buffer_time = timedelta(minutes=data['buffer_time'])

    available_slots = {}
    current_date = datetime.today()

    # Iterate for the next 7 days, excluding weekends if agent doesn't work
    for i in range(7):
        date = current_date + timedelta(days=i)

        # Skip weekend days based on agent's preferences
        if (date.weekday() == 5 and not working_on_sat) or (date.weekday() == 6 and not working_on_sun):
            continue

        # Check for leave period
        if data.get('leave_from') and data.get('leave_to'):
            leave_from = datetime.strptime(data['leave_from'], "%Y-%m-%d").date()
            leave_to = datetime.strptime(data['leave_to'], "%Y-%m-%d").date()
            if leave_from <= date <= leave_to:
                continue

        slots = []
        current_time = consulting_from

        # Generate slots for the date within consulting hours
        while current_time < consulting_to:
            end_time = (datetime.combine(datetime.today(), current_time) + slot_time).time()

            if end_time <= consulting_to:
                slots.append({
                    "start_time": current_time.strftime("%H:%M:%S"),
                    "end_time": end_time.strftime("%H:%M:%S"),
                    "status": "available"
                })

            # Advance to the next slot considering buffer time
            current_time = (datetime.combine(datetime.today(), end_time) + buffer_time).time()

        if slots:
            available_slots[date.strftime("%Y-%m-%d")] = slots

    return {
        "agent_id": data["agent_id"],
        "available_slots": available_slots
    }

@router.get('/getServiceList')
def get_service_list():
    service_data = supabase.table('service').select('*').execute()
    service_data = service_data.data
    service_list = []

    for value in service_data:
        
        data = {value['service_name']:{"description":value['description'],"agent_info":value['agents_opted']['agent_info']}}
        service_list.append(data)
    return data
# print(get_available_slots('b6ba6831-f549-407c-bce4-3e97ad2771d0'))
#
class EmailInput(BaseModel):
    sender_email: str
    sender_password: str
    receiver_email: str
    subject: str
    message: str
## Send an email to the user
@router.post("/send_email/")
def send_email_route(email_input: EmailInput):
    try:
        # Set up the SMTP server
        smtp_server = smtplib.SMTP('smtp.gmail.com', 587)
        smtp_server.starttls()
        smtp_server.login(email_input.sender_email, email_input.sender_password)

        # Create message container - the correct MIME type is multipart/alternative.
        msg = MIMEMultipart('alternative')
        msg['From'] = email_input.sender_email
        msg['To'] = email_input.receiver_email
        msg['Subject'] = email_input.subject

        # Attach plain text message to email
        msg.attach(MIMEText(email_input.message, 'plain'))

        # Send the message via the SMTP server
        smtp_server.sendmail(email_input.sender_email, email_input.receiver_email, msg.as_string())

        # Close the SMTP server
        smtp_server.quit()
        
        return {"message": "Email sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to send email: " + str(e))


## Get the list of services
@router.get('/getServiceList')
def get_service_list():
    service_data = supabase.table('service').select('*').execute()
    service_data = service_data.data
    service_list = []

    for value in service_data:
        
        data = {value['service_name']:{"description":value['description'],"agent_info":value['agents_opted']['agent_info']}}
        service_list.append(data)
    return data


## Get the booked slots for the given agent id
@router.get("/booked-slots/{agent_id}")
def booked_slots(agent_id: int, sample_data: Dict):
    booked_slots = {}
    for date, slots in sample_data['available_slots'].items():
        for slot in slots:
            if slot['status'] == 'booked':
                booked_slots.setdefault(date, []).append(slot)
    return {'agent_id': agent_id, 'booked_slots': booked_slots}


## Get the available slots for the given agent id
@router.get("/available-slots/{agent_id}")
def available_slots(agent_id: int, sample_data: Dict):
    available_slots = {}
    for date, slots in sample_data['available_slots'].items():
        available = [slot for slot in slots if slot['status'] == 'available']
        if available:
            available_slots[date] = available
    return {'agent_id': agent_id, 'available_slots': available_slots}