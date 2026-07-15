from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from webui.app import create_app

app = create_app()
