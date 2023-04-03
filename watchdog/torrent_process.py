import os, subprocess, datetime, shutil, json, stat, re, logging
from celery import Celery
from uuid import uuid4

app = Celery('torrent_process', broker='amqp://localhost')
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

@app.task
def handle_torrent_download(torrent_task_details: dict):
    torrent_uuid = uuid4()
    logging.basicConfig(filename=torrent_task_details["log_file"], encoding="utf-8", format="[%(asctime)s] %(message)s", level=torrent_task_details["log_level"], force=True)
    create_folder(new_folder_path=torrent_task_details["new_folder_path"])
    download_ps = download_torrent_file(torrent_file_abspath=torrent_task_details["torrent_file_abspath"], new_folder_path=torrent_task_details["new_folder_path"], watch_folder_parent_path=torrent_task_details["watch_folder_parent_path"], uuid=torrent_uuid)
    copy_on_complete_files(parent_dir=torrent_task_details["parent_dir"], pid=download_ps.pid, log_file=torrent_task_details["log_file"], uuid=torrent_uuid)
    with download_ps.stdout:
        for line in iter(download_ps.stdout.readline, b''):
            line = line.decode("utf-8")
            if re.match("\[\d{4}-\d{2}-\d{2} \d{1,2}:\d{2}:\d{2},\d*\]", line) is not None:
                logging.info(line)
            else:
                try:
                    aria_logfile_path = os.path.join(torrent_task_details["parent_dir"], "aria_log")
                    with open(aria_logfile_path, "a") as logfile:
                        logfile.write(line)
                except FileNotFoundError:
                    print(line)
    download_ps.wait()

def create_folder(new_folder_path: str):
    try:
        os.mkdir(new_folder_path)
        logging.debug(f"File folder is created at {new_folder_path}")
    except FileExistsError:
        pass
    return new_folder_path

def copy_on_complete_files(parent_dir, pid, log_file, uuid):
    data_file = os.path.join(parent_dir, "data")
    if "data" in os.listdir(parent_dir):
        with open(data_file, "r") as file:
            data = json.load(file)
        data["uuidpid"] = f"{data['uuidpid']};{uuid}:{pid}"
        with open(data_file, "w") as file:
            json.dump(data, file)
    else:
        with open(data_file, "w") as file:
            data = {
                "uuidpid": f"{uuid}:{pid}",
                "project_root": PROJECT_ROOT,
                "log_file": log_file
            }
            json.dump(data, file)       
    on_complete_file = os.path.join(PROJECT_ROOT, "on_complete.py")
    copied_complete_file = os.path.join(parent_dir, f"on_complete_{uuid}.py")
    shutil.copyfile(on_complete_file, copied_complete_file)
    os.chmod(copied_complete_file, stat.S_IRWXU)

def download_torrent_file(torrent_file_abspath: str, new_folder_path: str, watch_folder_parent_path: str, uuid):
    torrent_log_file = os.path.join(os.path.dirname(torrent_file_abspath), "torrent_log_file.log")
    on_complete_file_abspath = os.path.join(watch_folder_parent_path, f"on_complete_{uuid}.py")
    download_ps = subprocess.Popen(["aria2c", "-T", torrent_file_abspath, "-d", new_folder_path, "--file-allocation=falloc", "-V", "true", f'--on-bt-download-complete={on_complete_file_abspath}'], start_new_session=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    logging.info(f"New torrent is being run at PID: {download_ps.pid}")
    return download_ps

def download_magnet_file(magnet_file_abspath: str, new_folder_path: str, watch_folder_parent_path: str, uuid):
    torrent_log_file = os.path.join(os.path.dirname(magnet_file_abspath), "torrent_log_file.log")
    on_complete_file_abspath = os.path.join(watch_folder_parent_path, f"on_complete_{uuid}.py")
    download_ps = subprocess.Popen(["aria2c", "-T", magnet_file_abspath, "-d", new_folder_path, "--file-allocation=falloc", "-V", "true", f'--on-bt-download-complete={on_complete_file_abspath}'], start_new_session=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE)
    logging.info(f"New torrent is being run at PID: {download_ps.pid}")
    return download_ps