from notion_client import Client
from functools import lru_cache
import os

def get_env_variable(name):
    """Retrieve an environment variable or raise an exception if not found."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

@lru_cache
def get_notion_client():
    """Return a cached instance of the Notion client."""
    return Client(auth=get_env_variable("NOTION_TOKEN"))

@lru_cache
def get_database_id():
    """Retrieve the Notion database ID from environment variables."""
    return get_env_variable("NOTION_DATABASE_ID")