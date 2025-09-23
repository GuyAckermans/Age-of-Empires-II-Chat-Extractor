import os
import time
from mgz.summary import Summary
from datetime import datetime, date
import msvcrt  # For detecting any key press on Windows

# Configuration - Edit if needed
REPLAY_BASE_DIR = os.path.expanduser('~') + r'\Games\Age of Empires 2 DE'  # Base directory for AoE II DE
PROFILE_ID = None  # Set this to your profile ID (e.g., '76561199310445090') if auto-detection doesn't pick the right one

# Find the savegame directory
if PROFILE_ID is None:
    profile_dirs = [d for d in os.listdir(REPLAY_BASE_DIR) if d.isdigit() and len(d) > 5]  # Profile IDs are long numbers
    if len(profile_dirs) == 0:
        raise ValueError("Could not find any profile directory in Games\Age of Empires 2 DE")
    elif len(profile_dirs) > 1:
        # Auto-select the profile with the most recently modified savegame folder
        profile_times = []
        for pd in profile_dirs:
            sg_path = os.path.join(REPLAY_BASE_DIR, pd, 'savegame')
            if os.path.exists(sg_path):
                mod_time = os.path.getmtime(sg_path)
                profile_times.append((pd, mod_time))
        if profile_times:
            profile_times.sort(key=lambda x: x[1], reverse=True)  # Newest first
            PROFILE_ID = profile_times[0][0]
        else:
            raise ValueError("No valid savegame folders found in profiles. Set PROFILE_ID manually.")
    else:
        PROFILE_ID = profile_dirs[0]

# Safeguard: Ensure PROFILE_ID is a string
PROFILE_ID = str(PROFILE_ID)

REPLAY_DIR = os.path.join(REPLAY_BASE_DIR, PROFILE_ID, 'savegame')

def get_replays_by_date():
    today = date.today()
    todays_replays = []
    previous_replays = []
    for f in os.listdir(REPLAY_DIR):
        if f.endswith('.aoe2record'):
            file_path = os.path.join(REPLAY_DIR, f)
            mod_time = os.path.getmtime(file_path)
            file_date = datetime.fromtimestamp(mod_time).date()
            if file_date == today:
                todays_replays.append(file_path)
            else:
                previous_replays.append(file_path)
    
    # Sort both lists by modification time, newest first
    todays_replays.sort(key=os.path.getmtime, reverse=True)
    previous_replays.sort(key=os.path.getmtime, reverse=True)
    
    return todays_replays, previous_replays

def format_replay_info(replay_path, summary=None):
    basename = os.path.basename(replay_path)
    try:
        # Extract date and time from filename (e.g., "@2025.09.22 185103")
        parts = basename.split('@')[1].split()[0:2]
        date_str = parts[0]
        time_str = parts[1]
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y.%m.%d %H%M%S")
        formatted_date = dt.strftime("%B %d, %Y")
        formatted_time = dt.strftime("%H:%M")
    except Exception:
        formatted_date = "Unknown date"
        formatted_time = "Unknown time"
    
    duration_str = "Unknown duration"
    if summary:
        try:
            duration_ms = summary.get_duration()
            if duration_ms:
                # Adjust for 1.7x game speed to get real-time duration
                real_duration_sec = (duration_ms / 1000) / 1.7
                duration_str = time.strftime('%H:%M:%S', time.gmtime(real_duration_sec))
        except Exception:
            pass
    
    return f"{formatted_date} at {formatted_time} (Duration: {duration_str})"

def extract_all_chat(replay_path):
    try:
        with open(replay_path, 'rb') as f:
            summary = Summary(f)
        
        # Get players
        players = summary.get_players()
        
        # Color mapping (standard AoE II DE player colors by color_id)
        color_map = {
            0: 'Blue',
            1: 'Red',
            2: 'Green',
            3: 'Yellow',
            4: 'Teal',
            5: 'Purple',
            6: 'Gray',
            7: 'Orange'
        }
        
        # ANSI color codes for console output
        ansi_colors = {
            'Blue': '\033[94m',
            'Red': '\033[91m',
            'Green': '\033[92m',
            'Yellow': '\033[93m',
            'Teal': '\033[96m',
            'Purple': '\033[95m',
            'Gray': '\033[90m',
            'Orange': '\033[33m',  # Orange is approximated as brown/yellowish
            'Unknown': '\033[0m'  # Reset/no color
        }
        reset = '\033[0m'
        
        # Get chats
        chats = summary.get_chat()
        chat_lines = []
        for chat in chats:
            player = next((p for p in players if p['number'] == chat['player_number']), None)
            if player:
                player_name = player['name']
                color_id = player.get('color_id', -1)
                color = color_map.get(color_id, 'Unknown')
            else:
                player_name = 'Unknown'
                color = 'Unknown'
            
            timestamp_ms = chat.get('timestamp', 0)
            timestamp_sec = timestamp_ms / 1000
            timestamp = time.strftime('%H:%M:%S', time.gmtime(timestamp_sec))
            line = f"[{timestamp}] {player_name} ({color}): {chat['message']}"
            colored_line = ansi_colors.get(color, '') + line + reset
            chat_lines.append(colored_line)
        
        output = ""
        if chat_lines:
            output += "\n".join(chat_lines) + "\n\n"
        else:
            output += "Only boring people in this game, there was no chat\n"
        
        return output, summary
    except Exception as e:
        return f"Error parsing replay {replay_path}: {e}\n", None

if __name__ == "__main__":
    todays_replays, previous_replays = get_replays_by_date()
    
    # Process all today's games automatically
    if todays_replays:
        print(f"\nProcessing today's {len(todays_replays)} games:")
        for idx, replay in enumerate(todays_replays, 1):
            all_chats, summary = extract_all_chat(replay)
            replay_info = format_replay_info(replay, summary)
            print(f"\nGame {idx}/{len(todays_replays)}: {replay_info}")
            if all_chats:
                print(all_chats)
            else:
                print("Only boring people in this game, there was no chat")
    else:
        print("\nNo games played today.")
    
    # Prompt for additional previous games
    num_previous_input = input("\nHow many more previous games to show?: ").strip()
    try:
        NUM_PREVIOUS = int(num_previous_input) if num_previous_input else 0
        if NUM_PREVIOUS < 0:
            raise ValueError
    except ValueError:
        print("Invalid input. Showing 0 additional games.")
        NUM_PREVIOUS = 0
    
    if NUM_PREVIOUS > 0:
        additional_replays = previous_replays[:NUM_PREVIOUS]
        if additional_replays:
            print(f"\nProcessing {NUM_PREVIOUS} previous games:")
            for idx, replay in enumerate(additional_replays, 1):
                all_chats, summary = extract_all_chat(replay)
                replay_info = format_replay_info(replay, summary)
                print(f"\nGame {idx}/{NUM_PREVIOUS}: {replay_info}")
                if all_chats:
                    print(all_chats)
                else:
                    print("Only boring people in this game, there was no chat")
        else:
            print("\nNo previous games available.")
    
    # Pause at the end with any key press and close the window
    print("\nPress any key to quit...")
    msvcrt.getch()
    os.system('taskkill /f /pid %d' % os.getpid())