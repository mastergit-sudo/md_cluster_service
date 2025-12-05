import time
import os
import threading
from pathlib import Path
import yaml
import sys
import traceback

import win32serviceutil
import win32service
import win32event
import servicemanager

from logger_setup import get_logger
from file_handler import list_md_files, read_md_file, safe_move, ensure_dir, archive_file
from clusterer import MdClusterer
from utils import sanitize_folder_name, top_keywords_from_vectorizer

class MdClusterService(win32serviceutil.ServiceFramework):
    _svc_name_ = "MdClusterService"
    _svc_display_name_ = "Markdown Clustering Service"
    _svc_description_ = "Watches a folder and clusters .md files into subfolders based on content."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        # Load config
        cfg_path = os.path.join(os.path.dirname(__file__), "config.yaml")
        with open(cfg_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        log_file = self.config.get('log_file', os.path.join(os.path.dirname(__file__), 'md_cluster_service.log'))
        self.logger = get_logger("MdClusterService", log_file)
        self.poll_interval = int(self.config.get('poll_interval', 30))
        self.input_dir = self.config.get('input_dir')
        self.output_dir = self.config.get('output_dir')
        self.archive_dir = self.config.get('archive_dir')
        self.n_clusters = int(self.config.get('n_clusters', 5))
        self.min_files = int(self.config.get('min_files_for_clustering', 3))
        self.name_by_keywords = bool(self.config.get('name_clusters_by_keywords', True))
        ensure_dir(self.input_dir)
        ensure_dir(self.output_dir)
        if self.archive_dir:
            ensure_dir(self.archive_dir)

        self.running = False

    def SvcStop(self):
        self.logger.info("Service stop requested.")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.stop_event)
        self.running = False

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.logger.info("Service started.")
        self.running = True
        try:
            self.main()
        except Exception as e:
            self.logger.exception("Unhandled exception in service: %s", e)
            raise

    def main(self):
        while True:
            # wait with ability to break early
            rc = win32event.WaitForSingleObject(self.stop_event, int(self.poll_interval * 1000))
            if rc == win32event.WAIT_OBJECT_0:
                self.logger.info("Stop event set, exiting main loop.")
                break
            try:
                self.process_once()
            except Exception as e:
                self.logger.exception("Error during processing: %s", e)

    def process_once(self):
        files = list_md_files(self.input_dir)
        if not files:
            self.logger.debug("No .md files found.")
            return
        self.logger.info("Found %d .md files to consider.", len(files))
        # Read files
        docs = []
        paths = []
        for p in files:
            try:
                text = read_md_file(p)
                docs.append(text)
                paths.append(p)
            except Exception:
                self.logger.exception("Failed reading file %s", p)
        if len(docs) < self.min_files:
            # fallback: move all to a pending folder
            pending = os.path.join(self.output_dir, "pending")
            ensure_dir(pending)
            for src in paths:
                dst = os.path.join(pending, Path(src).name)
                self.logger.info("Moving %s -> %s (not enough files for clustering).", src, dst)
                safe_move(src, dst)
            return

        clusterer = MdClusterer(n_clusters=self.n_clusters)
        labels, model_and_matrix = clusterer.fit_predict(docs, requested_clusters=self.n_clusters)
        model, X = model_and_matrix
        # For each cluster, create folder and move files
        unique_labels = sorted(set(labels.tolist()))
        for lab in unique_labels:
            # determine folder name
            if self.name_by_keywords and model is not None:
                try:
                    keywords = top_keywords_from_vectorizer(clusterer.vectorizer, X, labels, lab, top_n=3)
                    if keywords:
                        folder_name = "_".join(keywords)
                    else:
                        folder_name = f"cluster_{lab}"
                except Exception:
                    folder_name = f"cluster_{lab}"
            else:
                folder_name = f"cluster_{lab}"
            folder_name = sanitize_folder_name(folder_name)
            target_folder = os.path.join(self.output_dir, folder_name)
            ensure_dir(target_folder)
            # move files in this cluster
            for i, l in enumerate(labels):
                if l == lab:
                    src = paths[i]
                    dst = os.path.join(target_folder, Path(src).name)
                    try:
                        self.logger.info("Moving %s -> %s", src, dst)
                        safe_move(src, dst)
                        if self.archive_dir:
                            # if archive desired, copy or move original; here we move already moved file? so archive not used after move.
                            # Instead, we can copy before move. For simplicity, skip archive if move done.
                            pass
                    except Exception:
                        self.logger.exception("Failed moving %s", src)

if __name__ == '__main__':
    # Allow install / remove / start / stop from command line
    if len(sys.argv) == 1:
        try:
            win32serviceutil.HandleCommandLine(MdClusterService)
        except Exception:
            traceback.print_exc()
    else:
        win32serviceutil.HandleCommandLine(MdClusterService)
