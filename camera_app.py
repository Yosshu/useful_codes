"""Tkinter で写真撮影と動画録画を行うカメラアプリ。"""

import os
import threading
import time

# macOS のシステム Tk が出す非推奨警告を抑制する。
os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")

import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

import cv2
from PIL import Image, ImageTk


class CameraApp:
    def __init__(
        self,
        root,
        camera_index=0,
        width=1280,
        height=720,
        fps=30,
        output_dir="camera_output",
    ):
        self.root = root
        self.fps = fps
        self.camera_index = camera_index
        self.camera_width = width
        self.camera_height = height

        self.output_dir = Path(output_dir)
        self.photo_dir = self.output_dir / "photos"
        self.video_dir = self.output_dir / "videos"
        self.photo_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)

        self.current_frame = None
        self.writer = None
        self.recording = False
        self.current_video_path = None
        self.running = True
        self.after_id = None
        self.last_camera_message = None
        self.camera_help_shown = False

        # OpenCV の open/read は環境によって長時間ブロックするため、Tkスレッドから分離する。
        self.frame_lock = threading.Lock()
        self.latest_frame = None
        self.camera_state = "searching"
        self.camera_message = "カメラを検索しています..."
        self.active_camera_index = None
        self.camera_stop_event = threading.Event()
        self.camera_rescan_event = threading.Event()
        self.camera_thread = None

        self.root.title("Camera App")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Key-r>", self.toggle_recording)
        self.root.bind("<Key-R>", self.toggle_recording)
        self.root.bind("<Key-p>", self.take_photo)
        self.root.bind("<Key-P>", self.take_photo)
        self.root.bind("<Escape>", self.close)

        self.preview_label = tk.Label(
            self.root,
            bg="black",
            fg="white",
            text="カメラを検索しています...",
            font=("TkDefaultFont", 16),
        )
        self.preview_label.pack(fill="both", expand=True, padx=12, pady=(12, 6))

        controls = ttk.Frame(self.root, padding=(12, 6, 12, 12))
        controls.pack(fill="x")

        self.photo_button = ttk.Button(
            controls,
            text="写真撮影 (P)",
            command=self.take_photo,
            state="disabled",
        )
        self.photo_button.pack(side="left", padx=(0, 8))

        self.record_button = ttk.Button(
            controls,
            text="録画開始 (R)",
            command=self.toggle_recording,
            state="disabled",
        )
        self.record_button.pack(side="left", padx=(0, 8))

        self.search_button = ttk.Button(
            controls,
            text="カメラ再検索",
            command=self.request_camera_search,
        )
        self.search_button.pack(side="left", padx=(0, 8))

        ttk.Button(controls, text="終了 (Esc)", command=self.close).pack(
            side="left"
        )

        self.status = tk.StringVar(value="カメラを検索しています...")
        ttk.Label(controls, textvariable=self.status).pack(side="right")

        # GUIを先に完成させ、カメラ処理はバックグラウンドで開始する。
        self.after_id = self.root.after(33, self.refresh_ui)
        self.camera_thread = threading.Thread(
            target=self.camera_worker,
            name="camera-capture",
            daemon=True,
        )
        self.camera_thread.start()

    @staticmethod
    def timestamp():
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]

    def set_camera_state(
        self,
        state,
        message,
        *,
        camera_index=None,
        frame=None,
        clear_frame=False,
    ):
        with self.frame_lock:
            self.camera_state = state
            self.camera_message = message
            self.active_camera_index = camera_index
            if clear_frame:
                self.latest_frame = None
            if frame is not None:
                self.latest_frame = frame

    def camera_worker(self):
        """カメラを探索し、最新フレームを共有するバックグラウンド処理。"""
        while not self.camera_stop_event.is_set():
            self.camera_rescan_event.clear()
            self.set_camera_state(
                "searching",
                "カメラID 0〜4を検索しています...",
                clear_frame=True,
            )

            result = self.find_working_camera()
            if self.camera_stop_event.is_set():
                return
            if self.camera_rescan_event.is_set():
                continue

            if result is None:
                self.set_camera_state(
                    "error",
                    "使用できるカメラが見つかりませんでした。",
                    clear_frame=True,
                )
                while not self.camera_stop_event.is_set():
                    if self.camera_rescan_event.wait(0.2):
                        break
                continue

            cap, index, first_frame = result
            self.set_camera_state(
                "ready",
                f"カメラID {index} に接続しました。",
                camera_index=index,
                frame=first_frame,
            )

            failures = 0
            while (
                not self.camera_stop_event.is_set()
                and not self.camera_rescan_event.is_set()
            ):
                ret, frame = cap.read()
                if ret and frame is not None and frame.size:
                    failures = 0
                    with self.frame_lock:
                        self.latest_frame = frame
                    continue

                failures += 1
                if failures >= 10:
                    self.set_camera_state(
                        "searching",
                        "映像を取得できません。カメラを再検索します...",
                        clear_frame=True,
                    )
                    break
                time.sleep(0.05)

            cap.release()
            if (
                failures >= 10
                and not self.camera_stop_event.is_set()
                and not self.camera_rescan_event.is_set()
            ):
                time.sleep(0.5)

    def find_working_camera(self):
        """既定バックエンドでID 0〜4を試し、映像を取得できるカメラを返す。"""
        indices = [self.camera_index]
        indices.extend(index for index in range(5) if index != self.camera_index)

        for index in indices:
            if (
                self.camera_stop_event.is_set()
                or self.camera_rescan_event.is_set()
            ):
                return None

            cap = cv2.VideoCapture(index)
            if not cap.isOpened():
                cap.release()
                continue

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
            cap.set(cv2.CAP_PROP_FPS, self.fps)

            for _ in range(10):
                if (
                    self.camera_stop_event.is_set()
                    or self.camera_rescan_event.is_set()
                ):
                    cap.release()
                    return None
                ret, frame = cap.read()
                if ret and frame is not None and frame.size:
                    self.camera_index = index
                    return cap, index, frame
                time.sleep(0.05)

            cap.release()

        return None

    def request_camera_search(self):
        if not self.running:
            return
        if self.recording:
            self.stop_recording()
        self.current_frame = None
        self.camera_help_shown = False
        self.set_camera_state(
            "searching",
            "カメラを再検索しています...",
            clear_frame=True,
        )
        self.camera_rescan_event.set()

    def refresh_ui(self):
        self.after_id = None
        if not self.running:
            return

        with self.frame_lock:
            state = self.camera_state
            message = self.camera_message
            frame = None if self.latest_frame is None else self.latest_frame.copy()

        if message != self.last_camera_message:
            self.status.set(message)
            self.last_camera_message = message

        camera_ready = state == "ready" and frame is not None
        button_state = "normal" if camera_ready else "disabled"
        self.photo_button.configure(state=button_state)
        self.record_button.configure(state=button_state)

        if camera_ready:
            self.current_frame = frame
            if self.recording and self.writer is not None:
                self.writer.write(frame)
            self.show_frame(frame)
        else:
            self.current_frame = None
            if self.recording:
                self.stop_recording()
                self.status.set(message)
            self.preview_label.configure(image="", text=message, wraplength=760)
            self.preview_label.image = None
            if state == "error" and not self.camera_help_shown:
                self.camera_help_shown = True
                self.root.after_idle(self.show_camera_help)

        interval_ms = max(1, round(1000 / self.fps))
        self.after_id = self.root.after(interval_ms, self.refresh_ui)

    def show_frame(self, frame):
        preview = frame.copy()
        if self.recording:
            cv2.putText(
                preview,
                "REC",
                (20, 45),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 0, 255),
                3,
                cv2.LINE_AA,
            )

        preview = self.resize_preview(preview, max_width=960)
        preview_rgb = cv2.cvtColor(preview, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(preview_rgb)
        photo = ImageTk.PhotoImage(image=image)
        self.preview_label.configure(image=photo, text="")
        self.preview_label.image = photo

    def show_camera_help(self):
        if not self.running:
            return
        with self.frame_lock:
            if self.camera_state != "error":
                return
        messagebox.showwarning(
            "カメラ映像を取得できません",
            "カメラID 0〜4を試しましたが、映像を取得できませんでした。\n\n"
            "macOS の「システム設定 > プライバシーとセキュリティ > カメラ」で、"
            "ターミナル（または使用中の Python）を許可してください。ほかのアプリが "
            "カメラを使用している場合は、そのアプリも終了してください。",
        )

    @staticmethod
    def resize_preview(frame, max_width):
        height, width = frame.shape[:2]
        if width <= max_width:
            return frame
        scale = max_width / width
        size = (max_width, max(1, round(height * scale)))
        return cv2.resize(frame, size, interpolation=cv2.INTER_AREA)

    def take_photo(self, _event=None):
        if self.current_frame is None:
            self.status.set("撮影できるフレームがまだありません。")
            return

        path = self.photo_dir / f"photo_{self.timestamp()}.png"
        if cv2.imwrite(str(path), self.current_frame):
            self.status.set(f"写真を保存しました: {path}")
        else:
            self.status.set("写真の保存に失敗しました。")

    def toggle_recording(self, _event=None):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        if self.current_frame is None:
            self.status.set("録画できるフレームがまだありません。")
            return

        height, width = self.current_frame.shape[:2]
        path = self.video_dir / f"video_{self.timestamp()}.mp4"
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(
            str(path),
            fourcc,
            self.fps,
            (width, height),
        )
        if not writer.isOpened():
            writer.release()
            self.status.set("録画ファイルを開けませんでした。")
            messagebox.showerror(
                "録画エラー",
                f"録画ファイルを開けませんでした。\n{path}",
            )
            return

        self.writer = writer
        self.current_video_path = path
        self.recording = True
        self.record_button.configure(text="録画停止 (R)")
        self.status.set(f"録画中: {path.name}")

    def stop_recording(self):
        if self.writer is not None:
            self.writer.release()
            self.writer = None

        saved_path = self.current_video_path
        self.current_video_path = None
        self.recording = False
        self.record_button.configure(text="録画開始 (R)")
        if saved_path is not None:
            self.status.set(f"動画を保存しました: {saved_path}")

    def close(self, _event=None):
        if not self.running:
            return

        self.running = False
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except tk.TclError:
                pass
            self.after_id = None
        if self.recording:
            self.stop_recording()
        self.camera_stop_event.set()
        self.camera_rescan_event.set()
        if self.camera_thread is not None:
            self.camera_thread.join(timeout=0.5)
        self.root.destroy()


def main():
    root = tk.Tk()
    CameraApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
