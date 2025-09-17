import os
import re
from typing import Dict, List

class Storage:
    def __init__(self, upload_dir="uploads"):
        self.upload_dir = upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)
        self.uploaded_files: List[str] = []
        self.file_paragraphs: Dict[str, List[str]] = {}
        self.file_data: Dict[str, Dict] = {}
        self.indexed_files = set()

    def save_file(self, file):
        file_path = os.path.join(self.upload_dir, file.filename)
        content = file.file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        text = content.decode(errors="ignore")
        paragraphs = [p.strip() for p in re.split(r'\n+', text) if p.strip()]
        self.file_paragraphs[file.filename] = paragraphs

        self.file_data[file.filename] = {
            "chars": len(text),
            "size": len(content),
            "status": "Pending"
        }

        if file.filename not in self.uploaded_files:
            self.uploaded_files.append(file.filename)

    def index_files(self):
        for f in self.uploaded_files:
            self.indexed_files.add(f)
            self.file_data[f]["status"] = "Indexed"

    def has_files(self):
        return bool(self.uploaded_files)

    def summary(self, success=True, message=None):
        total_chars = sum(fd["chars"] for fd in self.file_data.values())
        return {
            "status": "success" if success else "error",
            "message": message,
            "files": self.uploaded_files,
            "total_files": len(self.uploaded_files),
            "total_chars": total_chars,
            "indexed_files": len(self.indexed_files),
            "file_data": self.file_data,
        }

storage = Storage()
