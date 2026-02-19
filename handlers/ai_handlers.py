from bot_instance import bot
from database import db
from ai_service import call_wormgpt_api
from utils import check_channel_membership, get_time_remaining, split_message
from config import MUST_JOIN_CHANNELS
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def register_ai_handlers(bot):
    @bot.message_handler(func=lambda message: True)
    def handle_ai_request(message):
        user_id = message.from_user.id
        
        # Skip if it's a command (already handled)
        if message.text and message.text.startswith('/'):
            return
            
        user = db.get_user(user_id)
        if not user:
            try: bot.send_message(user_id, "❌ Use /start first")
            except: pass
            return
            
        if user.get('is_banned'):
            return
            
        # Check channel and access
        if not check_channel_membership(user_id):
            try: bot.send_message(user_id, "❌ Join all channels first! Use /start")
            except: pass
            return
            
        has_access = False
        if user.get('access_expiry'):
            try:
                expiry = datetime.fromisoformat(user['access_expiry'].replace('Z', '+00:00'))
                has_access = expiry > datetime.now()
            except Exception:
                pass
                
        if not has_access:
            try: bot.send_message(user_id, "🚫 <b>ACCESS EXPIRED!</b>\nRefer someone to get +24h access.")
            except: pass
            return
            
        # Update last active
        db.update_user(user_id, last_active=datetime.now().isoformat())
        
        # Immediate feedback
        waiting_msg = bot.reply_to(message, "⚡ <b>ExodusGPT is thinking...</b>")
        bot.send_chat_action(user_id, 'typing')
        
        try:
            # Get last 5 messages for context
            history = db.get_chat_history(user_id, limit=5)
            response = call_wormgpt_api(message.text, history=history)
            
            # Append timer
            timer_msg = f"⏰ <b>Access Left:</b> {get_time_remaining(user_id)}\n\n"
            full_response = timer_msg + response
            
            # Split if too long
            chunks = split_message(full_response)
            
            # Update the waiting message with the first chunk
            try:
                bot.edit_message_text(chunks[0], user_id, waiting_msg.message_id)
            except Exception:
                bot.send_message(user_id, chunks[0])
            
            # Send remaining chunks if any
            if len(chunks) > 1:
                for chunk in chunks[1:]:
                    try: bot.send_message(user_id, chunk)
                    except: pass
                
            db.add_message(user_id, message.text, response)
            
        except Exception as e:
            logger.error(f"AI interaction error: {e}")
            try: bot.send_message(user_id, "⚠️ Something went wrong. Try again.")
            except: pass
