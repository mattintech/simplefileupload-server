import os
import time

class FileMetadata:
    def __init__(self, code, file_path, max_downloads=1, expiry_hours=24):
        self.code = code
        self.file_path = file_path
        self.max_downloads = max_downloads
        self.expiry_time = time.time() + (expiry_hours * 3600)
        self.download_count = 0

    def is_expired(self):
        return time.time() > self.expiry_time

    def increment_download_count(self):
        self.download_count += 1

    def can_download(self):
        return self.download_count < self.max_downloads and not self.is_expired()

    def delete_file(self):
        if os.path.exists(self.file_path):
            os.remove(self.file_path)