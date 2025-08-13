import time

time.sleep(3)  # Simulate some processing delay

def handler(event, context):
    return f"Say hi to this simulation. Event: {event}, Context: {context}"