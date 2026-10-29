import os
from pathlib import Path

from dotenv import load_dotenv

from backend.app import create_app

load_dotenv(Path(__file__).resolve().parent / '.env', override=True)
if not os.getenv('DATABASE_URL'):
    raise RuntimeError('Set DATABASE_URL in the project .env. Local startup will not fall back to another database.')
app = create_app()


if __name__ == "__main__":
    print('Local API uses the database selected in the project .env. Edits affect that shared database.', flush=True)
    app.run(debug=True, port=int(os.getenv("PORT", "5000")))
