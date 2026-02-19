import logging
from datetime import datetime
from bot_instance import bot
from config import MUST_JOIN_CHANNELS, ADMIN_IDS
from database import db

logger = logging.getLogger(__name__)

def check_channel_membership(user_id):
    """Check if user has joined all required channels"""
    for channel in MUST_JOIN_CHANNELS:
        url = channel["url"].lower()
        if "youtube.com" in url or "youtube.be" in url:
            continue
            
        try:
            # Extract username/id from URL
            if "t.me/" in url:
                target = url.split("t.me/")[-1]
                if target.startswith("+"):
                    # Private channel link, can't easily check with get_chat_member
                    # unless bot is in the channel and we have the ID.
                    # For now, skip or assume okay if we can't check.
                    continue
                
                if not target.startswith("@"):
                    target = f"@{target}"
                
                member = bot.get_chat_member(target, user_id)
                if member.status in ['left', 'kicked']:
                    return False
        except Exception as e:
            logger.error(f"Error checking channel {channel.get('name')}: {e}")
            # If we can't check (e.g. bot not admin), don't block user?
            # Or block them? The original code continued on error but returned False on some.
            continue
            
    return True

def get_time_remaining(user_id):
    user = db.get_user(user_id)
    if not user or not user.get('access_expiry'):
        return "No access"
    
    try:
        expiry = datetime.fromisoformat(user['access_expiry'].replace('Z', '+00:00'))
        if expiry <= datetime.now():
            return "Expired"
        
        remaining = expiry - datetime.now()
        hours = remaining.days * 24 + remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    except Exception:
        return "Error"

def is_admin(user_id):
    return user_id in ADMIN_IDS

def split_message(text, max_length=4000):
    """Split a long message into chunks for Telegram"""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        
        # Find the last newline within the limit to split cleanly
        split_at = text.rfind('\n', 0, max_length)
        if split_at == -1:
            split_at = max_length
            
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip()
        
    return chunks
