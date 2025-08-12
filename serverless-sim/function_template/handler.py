import os
import time
import json

def handler(event, context):
    print("Serverless function handler started")
    
    # Simulate function execution
    function_id = os.environ.get("FUNCTION_ID", "unknown")
    execution_time = float(os.environ.get("EXECUTION_TIME", "1.0"))
    
    print(f"Executing function: {function_id}")
    print(f"Simulated execution time: {execution_time}s")
    
    # Simulate work
    time.sleep(execution_time)
    
    result = {
        "function_id": function_id,
        "status": "completed",
        "execution_time": execution_time,
        "timestamp": time.time()
    }
    
    print(f"Function result: {json.dumps(result)}")
    return json.dumps(result)

if __name__ == "__main__":
    handler({}, {})