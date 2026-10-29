import os

from dotenv import load_dotenv

from backend.app import create_app

load_dotenv()
app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "5000")))
