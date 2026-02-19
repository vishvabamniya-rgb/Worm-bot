from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from bot_instance import bot
from database import db
from config import ADMIN_IDS, MUST_JOIN_CHANNELS, USERS_CHANNEL, load_config, save_config
from utils import is_admin
import logging
import time

logger = logging.getLogger(__name__)

# User States for Admin Panel
user_states = {}

def register_admin_handlers(bot):
    @bot.message_handler(commands=['admin'])
    def admin_command(message):
        user_id = message.from_user.id
        if not is_admin(user_id):
            bot.reply_to(message, "🚫 Access denied!")
            return
        
        user_states.pop(user_id, None)
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton("📊 Statistics"),
            KeyboardButton("👥 All Users"),
            KeyboardButton("📢 Channels"),
            KeyboardButton("👑 Admins")
        )
        markup.add(
            KeyboardButton("🚫 Ban User"),
            KeyboardButton("✅ Unban User"),
            KeyboardButton("🔧 API Users"),
            KeyboardButton("📝 Broadcast")
        )
        markup.add(
            KeyboardButton("⚙️ Settings"),
            KeyboardButton("➕ Add Admin"),
            KeyboardButton("➖ Remove Admin"),
            KeyboardButton("❌ Close")
        )
        
        bot.send_message(user_id, "🛠️ <b>ADMIN PANEL</b>", reply_markup=markup)

    @bot.message_handler(func=lambda message: message.text in [
        "📊 Statistics", "👥 All Users", "📢 Channels", "👑 Admins",
        "🚫 Ban User", "✅ Unban User", "🔧 API Users", "📝 Broadcast",
        "⚙️ Settings", "➕ Add Admin", "➖ Remove Admin", "❌ Close",
        "Change Model", "Change Referrals", "Change Hours", "Back to Admin"
    ])
    def handle_admin_panel(message):
        user_id = message.from_user.id
        if not is_admin(user_id): return
        
        if message.text == "❌ Close":
            bot.send_message(user_id, "❌ Closed", reply_markup=ReplyKeyboardRemove())
            return
        
        if message.text == "📊 Statistics":
            stats = db.get_statistics(len(MUST_JOIN_CHANNELS))
            bot.send_message(user_id, f"📊 <b>STATS</b>\nTotal Users: {stats['total_users']}\nMessages: {stats['total_messages']}\nReferrals: {stats['total_referrals']}")
        
        elif message.text == "👥 All Users":
            users = db.get_all_users()
            msg = "👥 <b>ALL USERS (Last 10)</b>\n"
            for u in users[:10]:
                msg += f"• {u['first_name']} (@{u['username']}) - ID: {u['user_id']}\n"
            bot.send_message(user_id, msg)

        elif message.text == "📢 Channels":
            msg = "📢 <b>CHANNELS</b>\n"
            for c in MUST_JOIN_CHANNELS:
                msg += f"• {c['name']}: {c['url']}\n"
            bot.send_message(user_id, msg)

        elif message.text == "👑 Admins":
            bot.send_message(user_id, f"👑 <b>ADMINS</b>\n{', '.join(map(str, ADMIN_IDS))}")

        elif message.text == "🚫 Ban User":
            user_states[user_id] = {"action": "ban"}
            bot.send_message(user_id, "Enter User ID to ban:")
            
        elif message.text == "✅ Unban User":
            user_states[user_id] = {"action": "unban"}
            bot.send_message(user_id, "Enter User ID to unban:")

        elif message.text == "📝 Broadcast":
            user_states[user_id] = {"action": "broadcast"}
            bot.send_message(user_id, "Enter broadcast message:")
            
        elif message.text == "➕ Add Admin":
            user_states[user_id] = {"action": "add_admin"}
            bot.send_message(user_id, "Enter User ID to add as admin:")

        elif message.text == "➖ Remove Admin":
            user_states[user_id] = {"action": "remove_admin"}
            bot.send_message(user_id, "Enter User ID to remove from admins:")

        elif message.text == "⚙️ Settings":
            config = load_config()
            msg = "⚙️ <b>SETTINGS</b>\n\n"
            msg += f"🤖 Model: <code>{config.get('ai_model', 'N/A')}</code>\n"
            msg += f"🔑 API Referrals: <code>{config.get('api_referrals_required', 0)}</code>\n"
            msg += f"🕒 Access Hours: <code>{config.get('access_hours', 0)}</code>\n\n"
            msg += "Select setting to change:"
            
            markup = ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("Change Model", "Change Referrals", "Change Hours", "Back to Admin")
            bot.send_message(user_id, msg, reply_markup=markup)

        elif message.text == "Back to Admin":
            admin_command(message)

        elif message.text == "Change Model":
            user_states[user_id] = {"action": "set_model"}
            bot.send_message(user_id, "Enter new model ID (e.g., google/gemini-3-flash-preview):")

        elif message.text == "Change Referrals":
            user_states[user_id] = {"action": "set_referrals"}
            bot.send_message(user_id, "Enter number of referrals required:")

        elif message.text == "Change Hours":
            user_states[user_id] = {"action": "set_hours"}
            bot.send_message(user_id, "Enter number of access hours:")

    @bot.message_handler(func=lambda m: m.from_user.id in user_states)
    def handle_admin_states(message):
        user_id = message.from_user.id
        state = user_states[user_id]
        
        if state["action"] == "ban":
            try:
                target_id = int(message.text)
                if db.ban_user(target_id):
                    bot.send_message(user_id, f"✅ User {target_id} banned")
                else:
                    bot.send_message(user_id, "❌ Failed")
            except: bot.send_message(user_id, "❌ Invalid ID")
            user_states.pop(user_id)
            
        elif state["action"] == "unban":
            try:
                target_id = int(message.text)
                if db.unban_user(target_id):
                    bot.send_message(user_id, f"✅ User {target_id} unbanned")
                else:
                    bot.send_message(user_id, "❌ Failed")
            except: bot.send_message(user_id, "❌ Invalid ID")
            user_states.pop(user_id)

        elif state["action"] == "add_admin":
            try:
                target_id = int(message.text)
                config = load_config()
                if target_id not in config["admin_ids"]:
                    config["admin_ids"].append(target_id)
                    save_config(config)
                    ADMIN_IDS.append(target_id)
                    bot.send_message(user_id, f"✅ Admin {target_id} added")
                else:
                    bot.send_message(user_id, "❌ Already admin")
            except: bot.send_message(user_id, "❌ Invalid ID")
            user_states.pop(user_id)

        elif state["action"] == "remove_admin":
            try:
                target_id = int(message.text)
                config = load_config()
                if target_id in config["admin_ids"]:
                    config["admin_ids"].remove(target_id)
                    save_config(config)
                    if target_id in ADMIN_IDS: ADMIN_IDS.remove(target_id)
                    bot.send_message(user_id, f"✅ Admin {target_id} removed")
                else:
                    bot.send_message(user_id, "❌ Not admin")
            except: bot.send_message(user_id, "❌ Invalid ID")
            user_states.pop(user_id)
            
        elif state["action"] == "broadcast":
            users = db.get_all_users()
            sent = 0
            for u in users:
                try:
                    bot.send_message(u['user_id'], message.text)
                    sent += 1
                    time.sleep(0.05)
                except:
                    pass
            bot.send_message(user_id, f"✅ Sent to {sent} users")
            user_states.pop(user_id)

        elif state["action"] == "set_model":
            config = load_config()
            config["ai_model"] = message.text.strip()
            save_config(config)
            bot.send_message(user_id, f"✅ Model set to: {message.text}")
            user_states.pop(user_id)
            admin_command(message)

        elif state["action"] == "set_referrals":
            try:
                num = int(message.text)
                config = load_config()
                config["api_referrals_required"] = num
                save_config(config)
                bot.send_message(user_id, f"✅ Referrals set to: {num}")
            except: bot.send_message(user_id, "❌ Invalid number")
            user_states.pop(user_id)
            admin_command(message)

        elif state["action"] == "set_hours":
            try:
                num = int(message.text)
                config = load_config()
                config["access_hours"] = num
                save_config(config)
                bot.send_message(user_id, f"✅ Hours set to: {num}")
            except: bot.send_message(user_id, "❌ Invalid number")
            user_states.pop(user_id)
            admin_command(message)
