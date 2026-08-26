#!/usr/bin/env python3
import os
import sys
import getpass
import atexit
import signal
import readline

RESET = "\033[0m"


def get_real_user():
    try:
        return getpass.getuser()
    except Exception:
        return os.getenv("USER") or os.getenv("LOGNAME") or "user"

CURRENT_USER = get_real_user()
HOSTNAME = "straw"
HISTORY_FILE = os.path.expanduser("~/.straw_history")

sudo_authenticated = False

try:
    if os.path.exists(HISTORY_FILE):
        readline.read_history_file(HISTORY_FILE)
    readline.set_history_length(500)
except:
    pass

atexit.register(lambda: readline.write_history_file(HISTORY_FILE))

signal.signal(signal.SIGINT, signal.SIG_IGN)



def sudo_check():
    global sudo_authenticated
    if sudo_authenticated:
        return True

    max_attempts = 3
    correct_pass = "straw"
    for attempt in range(1, max_attempts + 1):
        try:
            pass_input = getpass.getpass(f"[sudo] password for {CURRENT_USER}: ")
        except (EOFError):
            print("\n")
            return False

        if pass_input == correct_pass:
            sudo_authenticated = True
            return True
        else:
            print("Sorry, try again.")

    print("sudo: 3 incorrect password attempts")
    return False

def main():
    global CURRENT_USER, sudo_authenticated

    while True:
        try:
            cwd = os.getcwd()
            home_dir = os.path.expanduser("~")

            if cwd == home_dir or cwd == "/data/data/com.termux/files/home":
                display_path = "~"
            else:
                display_path = os.path.basename(cwd)

            symbol = "#" if CURRENT_USER == "root" else "$"
            prompt_text = f"{CURRENT_USER}#{HOSTNAME}:[{display_path}]~{symbol} "
            prompt = f"{prompt_text}"

            cmd = input(prompt).strip()

            if not cmd:
                continue

            if cmd == "exit":
                print("logout")
                break
            elif cmd == "clear":
                os.system("clear")

            elif cmd == "history":
                for i in range(1, readline.get_current_history_length() + 1):
                    print(f"  {i}  {readline.get_history_item(i)}")
            elif cmd == "whoami":
                print(CURRENT_USER)
            elif cmd.startswith("cd "):
                try:
                    target_dir = cmd[3:].strip()
                    if not target_dir:
                        target_dir = home_dir
                    os.chdir(target_dir)
                except Exception as e:
                    print(f"cd: {e}")
            elif cmd == "su" or cmd == "sudo su":
                if CURRENT_USER == "root":
                    continue
                if sudo_check():
                    CURRENT_USER = "root"
                else:
                    print("su: Authentication failure")
            else:
                if cmd.startswith("sudo "):
                    if not sudo_check():
                        continue

                    cmd = cmd[5:].strip()

                os.system(cmd)
        except (EOFError):
            continue

if __name__ == "__main__":
    main()