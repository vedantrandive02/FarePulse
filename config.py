from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "FarePulse API"
    database_url: str = "sqlite:///./farepulse.db"
    fare_provider: str = "demo"
    amadeus_client_id: str = ""
    amadeus_client_secret: str = ""
    amadeus_base_url: str = "https://test.api.amadeus.com"
    serpapi_api_key: str = ""
    serpapi_base_url: str = "https://serpapi.com/search.json"
    collection_interval_minutes: int = 360
    cors_origins: str = "http://localhost:5173"
    secret_key: str = "development-only-change-me"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origins(self):
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

settings = Settings()
