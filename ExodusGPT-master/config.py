import json
import os
from dotenv import load_dotenv

load_dotenv()

CONFIG_FILE = "bot_config.json"
DB_FILE = "exodusgpt.db"

# Secrets from .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not BOT_TOKEN:
    print("⚠️ WARNING: BOT_TOKEN is missing in .env")
if not OPENROUTER_API_KEY:
    print("⚠️ WARNING: OPENROUTER_API_KEY is missing in .env")

DEFAULT_CONFIG = {
    "must_join_channels": [
        {"name": "SHADOW_LEGION_2", "url": "https://t.me/SHADOW_LEGION_2"},
        {"name": "Access_required", "url": "https://t.me/Access_required"},
        {"name": "darknyteexodus", "url": "https://t.me/darknyteexodus"},
        {"name": "Crack_tools", "url": "https://t.me/exodus_inventory"},
        {"name": "YouTube", "url": "https://youtube.com/@exodus-m1i"},
        {"name": "AbdulBotzOfficial", "url": "https://t.me/AbdulBotzOfficial"}
    ],
    "admin_ids": [6831272320],
    "users_channel": "exodusgpt_users",
    "api_referrals_required": 20,
    "bot_referrals_required": 200,
    "access_hours": 24,
    "bot_username": "ExodusGPT_Bot",
    "ai_model": "google/gemini-3-flash-preview"
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    
    # Save default if not exists
    with open(CONFIG_FILE, 'w') as f:
        json.dump(DEFAULT_CONFIG, f, indent=2)
    return DEFAULT_CONFIG

def save_config(config_data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=2)

# Global config object
config = load_config()

# Extract common values for easy access
ADMIN_IDS = config.get("admin_ids", [6831272320])
MUST_JOIN_CHANNELS = config.get("must_join_channels", [])
USERS_CHANNEL = config.get("users_channel", "exodusgpt_users")
API_REFERRALS_REQUIRED = config.get("api_referrals_required", 20)
BOT_REFERRALS_REQUIRED = config.get("bot_referrals_required", 200)
ACCESS_HOURS = config.get("access_hours", 24)
