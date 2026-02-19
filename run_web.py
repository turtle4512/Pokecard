"""
Launch the Flask web frontend.

Usage:
    python run_web.py
    # Open http://localhost:5000 in browser
"""

import os

from web import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port, threaded=True)
