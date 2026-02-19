import sqlite3
import time
import logging
from datetime import datetime, timedelta
from config import DB_FILE, ACCESS_HOURS

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # This allows accessing columns by name
        self.create_tables()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                referral_count INTEGER DEFAULT 0,
                api_access INTEGER DEFAULT 0,
                api_token TEXT,
                bot_access INTEGER DEFAULT 0,
                access_expiry TIMESTAMP,
                joined_channels INTEGER DEFAULT 0,
                message_count INTEGER DEFAULT 0,
                is_banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                banned_at TIMESTAMP
            )
        ''')
        
        # Admin actions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_actions (
                action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                action_type TEXT,
                target_id INTEGER,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Referrals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                referral_id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                referred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status INTEGER DEFAULT 1,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                FOREIGN KEY (referred_id) REFERENCES users (user_id)
            )
        ''')
        
        # Messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message_text TEXT,
                response_text TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name, last_name="", referral_code=None):
        cursor = self.conn.cursor()
        if not referral_code:
            referral_code = f"EX{user_id}_{int(time.time())}"
        
        try:
            user_id = int(user_id) # Ensure int
            cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
            if cursor.fetchone():
                return True
            
            # Ensure access_hours is int
            hrs = int(ACCESS_HOURS)
            expiry = (datetime.now() + timedelta(hours=hrs)).isoformat()
            
            cursor.execute('''
                INSERT INTO users 
                (user_id, username, first_name, last_name, referral_code, access_expiry) 
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, username, first_name, last_name, referral_code, expiry))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding user {user_id}: {str(e)}", exc_info=True)
            return False
    
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_user(self, user_id, **kwargs):
        try:
            cursor = self.conn.cursor()
            set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values())
            values.append(user_id)
            query = f"UPDATE users SET {set_clause} WHERE user_id = ?"
            cursor.execute(query, values)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return False
    
    def ban_user(self, user_id, reason="No reason provided"):
        return self.update_user(user_id, is_banned=1, ban_reason=reason, banned_at=datetime.now().isoformat())
    
    def unban_user(self, user_id):
        return self.update_user(user_id, is_banned=0, ban_reason=None, banned_at=None)
    
    def add_referral(self, referrer_id, referred_id):
        try:
            cursor = self.conn.cursor()
            # Check if referral already exists
            cursor.execute('SELECT referral_id FROM referrals WHERE referrer_id = ? AND referred_id = ?', 
                          (referrer_id, referred_id))
            if cursor.fetchone():
                return True
            
            # Add referral
            cursor.execute('INSERT INTO referrals (referrer_id, referred_id) VALUES (?, ?)', (referrer_id, referred_id))
            
            # Update referral count
            cursor.execute('UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?', (referrer_id,))
            
            # Extend access
            cursor.execute('''
                UPDATE users 
                SET access_expiry = CASE 
                    WHEN access_expiry <= datetime('now') OR access_expiry IS NULL 
                    THEN datetime('now', '+24 hours')
                    ELSE datetime(access_expiry, '+24 hours')
                END
                WHERE user_id = ?
            ''', (referrer_id,))
            
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding referral: {e}")
            return False
    
    def add_message(self, user_id, message_text, response_text):
        try:
            cursor = self.conn.cursor()
            cursor.execute('INSERT INTO messages (user_id, message_text, response_text) VALUES (?, ?, ?)', 
                          (user_id, message_text, response_text))
            cursor.execute('UPDATE users SET message_count = message_count + 1 WHERE user_id = ?', (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return False
    
    def get_chat_history(self, user_id, limit=5):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT message_text, response_text 
                FROM messages 
                WHERE user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            ''', (user_id, limit))
            rows = cursor.fetchall()
            return [{"user": row['message_text'], "assistant": row['response_text']} for row in reversed(rows)]
        except Exception as e:
            logger.error(f"Error fetching chat history: {e}")
            return []

    def get_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users ORDER BY joined_at DESC')
        return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self, must_join_count):
        cursor = self.conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE last_active > datetime('now', '-24 hours') AND is_banned = 0")
        active_users = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE (access_expiry <= datetime('now') OR joined_channels < ?) AND is_banned = 0", (must_join_count,))
        needs_ref = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM referrals')
        total_referrals = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM messages')
        total_messages = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_banned = 1')
        banned_users = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE date(joined_at) = date('now')")
        new_today = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE api_token IS NOT NULL')
        api_users = cursor.fetchone()[0] or 0
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'needs_ref': needs_ref,
            'total_referrals': total_referrals,
            'total_messages': total_messages,
            'banned_users': banned_users,
            'new_today': new_today,
            'api_users': api_users
        }

db = Database()
