from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import app.core.config as config

SCOPES = ['https://www.googleapis.com/auth/calendar']
SERVICE_ACCOUNT_FILE = 'credentials.json'

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
calendar_service = build('calendar', 'v3', credentials=creds)

# --- google calendar funcs ---
def add_event(event_body):
    return calendar_service.events().insert(calendarId=config.MY_EMAIL, body=event_body).execute()

def get_events(time_min, time_max):
    events_result = calendar_service.events().list(
        calendarId=config.MY_EMAIL,
        timeMin=time_min, 
        timeMax=time_max,   
        singleEvents=True,                
        orderBy='startTime'               
    ).execute()
    return events_result.get('items',[])