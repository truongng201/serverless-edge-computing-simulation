from control.ui_handler import app

def main():
    # Start the Flask application
    app.run(host="0.0.0.0", port=5001, debug=True)

if __name__ == "__main__":
    main()