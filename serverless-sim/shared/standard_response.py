from functools import wraps
from .custom_exception import CustomException
import traceback
import logging

from flask import jsonify

def standard_response(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            response = {
                "status": "success",
                "data": result,
                "message": "Operation completed successfully"
            }
            return jsonify(response), 200
        except CustomException as ce:
            response = {
                "status": "error",
                "data": {},
                "message": ce.message
            }
            return jsonify(response), ce.status_code
        except Exception:
            logger = logging.getLogger(__name__)
            logger.error(f"An error occurred: {traceback.format_exc()}")
            response = {
                "status": "error",
                "data": {},
                "message": "An unexpected error occurred"
            }
            return jsonify(response), 500
    return wrapper
