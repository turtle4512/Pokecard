"""
Launch the Flask web frontend.

Usage:
    python run_web.py
    # Open http://localhost:5000 in browser
"""

from web import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000, threaded=True)
