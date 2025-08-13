import os
from handler import handler
import json

if __name__ == "__main__":
    # Get JSON strings from env variables
    event_json = os.getenv("EVENT", "{}")
    context_json = os.getenv("CONTEXT", "{}")

    # Parse to Python dicts
    event = json.loads(event_json)
    context = json.loads(context_json)
    print("Result of function")
    # Call function and print result
    result = handler(event, context)
    print(result)