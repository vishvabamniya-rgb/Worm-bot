from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot_instance import bot
from database import db
from config import MUST_JOIN_CHANNELS, ACCESS_HOURS, API_REFERRALS_REQUIRED, BOT_REFERRALS_REQUIRED
from utils import check_channel_membership, get_time_remaining
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def register_user_handlers(bot):
    @bot.message_handler(commands=['start'])
    def start_command(message):
        user_id = message.from_user.id
        username = message.from_user.username or ""
        first_name = message.from_user.first_name or ""
        last_name = message.from_user.last_name or ""
        
        user = db.get_user(user_id)
        if user and user.get('is_banned'):
            bot.reply_to(message, f"🚫 <b>You are banned!</b>\nReason: {user.get('ban_reason', 'No reason')}")
            return
        
        db.add_user(user_id, username, first_name, last_name)
        db.update_user(user_id, last_active=datetime.now().isoformat())
        
        # Handle referral
        if len(message.text.split()) > 1:
            referral_code = message.text.split()[1]
            all_users = db.get_all_users()
            for u in all_users:
                if u['referral_code'] == referral_code and u['user_id'] != user_id:
                    if db.add_referral(u['user_id'], user_id):
                        try:
                            bot.send_message(u['user_id'], 
                                f"🎉 <b>Referral Successful!</b>\n👤 New user: @{username}\n✅ You got +24 hours access!")
                        except Exception:
                            pass
                    break
        
        if check_channel_membership(user_id):
            db.update_user(user_id, joined_channels=len(MUST_JOIN_CHANNELS))
            
            markup = InlineKeyboardMarkup(row_width=2)
            for channel in MUST_JOIN_CHANNELS:
                markup.add(InlineKeyboardButton(f"📢 {channel['name']}", url=channel['url']))
            markup.add(InlineKeyboardButton("🔄 Verify", callback_data=f"verify_{user_id}"))
            
            bot.reply_to(message,
                f"👋 <b>Welcome {first_name} to EXODUSGPT!</b>\n\n"
                "✅ <b>Access Granted!</b>\n\n"
                "🎯 <b>Commands:</b>\n"
                "• /status - Check status\n"
                "• /api - Get API\n"
                "• /buybot - Get custom bot\n"
                "• /admin - Admin panel\n\n"
                f"⏰ <b>Free Access:</b> {ACCESS_HOURS} hours\n\n"
                "💬 <b>Ask WormGPT anything - NO LIMITS!</b>",
                reply_markup=markup
            )
        else:
            db.update_user(user_id, joined_channels=0)
            
            markup = InlineKeyboardMarkup(row_width=2)
            for channel in MUST_JOIN_CHANNELS:
                markup.add(InlineKeyboardButton(f"📢 {channel['name']}", url=channel['url']))
            markup.add(InlineKeyboardButton("✅ I've Joined All", callback_data=f"verify_{user_id}"))
            
            channels_text = "\n".join([f"• {channel['name']}" for channel in MUST_JOIN_CHANNELS])
            
            bot.reply_to(message,
                f"👋 <b>Welcome {first_name} to EXODUSGPT!</b>\n\n"
                "⚠️ <b>Join these channels to continue:</b>\n\n"
                f"{channels_text}\n\n"
                "<b>After joining, click the button below:</b>",
                reply_markup=markup
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("verify_"))
    def verify_membership_callback(call):
        user_id = int(call.data.split("_")[1])
        if call.from_user.id != user_id:
            bot.answer_callback_query(call.id, "❌ Not your button!", show_alert=True)
            return
        
        if check_channel_membership(user_id):
            db.update_user(user_id, joined_channels=len(MUST_JOIN_CHANNELS))
            bot.answer_callback_query(call.id, "✅ Verified! Access granted!")
            bot.send_message(user_id, "✅ <b>Access Granted!</b>\n🔥 <b>WormGPT is ready!</b>\n💬 Ask anything!")
        else:
            bot.answer_callback_query(call.id, "❌ You haven't joined all channels!", show_alert=True)

    @bot.message_handler(commands=['status'])
    def status_command(message):
        user_id = message.from_user.id
        user = db.get_user(user_id)
        if not user:
            bot.reply_to(message, "❌ Use /start first")
            return
        
        # Check access
        has_access = False
        if user.get('access_expiry'):
            try:
                expiry = datetime.fromisoformat(user['access_expiry'].replace('Z', '+00:00'))
                has_access = expiry > datetime.now() and user.get('joined_channels', 0) >= len(MUST_JOIN_CHANNELS)
            except Exception:
                pass
        
        status_msg = (
            f"👤 <b>USER STATUS</b>\n"
            f"├─ Name: {user['first_name']} {user['last_name']}\n"
            f"├─ ID: {user_id}\n\n"
            f"⏰ <b>ACCESS</b>\n"
            f"├─ Status: {'✅ ACTIVE' if has_access else '❌ INACTIVE'}\n"
            f"├─ Time Left: {get_time_remaining(user_id)}\n\n"
            f"📊 <b>REFERRALS</b>\n"
            f"├─ Total: {user.get('referral_count', 0)}\n\n"
            f"🔗 <b>YOUR REFERRAL LINK:</b>\n"
            f"https://t.me/{bot.get_me().username}?start={user['referral_code']}"
        )
        bot.reply_to(message, status_msg)

    @bot.message_handler(commands=['api'])
    def api_command(message):
        user_id = message.from_user.id
        user = db.get_user(user_id)
        if not user: return
        
        refs = user.get('referral_count', 0)
        if refs < API_REFERRALS_REQUIRED:
            bot.reply_to(message, f"❌ Need {API_REFERRALS_REQUIRED} referrals. You have {refs}.")
            return
        
        if user.get('api_token'):
            bot.reply_to(message, f"✅ Your API Token: <code>{user['api_token']}</code>")
        else:
            bot.reply_to(message, "⏳ API token pending admin approval.")

    @bot.message_handler(commands=['buybot'])
    def buybot_command(message):
        user_id = message.from_user.id
        user = db.get_user(user_id)
        if not user: return
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("💰 Buy for $10", url="https://t.me/D4RkNYTEAdmin"))
        bot.reply_to(message, "🤖 <b>GET YOUR OWN BOT</b>\nContact @D4RkNYTEAdmin", reply_markup=markup)
