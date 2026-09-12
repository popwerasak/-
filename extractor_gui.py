#!/usr/bin/env python3
"""โปรแกรมแตกไฟล์ ZIP / RAR แบบมี GUI สำหรับ Windows, macOS และ Linux."""

import os
import sys
import queue
import shutil
import subprocess
import threading
import tkinter as tk
import zipfile
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

try:
    import rarfile
except ImportError:
    rarfile = None

SUPPORTED_EXTS = (".zip", ".rar")


class ExtractCancelled(Exception):
    pass


class ExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("โปรแกรมแตกไฟล์ ZIP / RAR")
        self.root.geometry("640x480")
        self.root.minsize(560, 420)

        self.archive_paths: list[Path] = []
        self.dest_dir = tk.StringVar(value=str(Path.home() / "Desktop"))
        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self.cancel_requested = threading.Event()

        self._configure_rar_tool()
        self._build_ui()
        self._poll_log_queue()

    # ---------- UI ----------

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        frame_files = ttk.LabelFrame(self.root, text="ไฟล์ที่จะแตก (.zip / .rar)")
        frame_files.pack(fill="both", expand=False, **pad)

        self.file_listbox = tk.Listbox(frame_files, height=6, selectmode="extended")
        self.file_listbox.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)

        scroll = ttk.Scrollbar(frame_files, orient="vertical", command=self.file_listbox.yview)
        scroll.pack(side="left", fill="y", pady=8)
        self.file_listbox.config(yscrollcommand=scroll.set)

        btns = ttk.Frame(frame_files)
        btns.pack(side="left", fill="y", padx=8, pady=8)
        ttk.Button(btns, text="เพิ่มไฟล์...", command=self.add_files).pack(fill="x", pady=2)
        ttk.Button(btns, text="ลบที่เลือก", command=self.remove_selected).pack(fill="x", pady=2)
        ttk.Button(btns, text="ล้างทั้งหมด", command=self.clear_files).pack(fill="x", pady=2)

        frame_dest = ttk.LabelFrame(self.root, text="แตกไฟล์ไปที่โฟลเดอร์")
        frame_dest.pack(fill="x", **pad)
        entry = ttk.Entry(frame_dest, textvariable=self.dest_dir)
        entry.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        ttk.Button(frame_dest, text="เลือกโฟลเดอร์...", command=self.choose_dest).pack(
            side="left", padx=8, pady=8
        )

        self.each_in_own_folder = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.root,
            text="สร้างโฟลเดอร์แยกตามชื่อไฟล์ (แนะนำ)",
            variable=self.each_in_own_folder,
        ).pack(anchor="w", padx=16)

        action_frame = ttk.Frame(self.root)
        action_frame.pack(fill="x", **pad)
        self.extract_btn = ttk.Button(action_frame, text="เริ่มแตกไฟล์", command=self.start_extract)
        self.extract_btn.pack(side="left")
        self.cancel_btn = ttk.Button(
            action_frame, text="ยกเลิก", command=self.cancel_extract, state="disabled"
        )
        self.cancel_btn.pack(side="left", padx=8)
        self.open_dest_btn = ttk.Button(
            action_frame, text="เปิดโฟลเดอร์ปลายทาง", command=self.open_dest_folder
        )
        self.open_dest_btn.pack(side="right")

        self.progress = ttk.Progressbar(self.root, mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=(0, 6))

        log_frame = ttk.LabelFrame(self.root, text="สถานะ")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(log_frame, height=10, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)

        if rarfile is None or not self.rar_tool_available:
            self._log(
                "หมายเหตุ: ไม่พบโปรแกรมช่วยแตกไฟล์ RAR (unrar/unar/7z) บนเครื่องนี้ "
                "ฟังก์ชันแตกไฟล์ .rar อาจใช้งานไม่ได้ กรุณาติดตั้งเพิ่มเติม (ดู README.md)"
            )

    # ---------- RAR backend detection ----------

    def _configure_rar_tool(self):
        self.rar_tool_available = False
        if rarfile is None:
            return
        for tool_name in ("unrar", "unar", "7z", "7zz", "bsdtar"):
            path = shutil.which(tool_name)
            if path:
                self.rar_tool_available = True
                if tool_name in ("unrar",):
                    rarfile.UNRAR_TOOL = path
                elif tool_name in ("7z", "7zz"):
                    rarfile.UNRAR_TOOL = path
                    rarfile.USE_EXTRACT_HACK = 1
                break

    # ---------- File / folder pickers ----------

    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="เลือกไฟล์ ZIP หรือ RAR",
            filetypes=[("Archive files", "*.zip *.rar"), ("All files", "*.*")],
        )
        for p in paths:
            path = Path(p)
            if path.suffix.lower() not in SUPPORTED_EXTS:
                continue
            if path not in self.archive_paths:
                self.archive_paths.append(path)
                self.file_listbox.insert("end", str(path))

    def remove_selected(self):
        for idx in reversed(self.file_listbox.curselection()):
            del self.archive_paths[idx]
            self.file_listbox.delete(idx)

    def clear_files(self):
        self.archive_paths.clear()
        self.file_listbox.delete(0, "end")

    def choose_dest(self):
        folder = filedialog.askdirectory(title="เลือกโฟลเดอร์ปลายทาง")
        if folder:
            self.dest_dir.set(folder)

    def open_dest_folder(self):
        target = Path(self.dest_dir.get())
        if not target.exists():
            messagebox.showwarning("ไม่พบโฟลเดอร์", f"ยังไม่มีโฟลเดอร์:\n{target}")
            return
        if sys.platform.startswith("win"):
            os.startfile(target)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(target)])
        else:
            subprocess.run(["xdg-open", str(target)])

    # ---------- Extraction ----------

    def start_extract(self):
        if not self.archive_paths:
            messagebox.showinfo("ยังไม่มีไฟล์", "กรุณาเพิ่มไฟล์ .zip หรือ .rar ก่อนเริ่มแตกไฟล์")
            return
        if self.worker_thread and self.worker_thread.is_alive():
            return

        dest_root = Path(self.dest_dir.get()).expanduser()
        try:
            dest_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror("ผิดพลาด", f"สร้างโฟลเดอร์ปลายทางไม่ได้:\n{exc}")
            return

        self.cancel_requested.clear()
        self.extract_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.progress["value"] = 0
        self._log("เริ่มแตกไฟล์...")

        self.worker_thread = threading.Thread(
            target=self._extract_all_worker,
            args=(list(self.archive_paths), dest_root, self.each_in_own_folder.get()),
            daemon=True,
        )
        self.worker_thread.start()

    def cancel_extract(self):
        self.cancel_requested.set()
        self._log("กำลังยกเลิก...")

    def _extract_all_worker(self, archives, dest_root: Path, own_folder: bool):
        total = len(archives)
        ok_count = 0
        for i, archive in enumerate(archives, start=1):
            if self.cancel_requested.is_set():
                self._log("ยกเลิกโดยผู้ใช้")
                break
            self._log(f"[{i}/{total}] กำลังแตกไฟล์: {archive.name}")
            target_dir = dest_root / archive.stem if own_folder else dest_root
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                self._extract_one(archive, target_dir)
                self._log(f"  เสร็จแล้ว -> {target_dir}")
                ok_count += 1
            except ExtractCancelled:
                self._log("ยกเลิกโดยผู้ใช้")
                break
            except Exception as exc:  # noqa: BLE001 - surface any failure to the user
                self._log(f"  ผิดพลาด: {exc}")
            self.root.after(0, self.progress.config, {"value": int(i / total * 100)})

        self._log(f"สรุป: สำเร็จ {ok_count}/{total} ไฟล์")
        self.root.after(0, self._on_worker_done)

    def _on_worker_done(self):
        self.extract_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")

    def _extract_one(self, archive: Path, target_dir: Path):
        ext = archive.suffix.lower()
        if ext == ".zip":
            self._extract_zip(archive, target_dir)
        elif ext == ".rar":
            self._extract_rar(archive, target_dir)
        else:
            raise ValueError(f"นามสกุลไฟล์ไม่รองรับ: {ext}")

    def _extract_zip(self, archive: Path, target_dir: Path):
        with zipfile.ZipFile(archive) as zf:
            password = None
            names = zf.namelist()
            for idx, name in enumerate(names):
                if self.cancel_requested.is_set():
                    raise ExtractCancelled()
                while True:
                    try:
                        zf.extract(name, path=target_dir, pwd=password.encode() if password else None)
                        break
                    except RuntimeError as exc:
                        if "password" not in str(exc).lower():
                            raise
                        password = self._ask_password(archive.name)
                        if password is None:
                            raise ExtractCancelled()

    def _extract_rar(self, archive: Path, target_dir: Path):
        if rarfile is None:
            raise RuntimeError(
                "ไม่ได้ติดตั้งไลบรารี 'rarfile' กรุณารัน: pip install rarfile"
            )
        if not self.rar_tool_available:
            raise RuntimeError(
                "ไม่พบโปรแกรมช่วยแตกไฟล์ RAR (unrar/unar/7z) กรุณาติดตั้งก่อน (ดู README.md)"
            )
        password = None
        while True:
            try:
                with rarfile.RarFile(archive) as rf:
                    if rf.needs_password() and password is None:
                        password = self._ask_password(archive.name)
                        if password is None:
                            raise ExtractCancelled()
                    rf.extractall(path=str(target_dir), pwd=password)
                return
            except rarfile.PasswordRequired:
                password = self._ask_password(archive.name)
                if password is None:
                    raise ExtractCancelled()
            except rarfile.BadRarFile as exc:
                raise RuntimeError(f"ไฟล์ RAR เสียหายหรือไม่ถูกต้อง: {exc}") from exc

    def _ask_password(self, filename: str):
        result: dict[str, str | None] = {}
        done = threading.Event()

        def prompt():
            result["value"] = simpledialog.askstring(
                "ไฟล์มีรหัสผ่าน",
                f"ไฟล์ '{filename}' มีการตั้งรหัสผ่าน\nกรุณาใส่รหัสผ่าน:",
                show="*",
                parent=self.root,
            )
            done.set()

        self.root.after(0, prompt)
        done.wait()
        return result.get("value")

    # ---------- Logging ----------

    def _log(self, message: str):
        self.log_queue.put(message)

    def _poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        self.root.after(150, self._poll_log_queue)


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if sys.platform.startswith("win"):
            style.theme_use("vista")
        elif sys.platform == "darwin":
            style.theme_use("aqua")
    except tk.TclError:
        pass
    app = ExtractorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
