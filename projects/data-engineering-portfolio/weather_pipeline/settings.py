""" uv add "psycopg[binary]" pydantic-settings
secrets and connection settings, read from environment variables or a local .env file"""


from functools import lru_cache

from pydantic import SecretStr	
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

	postgres_host: str = "localhost"
	postgres_port: int = 5432
	postgres_db: str = "weather"
	postgres_user: str = "weather"
	postgres_password: SecretStr #no default on purpose, you must provide it

	@property
	def postgres_conninfo(self) -> str:
		return (
			f"host={self.postgres_host} port={self.postgres_port} "
			f"dbname={self.postgres_db} user={self.postgres_user} "
			f"password={self.postgres_password.get_secret_value()}"
		)


@lru_cache
def get_settings() -> Settings:
	return Settings() #type: ignore[call-arg] - values come from env vars / .env


