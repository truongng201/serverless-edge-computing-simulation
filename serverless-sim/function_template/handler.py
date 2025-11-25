import time

def handler(event, context):
    print("Simulate an simple execution with sleeping")
    time.sleep(5)
    return f"Say hi to this simulation. Event: {event}, Context: {context}"