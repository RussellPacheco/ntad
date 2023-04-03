import shutil, os, json, sys, datetime, logging


PID_to_kill = sys.argv[1]
log_file = sys.argv[2]
parent_dir = sys.argv[3]
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

logging.basicConfig(filename=log_file, encoding="utf-8", format="[%(asctime)s] %(message)s", level="INFO", force=True)

try: 
    folder_to_delete = parent_dir
    shutil.rmtree(folder_to_delete)
    logging.info(f"Removing {folder_to_delete}")
except FileNotFoundError:
    logging.error(f"Folder Not Found Error Folder: {folder_to_delete}")
except Exception as e:
    logging.error(f"Folder Delete Error Folder: {folder_to_delete} Error: {e}")