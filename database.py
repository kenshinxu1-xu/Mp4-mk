import json
import os
from typing import Dict, List, Optional
from datetime import datetime
import pytz

class UserDatabase:
    def __init__(self, filename='user_data.json'):
        self.filename = filename
        self.users = self.load_data()
    
    def load_data(self) -> Dict:
        """Load user data from file"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_data(self):
        """Save user data to file"""
        with open(self.filename, 'w') as f:
            json.dump(self.users, f, indent=2)
    
    def add_user(self, user_id: int, username: str = None, first_name: str = None):
        """Add or update user"""
        user_id = str(user_id)
        if user_id not in self.users:
            self.users[user_id] = {
                'username': username,
                'first_name': first_name,
                'joined_date': datetime.now(pytz.UTC).isoformat(),
                'last_active': datetime.now(pytz.UTC).isoformat(),
                'favorites': [],
                'history': [],
                'settings': {
                    'source': 'gogoanime',
                    'quality': '720p',
                    'language': 'sub',
                    'notifications': True
                }
            }
        else:
            self.users[user_id]['last_active'] = datetime.now(pytz.UTC).isoformat()
            self.users[user_id]['username'] = username
            self.users[user_id]['first_name'] = first_name
        
        self.save_data()
        return self.users[user_id]
    
    def add_to_history(self, user_id: int, anime_name: str, episode: int = None):
        """Add anime to user history"""
        user_id = str(user_id)
        if user_id in self.users:
            history_item = {
                'anime': anime_name,
                'episode': episode,
                'timestamp': datetime.now(pytz.UTC).isoformat()
            }
            
            if 'history' not in self.users[user_id]:
                self.users[user_id]['history'] = []
            
            # Add to beginning, keep last 50
            self.users[user_id]['history'].insert(0, history_item)
            self.users[user_id]['history'] = self.users[user_id]['history'][:50]
            self.save_data()
    
    def toggle_favorite(self, user_id: int, anime_name: str) -> bool:
        """Toggle favorite status"""
        user_id = str(user_id)
        if user_id in self.users:
            if 'favorites' not in self.users[user_id]:
                self.users[user_id]['favorites'] = []
            
            if anime_name in self.users[user_id]['favorites']:
                self.users[user_id]['favorites'].remove(anime_name)
                is_favorite = False
            else:
                self.users[user_id]['favorites'].append(anime_name)
                is_favorite = True
            
            self.save_data()
            return is_favorite
    
    def update_settings(self, user_id: int, **kwargs):
        """Update user settings"""
        user_id = str(user_id)
        if user_id in self.users:
            if 'settings' not in self.users[user_id]:
                self.users[user_id]['settings'] = {}
            
            self.users[user_id]['settings'].update(kwargs)
            self.save_data()
            return True
        return False

# Global database instance
db = UserDatabase()
