#!/usr/bin/env python3

import os, json, sys, signal, shutil, subprocess, datetime, logging

data = {}
uuidpid_data = None
log_file = None
project_root = None
uuid_pid_pairs = []
new_pairs = []
on_kill_file = ""
data_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
uuid = os.path.basename(__file__).split(".")[0].split("_")[2]
parent_dir = os.path.dirname(os.path.abspath(__file__))

with open(data_file, "r") as file:
    data = json.load(file)

log_file = data["log_file"]
project_root = data["project_root"]
uuidpid_data = data["uuidpid"]
uuid_pid_pairs = uuidpid_data.split(";")
new_pairs = uuid_pid_pairs.copy()

logging.basicConfig(filename=log_file, encoding="utf-8", format="[%(asctime)s] %(message)s", force=True, level="INFO")

on_kill_file = os.path.join(data["project_root"], "on_kill.py")

for uuid_pid in uuid_pid_pairs:
    split_pair = uuid_pid.split(":")
    if uuid in split_pair:
        try:
            if sys.platform == "win32":
                os.kill(int(split_pair[1]), signal.SIGBREAK)
            else:
                os.kill(int(split_pair[1]), signal.SIGKILL)
            logging.info(f"Killing process: {split_pair[1]}")
            new_pairs.remove(uuid_pid)
        except PermissionError:
            logging.error(f"Permission Error Process: {split_pair[1]}")
        except Exception as e:
            logging.error(f"Error Killing Process: {split_pair[1]} Error: {e}")

data["pid"] = ";".join(new_pairs)
with open(data_file, "w") as file:
    json.dump(data, file)

with open(data_file, "r") as file:
    data = json.load(file)

if data["pid"] == "":
    subprocess.Popen(["python3", f"{on_kill_file}", str(split_pair[1]), log_file, parent_dir], start_new_session=True)

