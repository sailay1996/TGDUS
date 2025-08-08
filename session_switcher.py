#!/usr/bin/env python3
"""
Telegram Session Switcher
Easily switch between different Telegram accounts for downloading or uploading
"""

import asyncio
import os
import sys
from pathlib import Path
from colorama import Fore, Style, init

# Add src directory to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.append(src_path)

from session_manager import SessionManager

# Initialize colorama
init(autoreset=True)


def display_header():
    """Display application header"""
    print(f"{Fore.CYAN}🔄 Telegram Session Switcher{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*35}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}Switch between your Telegram accounts easily{Style.RESET_ALL}")
    print()


async def main_menu():
    """Main application menu"""
    session_manager = SessionManager()
    
    while True:
        display_header()
        
        # Show current session
        current = session_manager.get_current_session()
        if current:
            print(f"{Fore.GREEN}📱 Current Account: {current.first_name} {current.last_name or ''} ({current.phone_number}){Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}📱 No active session{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}What would you like to do?{Style.RESET_ALL}")
        print("1. 📤 Upload files (current session)")
        print("2. 📥 Download files (current session)")
        print("3. 🔄 Switch to different account")
        print("4. ➕ Add new account")
        print("5. ⚙️  Manage sessions")
        print("0. 🚪 Exit")
        
        choice = input(f"\n{Fore.CYAN}Enter your choice (0-5): {Style.RESET_ALL}").strip()
        
        if choice == "0":
            print(f"{Fore.YELLOW}Goodbye! 👋{Style.RESET_ALL}")
            break
        elif choice == "1":
            if current:
                await run_uploader()
            else:
                print(f"{Fore.RED}❌ No active session. Please switch to an account first.{Style.RESET_ALL}")
                input("Press Enter to continue...")
        elif choice == "2":
            if current:
                await run_downloader()
            else:
                print(f"{Fore.RED}❌ No active session. Please switch to an account first.{Style.RESET_ALL}")
                input("Press Enter to continue...")
        elif choice == "3":
            await switch_session(session_manager)
        elif choice == "4":
            await add_new_session(session_manager)
        elif choice == "5":
            await session_manager.interactive_session_menu()
        else:
            print(f"{Fore.RED}❌ Invalid choice!{Style.RESET_ALL}")
            input("Press Enter to continue...")


async def switch_session(session_manager):
    """Switch to a different session"""
    print(f"\n{Fore.CYAN}🔄 Switch Account{Style.RESET_ALL}")
    
    if not session_manager.sessions:
        print(f"{Fore.YELLOW}📭 No sessions available. Add a session first.{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return
    
    print(f"\n{Fore.CYAN}Available accounts:{Style.RESET_ALL}")
    session_manager.list_sessions()
    
    session_name = input(f"\n{Fore.CYAN}Enter session name to switch to: {Style.RESET_ALL}").strip()
    
    if session_name and session_manager.switch_session(session_name):
        new_session = session_manager.get_current_session()
        print(f"{Fore.GREEN}✅ Switched to: {new_session.first_name} {new_session.last_name or ''} ({new_session.phone_number}){Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}❌ Failed to switch to '{session_name}'{Style.RESET_ALL}")
    
    input("Press Enter to continue...")


async def add_new_session(session_manager):
    """Add a new session interactively"""
    print(f"\n{Fore.CYAN}➕ Add New Account{Style.RESET_ALL}")
    
    name = input(f"{Fore.CYAN}Session name (e.g., 'personal', 'work'): {Style.RESET_ALL}").strip()
    if not name:
        print(f"{Fore.RED}❌ Session name cannot be empty{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return
    
    phone = input(f"{Fore.CYAN}Phone number (with country code, e.g., +1234567890): {Style.RESET_ALL}").strip()
    if not phone:
        print(f"{Fore.RED}❌ Phone number cannot be empty{Style.RESET_ALL}")
        input("Press Enter to continue...")
        return
    
    try:
        api_id = int(input(f"{Fore.CYAN}API ID: {Style.RESET_ALL}").strip())
        api_hash = input(f"{Fore.CYAN}API Hash: {Style.RESET_ALL}").strip()
        
        if not api_hash:
            print(f"{Fore.RED}❌ API Hash cannot be empty{Style.RESET_ALL}")
            input("Press Enter to continue...")
            return
        
        print(f"{Fore.YELLOW}🔄 Adding session and connecting...{Style.RESET_ALL}")
        success = await session_manager.add_session(name, phone, api_id, api_hash)
        
        if success:
            # Automatically switch to the new session
            session_manager.switch_session(name)
            print(f"{Fore.GREEN}✅ Account added and activated successfully!{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ Failed to add session{Style.RESET_ALL}")
        
    except ValueError:
        print(f"{Fore.RED}❌ Invalid API ID{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}❌ Error adding session: {e}{Style.RESET_ALL}")
    
    input("Press Enter to continue...")


async def run_uploader():
    """Run the uploader with current session"""
    print(f"\n{Fore.GREEN}🚀 Starting uploader...{Style.RESET_ALL}")
    
    # Check if original uploader exists
    uploader_path = os.path.join('src', 'uploader.py')
    if os.path.exists(uploader_path):
        try:
            # Import and run the original uploader
            from src.uploader import main as uploader_main
            await uploader_main()
        except Exception as e:
            print(f"{Fore.RED}❌ Error running uploader: {e}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}💡 Try running: python src/uploader.py{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}❌ Uploader not found at {uploader_path}{Style.RESET_ALL}")
    
    input("Press Enter to continue...")


async def run_downloader():
    """Run the downloader with current session"""
    print(f"\n{Fore.GREEN}🚀 Starting downloader...{Style.RESET_ALL}")
    
    # Check if downloader exists
    downloader_path = os.path.join('src', 'downloder.py')
    if os.path.exists(downloader_path):
        try:
            # Import and run the downloader
            from src.downloder import main as downloader_main
            await downloader_main()
        except Exception as e:
            print(f"{Fore.RED}❌ Error running downloader: {e}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}💡 Try running: python src/downloder.py{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}❌ Downloader not found at {downloader_path}{Style.RESET_ALL}")
    
    input("Press Enter to continue...")


def show_help():
    """Show help information"""
    print(f"{Fore.CYAN}📖 How to use Session Switcher:{Style.RESET_ALL}")
    print()
    print(f"{Fore.YELLOW}1. Add your accounts:{Style.RESET_ALL}")
    print("   - Get API credentials from https://my.telegram.org")
    print("   - Add each account with a unique name")
    print()
    print(f"{Fore.YELLOW}2. Switch between accounts:{Style.RESET_ALL}")
    print("   - Select 'Switch to different account'")
    print("   - Choose from your saved accounts")
    print()
    print(f"{Fore.YELLOW}3. Use uploader/downloader:{Style.RESET_ALL}")
    print("   - Current active account will be used")
    print("   - Switch accounts anytime without re-authentication")
    print()
    print(f"{Fore.GREEN}💡 Benefits:{Style.RESET_ALL}")
    print("   ✅ No need to re-enter phone numbers")
    print("   ✅ Quick switching between accounts")
    print("   ✅ Access different channels per account")
    print("   ✅ Persistent session storage")


if __name__ == "__main__":
    try:
        # Show help on first run
        if len(sys.argv) > 1 and sys.argv[1] == "--help":
            show_help()
        else:
            asyncio.run(main_menu())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}👋 Goodbye!{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}❌ Unexpected error: {e}{Style.RESET_ALL}")