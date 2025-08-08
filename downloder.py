import asyncio
import os
import json
from dotenv import load_dotenv
from colorama import Fore, Style
from tqdm.asyncio import tqdm
from telethon import TelegramClient
from telethon.tl.types import (
    DocumentAttributeFilename,
    InputMessagesFilterVideo,
    InputMessagesFilterPhotos,
    InputMessagesFilterDocument,
    Channel,
    Chat,
)

# Load environment variables
load_dotenv('.env.local')  # Specify the correct .env file name

# Retrieve values from .env
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
session_name = os.getenv("SESSION_NAME", "default_session")
batch_size = int(os.getenv("BATCH_SIZE", 5))


def save_download_state(downloaded_ids, state_file="download_state.json"):
    """Save downloaded message IDs to JSON file"""
    try:
        with open(state_file, 'w') as f:
            json.dump(list(downloaded_ids), f)
    except Exception as e:
        print(f"{Fore.YELLOW}Warning: Could not save download state: {e}{Style.RESET_ALL}")


def load_download_state(state_file="download_state.json"):
    """Load downloaded message IDs from JSON file"""
    try:
        with open(state_file, 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()
    except Exception as e:
        print(f"{Fore.YELLOW}Warning: Could not load download state: {e}{Style.RESET_ALL}")
        return set()


def get_filename_from_message(message):
    """Extract filename from message"""
    if message.document:
        # Try to get original filename
        for attr in message.document.attributes:
            if isinstance(attr, DocumentAttributeFilename):
                return attr.file_name
        # Fallback to generic name based on mime type
        if message.document.mime_type:
            ext = message.document.mime_type.split('/')[-1]
            if ext == 'pdf':
                return f"document_{message.id}.pdf"
            elif ext in ['zip', 'x-zip-compressed']:
                return f"archive_{message.id}.zip"
            elif 'video' in message.document.mime_type:
                return f"video_{message.id}.mp4"
        return f"document_{message.id}.bin"
    elif message.video:
        return f"video_{message.id}.mp4"
    elif message.photo:
        return f"photo_{message.id}.jpg"
    else:
        return f"media_{message.id}.bin"


def is_file_already_downloaded(message, folder_path):
    """Check if file already exists in the folder"""
    filename = get_filename_from_message(message)
    file_path = os.path.join(folder_path, filename)
    return os.path.exists(file_path)


async def list_user_channels(client):
    """List all channels and groups the user has access to"""
    print(f"{Fore.YELLOW}Fetching your channels and groups...{Style.RESET_ALL}")
    
    dialogs = await client.get_dialogs()
    channels = []
    
    for dialog in dialogs:
        entity = dialog.entity
        if isinstance(entity, (Channel, Chat)):
            # Only include channels and groups, not private chats
            if hasattr(entity, 'username') and entity.username:
                channels.append({
                    'title': entity.title,
                    'username': entity.username,
                    'id': entity.id,
                    'type': 'Channel' if isinstance(entity, Channel) else 'Group'
                })
            else:
                channels.append({
                    'title': entity.title,
                    'username': None,
                    'id': entity.id,
                    'type': 'Channel' if isinstance(entity, Channel) else 'Group'
                })
    
    return channels


async def display_and_select_channel(client):
    """Display available channels and let user select one"""
    channels = await list_user_channels(client)
    
    if not channels:
        print(f"{Fore.RED}No channels or groups found!{Style.RESET_ALL}")
        return None
    
    print(f"\n{Fore.CYAN}Available channels and groups:{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'No.':<4} {'Type':<8} {'Title':<30} {'Username':<20}{Style.RESET_ALL}")
    print("-" * 70)
    
    for i, channel in enumerate(channels, 1):
        username_display = f"@{channel['username']}" if channel['username'] else "(Private)"
        title_display = channel['title'][:28] + ".." if len(channel['title']) > 30 else channel['title']
        print(f"{i:<4} {channel['type']:<8} {title_display:<30} {username_display:<20}")
    
    print(f"\n{Fore.CYAN}0. Enter channel manually{Style.RESET_ALL}")
    
    while True:
        try:
            choice = input(f"\n{Fore.CYAN}Select a channel (0-{len(channels)}): {Style.RESET_ALL}")
            choice_num = int(choice)
            
            if choice_num == 0:
                # Manual entry
                channel_username = input(f"{Fore.CYAN}Enter the channel name or username: {Style.RESET_ALL}")
                return await client.get_entity(channel_username)
            elif 1 <= choice_num <= len(channels):
                selected_channel = channels[choice_num - 1]
                if selected_channel['username']:
                    return await client.get_entity(selected_channel['username'])
                else:
                    return await client.get_entity(selected_channel['id'])
            else:
                print(f"{Fore.RED}Invalid choice! Please select a number between 0 and {len(channels)}.{Style.RESET_ALL}")
        except ValueError:
            print(f"{Fore.RED}Invalid input! Please enter a number.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Error accessing channel: {e}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Please try another selection.{Style.RESET_ALL}")


async def download_file(message, folder_name, progress_bars, downloaded_ids):
    try:
        # Check if file already exists
        if is_file_already_downloaded(message, folder_name):
            filename = get_filename_from_message(message)
            print(f"{Fore.YELLOW}Skipping {filename} - already downloaded{Style.RESET_ALL}")
            downloaded_ids.add(message.id)
            return
        
        # Get the file size
        file_size = (
            message.video.size
            if message.video
            else message.document.size if message.document else 0
        )

        filename = get_filename_from_message(message)
        # Initialize the progress bar
        progress_bar = tqdm(
            total=file_size,
            desc=f"Downloading {filename[:20]}...",
            ncols=100,
            unit="B",
            unit_scale=True,
            leave=True,  # Keep progress bar visible after completion
            bar_format=(
                "{l_bar}%s{bar}%s| {n_fmt}/{total_fmt} {unit} "
                "| Elapsed: {elapsed}/{remaining} | {rate_fmt}"
                % (Fore.BLUE, Style.RESET_ALL)
            ),
        )
        progress_bars.append(progress_bar)

        # Download media with progress
        await message.download_media(
            file=f"./{folder_name}/",
            progress_callback=lambda current, total: (
                progress_bar.update(current - progress_bar.n) if total else None
            ),
        )

        # After download finishes, change the color to green
        progress_bar.bar_format = (
            "{l_bar}%s{bar}%s| {n_fmt}/{total_fmt} {unit} "
            "| Elapsed: {elapsed}/{rate_fmt}" % (Fore.GREEN, Style.RESET_ALL)
        )
        progress_bar.set_description(f"Finished {filename[:20]}...")
        progress_bar.n = progress_bar.total  # Ensure the progress bar shows 100%
        progress_bar.update(0)  # Force update to display the changes
        
        # Mark as downloaded
        downloaded_ids.add(message.id)

    except Exception as e:
        print(f"Error downloading media: {e}")


async def download_in_batches(messages, folder_name, batch_size, downloaded_ids, state_file):
    tasks = []
    progressbar = []
    for i, message in enumerate(messages, 1):
        tasks.append(download_file(message, folder_name, progressbar, downloaded_ids))
        # Run in batches of batch_size
        if len(tasks) == batch_size or i == len(messages):
            await asyncio.gather(*tasks)
            # Save state after each batch
            save_download_state(downloaded_ids, state_file)
            tasks.clear()  # Clear tasks after each batch


async def main():
    async with TelegramClient(session_name, api_id, api_hash) as client:
        print(f"{Fore.GREEN}Connected successfully!{Style.RESET_ALL}")
        
        # Display and select channel
        channel = await display_and_select_channel(client)
        if not channel:
            print(f"{Fore.RED}No channel selected. Exiting...{Style.RESET_ALL}")
            return
            
        print(
            f"{Fore.YELLOW}Selected channel: {channel.title} (ID: {channel.id}){Style.RESET_ALL}"
        )

        # Prompt the user for their choice
        print(
            f"{Fore.CYAN}Choose the type of content to download:{Style.RESET_ALL}\n"
            f"1. Images\n"
            f"2. Videos\n"
            f"3. PDFs\n"
            f"4. ZIP files\n"
            f"5. All types\n"
        )
        choice = input(f"{Fore.CYAN}Enter your choice (1-5): {Style.RESET_ALL}")

        default_folder_name = ""
        filter_type = None

        if choice == "1":
            filter_type = InputMessagesFilterPhotos()
            default_folder_name = "images"
        elif choice == "2":
            filter_type = InputMessagesFilterVideo()
            default_folder_name = "videos"
        elif choice in ["3", "4"]:
            filter_type = InputMessagesFilterDocument()
            default_folder_name = "pdfs" if choice == "3" else "zips"
        elif choice == "5":
            filter_type = None
            default_folder_name = "all_media"
        else:
            print(f"{Fore.RED}Invalid choice! Exiting...{Style.RESET_ALL}")
            return

        # Custom folder naming
        print(f"\n{Fore.CYAN}Folder Configuration:{Style.RESET_ALL}")
        custom_folder = input(f"{Fore.CYAN}Enter custom folder name (press Enter for default '{default_folder_name}'): {Style.RESET_ALL}").strip()
        
        if custom_folder:
            folder_name = custom_folder
        else:
            folder_name = default_folder_name
            
        download_path = f"downloads/{folder_name}"
        if not os.path.exists(download_path):
            os.makedirs(download_path)
            print(f"{Fore.GREEN}Created folder: {download_path}{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}Using existing folder: {download_path}{Style.RESET_ALL}")

        # Load download state
        state_file = f"downloads/{folder_name}/download_state.json"
        downloaded_ids = load_download_state(state_file)
        
        print(f"{Fore.YELLOW}Fetching media messages...{Style.RESET_ALL}")
        media_messages = await client.get_messages(
            channel, filter=filter_type, limit=2000
        )

        if choice == "3":
            media_messages = [
                msg
                for msg in media_messages
                if msg.document and msg.document.mime_type == "application/pdf"
            ]
        elif choice == "4":
            media_messages = [
                msg
                for msg in media_messages
                if msg.document and msg.document.mime_type == "application/zip"
            ]

        # Filter out already downloaded messages
        original_count = len(media_messages)
        media_messages = [
            msg for msg in media_messages 
            if msg.id not in downloaded_ids and not is_file_already_downloaded(msg, download_path)
        ]
        
        already_downloaded = original_count - len(media_messages)
        
        print(f"Found {original_count} total messages matching your choice.")
        if already_downloaded > 0:
            print(f"{Fore.YELLOW}{already_downloaded} files already downloaded (skipping){Style.RESET_ALL}")
        print(f"{Fore.GREEN}{len(media_messages)} new files to download{Style.RESET_ALL}")

        if media_messages:
            await download_in_batches(media_messages, download_path, batch_size, downloaded_ids, state_file)
            print(f"\n{Fore.GREEN}Download completed! Files saved to: {download_path}{Style.RESET_ALL}")
        else:
            if already_downloaded > 0:
                print(f"{Fore.YELLOW}All files have already been downloaded!{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}No media found for the selected type.{Style.RESET_ALL}")


if __name__ == "__main__":
    asyncio.run(main())
