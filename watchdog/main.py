import os, subprocess, json, argparse, shutil, stat, datetime, logging, time, re
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from torrent_process import handle_torrent_download
from utils import write_to_json


parser = argparse.ArgumentParser(prog="Nas Torrent Auto Downloader", description="Automatically watches specified download folders for torrent files, and if found, downloads torrent.")
parser.add_argument("-w", "--watch-path", required=True, help="Set the folder to watch")
parser.add_argument("-d", "--download-folder", required=True, help="Set the download folder")
parser.add_argument("-l", "--log-file", required=True, help="Specify the log file path.")
parser.add_argument("--log-level", required=False, help="DEBUG, INFO, WARNING, ERROR, CRITICAL", default="INFO")

args = parser.parse_args()

log_file = args.log_file
log_level = args.log_level

numeric_level = getattr(logging, log_level.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: %s' % log_level)

logging.basicConfig(filename=log_file, encoding="utf-8", level=log_level, format="[%(asctime)s] %(message)s")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
watch_path = os.path.normpath(args.watch_path)
download_folder = os.path.normpath(args.download_folder)


class TorrentDownload:
    def __init__(self) -> None:
        self.count = 0

    def increase_count(self):
        self.count += 1


class TorrentManager:
    def __init__(self) -> None:
        self.managed_downloads = {}

    def register_download(self, filename):
        self.managed_downloads[filename] = TorrentDownload()
        return filename
    
    def increase_count(self, filename): 
        self.managed_downloads[filename].increase_count()
        return self.managed_downloads[filename].count
    
    def get_count(self, filename):
        return self.managed_downloads[filename].count
    
    def file_exist(self, filename):
        if filename in self.managed_downloads.keys():
            return True
        return False
    
    def remove_download(self, filename):
        del self.managed_downloads[filename]


class Callback(FileSystemEventHandler):
    def __init__(self, torrent_manager: TorrentManager = None) -> None:
        if torrent_manager is None:
            torrent_manager = TorrentManager()

        self.torrent_manager = torrent_manager
        
    def validator(self, event):
        file_found = False
        pattern = r"\.(torrent|magnet)$"
        if event.event_type == "moved":
            if re.search(pattern, event.dest_path):
                file_found = True 
        else:
            if re.search(pattern, event.src_path):
                file_found = True
        if file_found:
            should_be_watchpath = None
            file_type = None
            if event.event_type == "moved":
                should_be_watchpath = os.path.dirname(os.path.dirname(event.dest_path))
                file_type = os.path.basename(event.dest_path).split(".")[-1]
            else:
                should_be_watchpath = os.path.dirname(os.path.dirname(event.src_path))  
                file_type = os.path.basename(event.src_path).split(".")[-1]
            if should_be_watchpath == watch_path:
                if file_type in ["torrent", "magnet"]:
                    return True
        return False
        
    # def on_any_event(self, event):
    #     write_to_json(event)
    
    def on_modified(self, event):
        if self.validator(event):
            self.on_new_file(event)

    def on_moved(self, event):
        if self.validator(event):
            self.on_new_file(event)

    def on_created(self, event):
        if self.validator(event):
            self.on_new_file(event)

    def on_deleted(self, event):
        if self.validator(event):
            self.on_new_file(event)

    def on_closed(self, event):
        if self.validator(event):
            self.on_new_file(event)

    def on_new_file(self, event):
        filename = None
        if event.event_type == "moved":
            filename = os.path.basename(event.dest_path)
        else: 
            filename = os.path.basename(event.src_path)
        if not self.torrent_manager.file_exist(filename=filename) and event.event_type == "created":
            self.torrent_manager.register_download(filename=filename)
            self.torrent_manager.increase_count(filename=filename)
        elif self.torrent_manager.file_exist(filename=filename):
            self.torrent_manager.increase_count(filename=filename)        
            if self.torrent_manager.get_count(filename=filename) == 6:
                self.torrent_manager.remove_download(filename=filename)
                parent_dir = None
                if event.event_type == "moved":
                    parent_dir = os.path.abspath(os.path.join(event.dest_path, os.pardir))
                    torrent_file_abspath = event.dest_path
                else:
                    parent_dir = os.path.abspath(os.path.join(event.src_path, os.pardir))
                    torrent_file_abspath = event.src_path

                parent = os.path.split(parent_dir)[1]
                parent_parent_dir = os.path.abspath(os.path.join(parent_dir, os.pardir))
                parent_parent = os.path.split(parent_parent_dir)[1]
                watch_folder_parent = os.path.split(watch_path)[1]
                torrent_file = os.path.basename(torrent_file_abspath)
                new_folder_path = os.path.join(download_folder, parent)
                file_type = torrent_file.split(".")[1]
                logging.info(f"New file detected:: Filename: {torrent_file} Filepath: {torrent_file_abspath} ")
                print(f"[{datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')}] New file detected:: Filename: {torrent_file} Filepath: {torrent_file_abspath} ")
                torrent_task_details = {
                    "file_type": file_type,
                    "new_folder_path": new_folder_path,
                    "torrent_file_abspath": torrent_file_abspath,
                    "watch_folder_parent_path": parent_dir,
                    "parent_dir": parent_dir,
                    "log_file": log_file,
                    "log_level": log_level
                }
                handle_torrent_download.delay(torrent_task_details)
        

observer = Observer()
callback = Callback()

path = watch_path
print(f"callback: {callback}")
observer.schedule(event_handler=callback, path=path, recursive=True)
logging.info(f"Watch Dog is running")
print(f"[{datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')}] Watch Dog is running")
observer.start()


try:
    while observer.is_alive():
        observer.join(1)
finally:
    observer.stop()
    observer.join()



