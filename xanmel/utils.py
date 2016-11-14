import datetime
import pytz

def current_time():
    utc = pytz.timezone('UTC')
    return datetime.datetime.utcnow().replace(tzinfo=utc)
