#!/usr/bin/env python3
"""
Telegram Session Manager
Allows switching between multiple Telegram accounts without re-entering phone numbers
"""

import os
import json
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from colorama import Fore, Style, init
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

# Initialize colorama
init(autoreset=True)

@dataclass
class SessionInfo:
    """Information about a saved session"""
    name: str
    phone_number: str
    api_id: int
    api_hash: str
    session_file: str
    user_id: Optional[int] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = False
    created_at: Optional[str] = None
    last_used: Optional[str] = None

class SessionManager:
    """Manages multiple Telegram sessions"""
    
    def __init__(self, sessions_dir: str = "sessions", config_file: str = "sessions_config.json"):
        self.sessions_dir = Path(sessions_dir)
        self.config_file = Path(config_file)
        self.sessions: Dict[str, SessionInfo] = {}
        self.current_session: Optional[str] = None
        
        # Create sessions directory if it doesn't exist
        self.sessions_dir.mkdir(exist_ok=True)
        
        # Load existing sessions
        self.load_sessions()
    
    def load_sessions(self) -> None:
        """Load sessions from config file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.sessions = {
                        name: SessionInfo(**info) 
                        for name, info in data.get('sessions', {}).items()
                    }
                    self.current_session = data.get('current_session')
                    print(f"{Fore.GREEN}✓ Loaded {len(self.sessions)} saved sessions{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.YELLOW}⚠ Warning: Could not load sessions config: {e}{Style.RESET_ALL}")
                self.sessions = {}
    
    def save_sessions(self) -> None:
        """Save sessions to config file"""
        try:
            data = {
                'sessions': {name: asdict(info) for name, info in self.sessions.items()},
                'current_session': self.current_session
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"{Fore.RED}✗ Error saving sessions config: {e}{Style.RESET_ALL}")
    
    def list_sessions(self) -> None:
        """Display all available sessions"""
        if not self.sessions:
            print(f"{Fore.YELLOW}No saved sessions found{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}📱 Available Telegram Sessions:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'No.':<4} {'Name':<15} {'Phone':<15} {'Username':<15} {'Status':<10}{Style.RESET_ALL}")
        print("-" * 70)
        
        for i, (name, info) in enumerate(self.sessions.items(), 1):
            status = "🟢 Active" if name == self.current_session else "⚪ Inactive"
            username = f"@{info.username}" if info.username else "(No username)"
            
            # Handle Unicode characters safely
            try:
                print(f"{i:<4} {name:<15} {info.phone_number:<15} {username:<15} {status:<10}")
            except UnicodeEncodeError:
                safe_name = name.encode('ascii', 'replace').decode('ascii')
                safe_username = username.encode('ascii', 'replace').decode('ascii')
                print(f"{i:<4} {safe_name:<15} {info.phone_number:<15} {safe_username:<15} {status:<10}")
    
    async def add_session(self, name: str, phone_number: str, api_id: int, api_hash: str) -> bool:
        """Add a new session by logging in"""
        if name in self.sessions:
            print(f"{Fore.RED}✗ Session '{name}' already exists{Style.RESET_ALL}")
            return False
        
        session_file = str(self.sessions_dir / f"{name}.session")
        
        try:
            print(f"{Fore.CYAN}🔐 Logging into Telegram account...{Style.RESET_ALL}")
            
            async with TelegramClient(session_file, api_id, api_hash) as client:
                # Start the client (this will prompt for phone and code)
                await client.start(phone=phone_number)
                
                # Get user information
                me = await client.get_me()
                
                # Create session info
                session_info = SessionInfo(
                    name=name,
                    phone_number=phone_number,
                    api_id=api_id,
                    api_hash=api_hash,
                    session_file=session_file,
                    user_id=me.id,
                    username=me.username,
                    first_name=me.first_name,
                    last_name=me.last_name,
                    created_at=str(asyncio.get_event_loop().time())
                )
                
                # Save session
                self.sessions[name] = session_info
                self.save_sessions()
                
                print(f"{Fore.GREEN}✓ Session '{name}' added successfully!{Style.RESET_ALL}")
                print(f"{Fore.GREEN}  User: {me.first_name} {me.last_name or ''} (@{me.username or 'no_username'}){Style.RESET_ALL}")
                return True
                
        except SessionPasswordNeededError:
            print(f"{Fore.RED}✗ Two-factor authentication is enabled. Please enter your password:{Style.RESET_ALL}")
            password = input(f"{Fore.CYAN}Password: {Style.RESET_ALL}")
            
            try:
                async with TelegramClient(session_file, api_id, api_hash) as client:
                    await client.start(phone=phone_number, password=password)
                    me = await client.get_me()
                    
                    session_info = SessionInfo(
                        name=name,
                        phone_number=phone_number,
                        api_id=api_id,
                        api_hash=api_hash,
                        session_file=session_file,
                        user_id=me.id,
                        username=me.username,
                        first_name=me.first_name,
                        last_name=me.last_name,
                        created_at=str(asyncio.get_event_loop().time())
                    )
                    
                    self.sessions[name] = session_info
                    self.save_sessions()
                    
                    print(f"{Fore.GREEN}✓ Session '{name}' added successfully!{Style.RESET_ALL}")
                    return True
            except Exception as e:
                print(f"{Fore.RED}✗ Failed to login with password: {e}{Style.RESET_ALL}")
                return False
                
        except PhoneCodeInvalidError:
            print(f"{Fore.RED}✗ Invalid verification code{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to add session: {e}{Style.RESET_ALL}")
            return False
    
    def switch_session(self, session_name: str) -> bool:
        """Switch to a different session"""
        if session_name not in self.sessions:
            print(f"{Fore.RED}✗ Session '{session_name}' not found{Style.RESET_ALL}")
            return False
        
        # Check if session file exists
        session_info = self.sessions[session_name]
        if not Path(session_info.session_file).exists():
            print(f"{Fore.RED}✗ Session file not found: {session_info.session_file}{Style.RESET_ALL}")
            return False
        
        # Update current session
        old_session = self.current_session
        self.current_session = session_name
        
        # Update last used time
        self.sessions[session_name].last_used = str(asyncio.get_event_loop().time())
        
        self.save_sessions()
        
        session_info = self.sessions[session_name]
        print(f"{Fore.GREEN}✓ Switched to session '{session_name}'{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  Account: {session_info.first_name} {session_info.last_name or ''} ({session_info.phone_number}){Style.RESET_ALL}")
        
        if old_session:
            print(f"{Fore.YELLOW}  Previous: {old_session}{Style.RESET_ALL}")
        
        return True
    
    def remove_session(self, session_name: str) -> bool:
        """Remove a session"""
        if session_name not in self.sessions:
            print(f"{Fore.RED}✗ Session '{session_name}' not found{Style.RESET_ALL}")
            return False
        
        session_info = self.sessions[session_name]
        
        # Confirm deletion
        confirm = input(f"{Fore.YELLOW}⚠ Delete session '{session_name}' ({session_info.phone_number})? (y/N): {Style.RESET_ALL}")
        if confirm.lower() != 'y':
            print(f"{Fore.YELLOW}Deletion cancelled{Style.RESET_ALL}")
            return False
        
        # Remove session file
        try:
            if Path(session_info.session_file).exists():
                Path(session_info.session_file).unlink()
        except Exception as e:
            print(f"{Fore.YELLOW}⚠ Warning: Could not delete session file: {e}{Style.RESET_ALL}")
        
        # Remove from sessions
        del self.sessions[session_name]
        
        # Update current session if it was the deleted one
        if self.current_session == session_name:
            self.current_session = None
        
        self.save_sessions()
        
        print(f"{Fore.GREEN}✓ Session '{session_name}' removed{Style.RESET_ALL}")
        return True
    
    def get_current_session(self) -> Optional[SessionInfo]:
        """Get current active session info"""
        if self.current_session and self.current_session in self.sessions:
            return self.sessions[self.current_session]
        return None
    
    async def get_client(self, session_name: Optional[str] = None) -> Optional[TelegramClient]:
        """Get a Telegram client for the specified or current session"""
        target_session = session_name or self.current_session
        
        if not target_session or target_session not in self.sessions:
            print(f"{Fore.RED}✗ No active session found{Style.RESET_ALL}")
            return None
        
        session_info = self.sessions[target_session]
        
        try:
            client = TelegramClient(
                session_info.session_file,
                session_info.api_id,
                session_info.api_hash
            )
            
            await client.start()
            return client
            
        except Exception as e:
            print(f"{Fore.RED}✗ Failed to connect with session '{target_session}': {e}{Style.RESET_ALL}")
            return None
    
    async def interactive_session_menu(self) -> None:
        """Interactive menu for session management"""
        while True:
            print(f"\n{Fore.CYAN}📱 Telegram Session Manager{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*40}{Style.RESET_ALL}")
            
            current = self.get_current_session()
            if current:
                print(f"{Fore.GREEN}Current: {current.name} ({current.phone_number}){Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}No active session{Style.RESET_ALL}")
            
            print(f"\n{Fore.CYAN}Options:{Style.RESET_ALL}")
            print("1. List all sessions")
            print("2. Add new session")
            print("3. Switch session")
            print("4. Remove session")
            print("5. Test current session")
            print("0. Exit")
            
            choice = input(f"\n{Fore.CYAN}Enter your choice (0-5): {Style.RESET_ALL}").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                self.list_sessions()
            elif choice == "2":
                await self._add_session_interactive()
            elif choice == "3":
                self._switch_session_interactive()
            elif choice == "4":
                self._remove_session_interactive()
            elif choice == "5":
                await self._test_session()
            else:
                print(f"{Fore.RED}Invalid choice!{Style.RESET_ALL}")
    
    async def _add_session_interactive(self) -> None:
        """Interactive session addition"""
        print(f"\n{Fore.CYAN}➕ Add New Session{Style.RESET_ALL}")
        
        name = input(f"{Fore.CYAN}Session name: {Style.RESET_ALL}").strip()
        if not name:
            print(f"{Fore.RED}Session name cannot be empty{Style.RESET_ALL}")
            return
        
        phone = input(f"{Fore.CYAN}Phone number (with country code): {Style.RESET_ALL}").strip()
        if not phone:
            print(f"{Fore.RED}Phone number cannot be empty{Style.RESET_ALL}")
            return
        
        try:
            api_id = int(input(f"{Fore.CYAN}API ID: {Style.RESET_ALL}").strip())
            api_hash = input(f"{Fore.CYAN}API Hash: {Style.RESET_ALL}").strip()
            
            if not api_hash:
                print(f"{Fore.RED}API Hash cannot be empty{Style.RESET_ALL}")
                return
            
            await self.add_session(name, phone, api_id, api_hash)
            
        except ValueError:
            print(f"{Fore.RED}Invalid API ID{Style.RESET_ALL}")
    
    def _switch_session_interactive(self) -> None:
        """Interactive session switching"""
        if not self.sessions:
            print(f"{Fore.YELLOW}No sessions available{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}🔄 Switch Session{Style.RESET_ALL}")
        self.list_sessions()
        
        session_name = input(f"\n{Fore.CYAN}Enter session name: {Style.RESET_ALL}").strip()
        if session_name:
            self.switch_session(session_name)
    
    def _remove_session_interactive(self) -> None:
        """Interactive session removal"""
        if not self.sessions:
            print(f"{Fore.YELLOW}No sessions available{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}🗑️ Remove Session{Style.RESET_ALL}")
        self.list_sessions()
        
        session_name = input(f"\n{Fore.CYAN}Enter session name to remove: {Style.RESET_ALL}").strip()
        if session_name:
            self.remove_session(session_name)
    
    async def _test_session(self) -> None:
        """Test current session connection"""
        current = self.get_current_session()
        if not current:
            print(f"{Fore.YELLOW}No active session to test{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}🧪 Testing session '{current.name}'...{Style.RESET_ALL}")
        
        try:
            client = await self.get_client()
            if client:
                me = await client.get_me()
                print(f"{Fore.GREEN}✓ Connection successful!{Style.RESET_ALL}")
                print(f"{Fore.GREEN}  User: {me.first_name} {me.last_name or ''} (@{me.username or 'no_username'}){Style.RESET_ALL}")
                print(f"{Fore.GREEN}  Phone: {me.phone}{Style.RESET_ALL}")
                await client.disconnect()
            else:
                print(f"{Fore.RED}✗ Connection failed{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}✗ Test failed: {e}{Style.RESET_ALL}")


async def main():
    """Main function for standalone session manager"""
    manager = SessionManager()
    await manager.interactive_session_menu()
    print(f"\n{Fore.CYAN}👋 Session Manager closed{Style.RESET_ALL}")


if __name__ == "__main__":
    asyncio.run(main())