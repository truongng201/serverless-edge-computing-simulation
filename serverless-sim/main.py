from control.ui_handler import app
from flask_cors import CORS

def main():
    # Start the Flask application
    # set cors_allowed_origins to allow all origins
    CORS(app, resources={r"/*": {"origins": "*"}})
    app.run(host="0.0.0.0", port=5001, debug=True)

if __name__ == "__main__":
    main()