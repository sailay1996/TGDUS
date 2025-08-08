#!/usr/bin/env python3
"""
Telegram Multi-Session Uploader
Upload files to Telegram with support for multiple accounts
"""

import asyncio
import os
import json
from pathlib import Path
from colorama import Fore, Style, init
from tqdm.asyncio import tqdm
from telethon import TelegramClient
from telethon.tl.types import (
    Channel,
    Chat,
    DocumentAttributeFilename,
)

# Import our session manager
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from session_manager import SessionManager, SessionInfo

# Initialize colorama
init(autoreset=True)


def save_upload_state(uploaded_files, state_file="upload_state.json"):
    """Save uploaded file paths to JSON file"""
    try:
        with open(state_file, 'w') as f:
            json.dump(list(uploaded_files), f)
    except Exception as e:
        print(f"{Fore.YELLOW}Warning: Could not save upload state: {e}{Style.RESET_ALL}")


def load_upload_state(state_file="upload_state.json"):
    """Load uploaded file paths from JSON file"""
    try:
        with open(state_file, 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()
    except Exception as e:
        print(f"{Fore.YELLOW}Warning: Could not load upload state: {e}{Style.RESET_ALL}")
        return set()


def get_files_from_folder(folder_path, file_types=None):
    """Get all files from folder based on file types"""
    files = []
    
    if not os.path.exists(folder_path):
        print(f"{Fore.RED}Folder does not exist: {folder_path}{Style.RESET_ALL}")
        return files
    
    for root, dirs, filenames in os.walk(folder_path):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            
            # Skip state files
            if filename.endswith('_state.json'):
                continue
                
            # Filter by file types if specified
            if file_types:
                file_ext = os.path.splitext(filename)[1].lower()
                if file_ext not in file_types:
                    continue
            
            files.append(file_path)
    
    return files


async def list_user_channels(client):
    """List all channels and groups the user has access to"""
    print(f"{Fore.YELLOW}Fetching your channels and groups...{Style.RESET_ALL}")
    
    dialogs = await client.get_dialogs()
    channels = []
    
    for dialog in dialogs:
        entity = dialog.entity
        if isinstance(entity, (Channel, Chat)):
            # Check if user has admin rights or can send messages
            try:
                permissions = dialog.entity.default_banned_rights
                can_send = not (permissions and permissions.send_media)
                
                if can_send or hasattr(entity, 'creator') or hasattr(entity, 'admin_rights'):
                    channels.append({
                        'title': entity.title,
                        'username': entity.username if hasattr(entity, 'username') else None,
                        'id': entity.id,
                        'type': 'Channel' if isinstance(entity, Channel) else 'Group'
                    })
            except:
                # If we can't check permissions, include it anyway
                channels.append({
                    'title': entity.title,
                    'username': entity.username if hasattr(entity, 'username') else None,
                    'id': entity.id,
                    'type': 'Channel' if isinstance(entity, Channel) else 'Group'
                })
    
    return channels


async def display_and_select_upload_target(client):
    """Display available channels and let user select one for upload"""
    channels = await list_user_channels(client)
    
    if not channels:
        print(f"{Fore.RED}No channels or groups found where you can upload!{Style.RESET_ALL}")
        return None
    
    print(f"\n{Fore.CYAN}Available channels and groups for upload:{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'No.':<4} {'Type':<8} {'Title':<30} {'Username':<20}{Style.RESET_ALL}")
    print("-" * 70)
    
    for i, channel in enumerate(channels, 1):
        username_display = f"@{channel['username']}" if channel['username'] else "(Private)"
        title_display = channel['title'][:28] + ".." if len(channel['title']) > 30 else channel['title']
        
        # Handle Unicode characters safely
        try:
            print(f"{i:<4} {channel['type']:<8} {title_display:<30} {username_display:<20}")
        except UnicodeEncodeError:
            # Fallback for non-ASCII characters
            safe_title = title_display.encode('ascii', 'replace').decode('ascii')
            print(f"{i:<4} {channel['type']:<8} {safe_title:<30} {username_display:<20}")
    
    print(f"\n{Fore.CYAN}0. Enter channel manually{Style.RESET_ALL}")
    
    while True:
        try:
            choice = input(f"\n{Fore.CYAN}Select a channel (0-{len(channels)}): {Style.RESET_ALL}")
            choice_num = int(choice)
            
            if choice_num == 0:
                # Manual entry
                channel_username = input(f"{Fore.CYAN}Enter the channel name or username: {Style.RESET_ALL}")
                try:
                    entity = await client.get_entity(channel_username)
                    print(f"{Fore.GREEN}+ Found: {getattr(entity, 'title', channel_username)}{Style.RESET_ALL}")
                    return entity
                except Exception as e:
                    print(f"{Fore.RED}X Cannot access '{channel_username}': {e}{Style.RESET_ALL}")
                    continue
            elif 1 <= choice_num <= len(channels):
                selected_channel = channels[choice_num - 1]
                try:
                    if selected_channel['username']:
                        entity = await client.get_entity(selected_channel['username'])
                    else:
                        entity = await client.get_entity(selected_channel['id'])
                    print(f"{Fore.GREEN}+ Selected: {getattr(entity, 'title', 'Unknown')}{Style.RESET_ALL}")
                    return entity
                except Exception as e:
                    print(f"{Fore.RED}X Cannot access selected channel: {e}{Style.RESET_ALL}")
                    continue
            else:
                print(f"{Fore.RED}Invalid choice! Please select a number between 0 and {len(channels)}.{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}Invalid input! Please enter a number.{Style.RESET_ALL}")
        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}Operation cancelled by user.{Style.RESET_ALL}")
            return None


async def upload_file(client, file_path, channel, progress_bars, uploaded_files, caption=None):
    """Upload a single file to the channel"""
    filename = os.path.basename(file_path)
    progress_bar = None
    
    try:
        file_size = os.path.getsize(file_path)
        
        # Check if already uploaded
        if file_path in uploaded_files:
            print(f"{Fore.YELLOW}Skipping {filename} - already uploaded{Style.RESET_ALL}")
            return True
        
        # Simple permission check (non-blocking)
        try:
            if hasattr(channel, 'default_banned_rights'):
                rights = channel.default_banned_rights
                if rights and rights.send_media:
                    print(f"{Fore.YELLOW}! Warning: May not have media permissions for {getattr(channel, 'title', 'Unknown')}{Style.RESET_ALL}")
        except Exception:
            # Ignore permission check errors and proceed with upload
            pass
        
        # Initialize progress bar
        progress_bar = tqdm(
            total=file_size,
            desc=f"Uploading {filename[:20]}...",
            ncols=100,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            colour="green"
        )
        progress_bars.append(progress_bar)
        
        # Upload file with progress callback
        def progress_callback(current, total):
            if progress_bar:
                progress_bar.n = current
                progress_bar.refresh()
        
        # Perform upload using the channel entity directly
        await client.send_file(
            channel,  # Use entity directly, not channel.id
            file_path,
            caption=caption,
            progress_callback=progress_callback,
            attributes=[DocumentAttributeFilename(filename)]
        )
        
        # Mark as uploaded
        uploaded_files.add(file_path)
        
        # Complete progress bar
        if progress_bar:
            progress_bar.n = file_size
            progress_bar.refresh()
            progress_bar.close()
        
        print(f"{Fore.GREEN}✓ Uploaded: {filename}{Style.RESET_ALL}")
        return True
        
    except Exception as e:
        if progress_bar:
            progress_bar.close()
        
        error_msg = str(e).lower()
        if "peer validation failed" in error_msg or "invalid peer" in error_msg:
            print(f"{Fore.RED}X Peer validation failed for {filename}. Channel may be inaccessible.{Style.RESET_ALL}")
        elif "flood" in error_msg.lower():
            print(f"{Fore.RED}X Rate limit exceeded. Please wait before uploading more files.{Style.RESET_ALL}")
        elif "file" in error_msg.lower() and "large" in error_msg.lower():
            print(f"{Fore.RED}X File {filename} is too large for upload.{Style.RESET_ALL}")
        elif "permission" in error_msg.lower() or "forbidden" in error_msg.lower():
            print(f"{Fore.RED}X Permission denied for {filename}. Check channel permissions.{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}X Failed to upload {filename}: {e}{Style.RESET_ALL}")
        return False


async def upload_in_batches(client, files, channel, batch_size, uploaded_files, state_file, caption=None):
    """Upload files in batches"""
    tasks = []
    progress_bars = []
    successful_uploads = 0
    failed_uploads = 0
    
    for i, file_path in enumerate(files, 1):
        tasks.append(upload_file(client, file_path, channel, progress_bars, uploaded_files, caption))
        
        # Run in batches
        if len(tasks) == batch_size or i == len(files):
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successful and failed uploads
            for result in results:
                if isinstance(result, Exception):
                    failed_uploads += 1
                elif result is True:
                    successful_uploads += 1
                else:
                    failed_uploads += 1
            
            # Save state after each batch
            save_upload_state(uploaded_files, state_file)
            tasks.clear()
    
    # Provide detailed completion summary
    total_files = len(files)
    if successful_uploads == total_files:
        print(f"\n{Fore.GREEN}+ Upload completed successfully! {successful_uploads}/{total_files} files uploaded{Style.RESET_ALL}")
    elif successful_uploads > 0:
        print(f"\n{Fore.YELLOW}! Upload partially completed: {successful_uploads}/{total_files} files uploaded, {failed_uploads} failed{Style.RESET_ALL}")
    else:
        print(f"\n{Fore.RED}X Upload failed: 0/{total_files} files uploaded{Style.RESET_ALL}")
    
    return successful_uploads, failed_uploads


async def session_selection_menu(session_manager):
    """Menu for session selection and management"""
    while True:
        print(f"\n{Fore.CYAN}📱 Session Management{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*30}{Style.RESET_ALL}")
        
        current = session_manager.get_current_session()
        if current:
            print(f"{Fore.GREEN}Current: {current.name} ({current.phone_number}){Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}No active session{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}Options:{Style.RESET_ALL}")
        print("1. Use current session")
        print("2. Switch session")
        print("3. Add new session")
        print("4. Manage sessions")
        print("0. Exit")
        
        choice = input(f"\n{Fore.CYAN}Enter your choice (0-4): {Style.RESET_ALL}").strip()
        
        if choice == "0":
            return None
        elif choice == "1":
            if current:
                return current
            else:
                print(f"{Fore.RED}No active session available{Style.RESET_ALL}")
        elif choice == "2":
            if session_manager.sessions:
                session_manager.list_sessions()
                session_name = input(f"\n{Fore.CYAN}Enter session name: {Style.RESET_ALL}").strip()
                if session_name and session_manager.switch_session(session_name):
                    return session_manager.get_current_session()
            else:
                print(f"{Fore.YELLOW}No sessions available{Style.RESET_ALL}")
        elif choice == "3":
            await add_session_interactive(session_manager)
        elif choice == "4":
            await session_manager.interactive_session_menu()
        else:
            print(f"{Fore.RED}Invalid choice!{Style.RESET_ALL}")


async def add_session_interactive(session_manager):
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
        
        success = await session_manager.add_session(name, phone, api_id, api_hash)
        if success:
            # Automatically switch to the new session
            session_manager.switch_session(name)
        
    except ValueError:
        print(f"{Fore.RED}Invalid API ID{Style.RESET_ALL}")


async def main():
    print(f"{Fore.CYAN}>> TELEGRAM MULTI-SESSION UPLOADER{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*45}{Style.RESET_ALL}")
    
    # Initialize session manager
    session_manager = SessionManager()
    
    # Session selection
    session_info = await session_selection_menu(session_manager)
    if not session_info:
        print(f"{Fore.YELLOW}No session selected. Exiting...{Style.RESET_ALL}")
        return
    
    try:
        # Get client for selected session
        client = await session_manager.get_client(session_info.name)
        if not client:
            print(f"{Fore.RED}Failed to connect with session '{session_info.name}'. Exiting...{Style.RESET_ALL}")
            return
        
        print(f"{Fore.GREEN}+ Connected to Telegram successfully!{Style.RESET_ALL}")
        print(f"{Fore.GREEN}  Account: {session_info.first_name} {session_info.last_name or ''} ({session_info.phone_number}){Style.RESET_ALL}")
        
        # Select upload target
        channel = await display_and_select_upload_target(client)
        if not channel:
            print(f"{Fore.RED}No channel selected. Exiting...{Style.RESET_ALL}")
            await client.disconnect()
            return
        
        print(f"{Fore.YELLOW}Selected upload target: {channel.title} (ID: {channel.id}){Style.RESET_ALL}")
        
        # Choose upload mode
        print(
            f"{Fore.CYAN}Choose upload mode:{Style.RESET_ALL}\n"
            f"1. Upload single file\n"
            f"2. Upload entire folder\n"
        )
        mode_choice = input(f"{Fore.CYAN}Enter your choice (1-2): {Style.RESET_ALL}").strip()
        
        if mode_choice == "1":
            # Single file upload
            file_path = input(f"{Fore.CYAN}Enter the file path to upload: {Style.RESET_ALL}").strip()
            
            if not file_path or not os.path.exists(file_path) or not os.path.isfile(file_path):
                print(f"{Fore.RED}Invalid file path! Exiting...{Style.RESET_ALL}")
                await client.disconnect()
                return
            
            # Optional caption for single file
            add_caption = input(f"{Fore.CYAN}Add a caption to the file? (y/n): {Style.RESET_ALL}").lower()
            caption = None
            if add_caption == 'y':
                caption = input(f"{Fore.CYAN}Enter caption: {Style.RESET_ALL}")
            
            # Confirm upload
            filename = os.path.basename(file_path)
            confirm = input(f"{Fore.YELLOW}Upload '{filename}' to {channel.title}? (y/n): {Style.RESET_ALL}")
            if confirm.lower() != 'y':
                print(f"{Fore.YELLOW}Upload cancelled.{Style.RESET_ALL}")
                await client.disconnect()
                return
            
            # Upload single file
            print(f"{Fore.GREEN}Starting upload...{Style.RESET_ALL}")
            progress_bars = []
            uploaded_files = set()
            result = await upload_file(client, file_path, channel, progress_bars, uploaded_files, caption)
            
            # Close progress bars
            for pb in progress_bars:
                pb.close()
            
            if result:
                print(f"\n{Fore.GREEN}+ Upload completed successfully! '{filename}' uploaded to {channel.title}{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.RED}X Upload failed! '{filename}' could not be uploaded to {channel.title}{Style.RESET_ALL}")
        
        elif mode_choice == "2":
            # Folder upload (existing functionality)
            folder_path = input(f"{Fore.CYAN}Enter the folder path to upload from: {Style.RESET_ALL}").strip()
            
            if not folder_path or not os.path.exists(folder_path):
                print(f"{Fore.RED}Invalid folder path! Exiting...{Style.RESET_ALL}")
                await client.disconnect()
                return
            
            # Choose file types
            print(
                f"{Fore.CYAN}Choose the type of files to upload:{Style.RESET_ALL}\n"
                f"1. Images (.jpg, .jpeg, .png, .gif, .webp)\n"
                f"2. Videos (.mp4, .avi, .mov, .mkv, .webm)\n"
                f"3. Documents (.pdf, .doc, .docx, .txt)\n"
                f"4. Archives (.zip, .rar, .7z)\n"
                f"5. All files\n"
            )
            choice = input(f"{Fore.CYAN}Enter your choice (1-5): {Style.RESET_ALL}")
            
            file_types = None
            if choice == "1":
                file_types = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            elif choice == "2":
                file_types = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
            elif choice == "3":
                file_types = ['.pdf', '.doc', '.docx', '.txt']
            elif choice == "4":
                file_types = ['.zip', '.rar', '.7z']
            elif choice == "5":
                file_types = None  # All files
            else:
                print(f"{Fore.RED}Invalid choice! Exiting...{Style.RESET_ALL}")
                await client.disconnect()
                return
            
            # Get files to upload
            files = get_files_from_folder(folder_path, file_types)
            
            if not files:
                print(f"{Fore.RED}No files found to upload!{Style.RESET_ALL}")
                await client.disconnect()
                return
            
            # Load upload state
            state_file = os.path.join(folder_path, "upload_state.json")
            uploaded_files = load_upload_state(state_file)
            
            # Filter out already uploaded files
            original_count = len(files)
            files = [f for f in files if f not in uploaded_files]
            already_uploaded = original_count - len(files)
            
            print(f"Found {original_count} total files.")
            if already_uploaded > 0:
                print(f"{Fore.YELLOW}{already_uploaded} files already uploaded (skipping){Style.RESET_ALL}")
            print(f"{Fore.GREEN}{len(files)} new files to upload{Style.RESET_ALL}")
            
            if not files:
                print(f"{Fore.YELLOW}All files have already been uploaded!{Style.RESET_ALL}")
                await client.disconnect()
                return
            
            # Optional caption
            add_caption = input(f"{Fore.CYAN}Add a caption to all files? (y/n): {Style.RESET_ALL}").lower()
            caption = None
            if add_caption == 'y':
                caption = input(f"{Fore.CYAN}Enter caption: {Style.RESET_ALL}")
            
            # Confirm upload
            confirm = input(f"{Fore.YELLOW}Upload {len(files)} files to {channel.title}? (y/n): {Style.RESET_ALL}")
            if confirm.lower() != 'y':
                print(f"{Fore.YELLOW}Upload cancelled.{Style.RESET_ALL}")
                await client.disconnect()
                return
            
            # Start upload
            print(f"{Fore.GREEN}Starting upload...{Style.RESET_ALL}")
            batch_size = 5  # Default batch size
            successful, failed = await upload_in_batches(client, files, channel, batch_size, uploaded_files, state_file, caption)
            
            # Final summary is already printed by upload_in_batches function
        
        else:
            print(f"{Fore.RED}Invalid choice! Exiting...{Style.RESET_ALL}")
        
        # Disconnect client
        await client.disconnect()
        
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}! Operation cancelled by user{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}X Error: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}! Please check your session and internet connection{Style.RESET_ALL}")


if __name__ == "__main__":
    asyncio.run(main())