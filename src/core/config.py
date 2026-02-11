from pathlib import Path
class Settings:
    app_name="IANAE"
    app_version="3.0.0"
    environment="development"
    debug=True
    data_dir=Path("data")
    database_url="sqlite:///./data/databases/ianae_v3.db"
    api_host="127.0.0.1"
    api_port=8000
settings=Settings()