"""Tkinter で写真撮影と動画録画を行うカメラアプリ。"""

import os
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
        self.output_dir = Path(output_dir)
        self.photo_dir = self.output_dir / "photos"
        self.video_dir = self.output_dir / "videos"
        self.photo_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)

        self.camera_index = camera_index
        self.camera_width = width
        self.camera_height = height
        self.cap = None
        self.current_frame = None
        self.writer = None
        self.recording = False
        self.current_video_path = None
        self.running = True
        self.after_id = None
        self.camera_help_shown = False
        self.read_failures = 0

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
            text="カメラを準備しています...",
            font=("TkDefaultFont", 16),
        )
        self.preview_label.pack(fill="both", expand=True, padx=12, pady=(12, 6))

        controls = ttk.Frame(self.root, padding=(12, 6, 12, 12))
        controls.pack(fill="x")

        self.photo_button = ttk.Button(
            controls,
            text="写真撮影 (P)",
            command=self.take_photo,
        )
        self.photo_button.pack(side="left", padx=(0, 8))

        self.record_button = ttk.Button(
            controls,
            text="録画開始 (R)",
            command=self.toggle_recording,
        )
        self.record_button.pack(side="left", padx=(0, 8))

        self.search_button = ttk.Button(
            controls,
            text="カメラ再検索",
            command=self.initialize_camera,
        )
        self.search_button.pack(side="left", padx=(0, 8))

        ttk.Button(controls, text="終了 (Esc)", command=self.close).pack(
            side="left"
        )

        self.status = tk.StringVar(value="カメラを準備しています...")
        ttk.Label(controls, textvariable=self.status).pack(side="right")

        # ウィンドウを先に描画してから、既定バックエンドでカメラを探す。
        self.after_id = self.root.after(100, self.initialize_camera)

    def initialize_camera(self):
        """優先IDから順にカメラを探し、実際にフレームを取得できるものを使う。"""
        if not self.running:
            return

        self.cancel_scheduled_update()
        if self.recording:
            self.stop_recording()
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        self.current_frame = None
        self.read_failures = 0
        self.search_button.configure(state="disabled")
        self.photo_button.configure(state="disabled")
        self.record_button.configure(state="disabled")
        self.status.set("カメラを検索しています...")
        self.preview_label.configure(
            image="",
            text="カメラID 0〜4を検索しています...",
            wraplength=760,
        )
        self.preview_label.image = None
        self.root.update_idletasks()

        indices = [self.camera_index]
        indices.extend(index for index in range(5) if index != self.camera_index)
        first_frame = None

        for index in indices:
            cap = cv2.VideoCapture(index)
            if not cap.isOpened():
                cap.release()
                continue

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
            cap.set(cv2.CAP_PROP_FPS, self.fps)

            # 起動直後は空フレームになることがあるので、少しだけ待って再試行する。
            for _ in range(10):
                ret, frame = cap.read()
                if ret and frame is not None and frame.size:
                    first_frame = frame
                    break
                time.sleep(0.05)

            if first_frame is not None:
                self.cap = cap
                self.camera_index = index
                self.current_frame = first_frame
                break
            cap.release()

        self.search_button.configure(state="normal")
        if self.cap is None:
            message = (
                "使用できるカメラが見つかりませんでした。\n"
                "カメラID 0〜4を確認しました。カメラ権限や、ほかのアプリによる "
                "カメラ使用を確認してください。"
            )
            self.status.set("使用できるカメラが見つかりませんでした。")
            self.preview_label.configure(image="", text=message, wraplength=760)
            if not self.camera_help_shown:
                self.camera_help_shown = True
                self.root.after_idle(self.show_camera_help)
            return

        self.photo_button.configure(state="normal")
        self.record_button.configure(state="normal")
        self.status.set(f"カメラID {self.camera_index} に接続しました。")
        self.after_id = self.root.after(0, self.update_frame)

    def cancel_scheduled_update(self):
        if self.after_id is None:
            return
        try:
            self.root.after_cancel(self.after_id)
        except tk.TclError:
            pass
        self.after_id = None

    @staticmethod
    def timestamp():
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]

    def update_frame(self):
        self.after_id = None
        if not self.running:
            return

        if self.cap is None or not self.cap.isOpened():
            self.status.set("カメラが切断されました。再検索します...")
            self.after_id = self.root.after(500, self.initialize_camera)
            return

        ret, frame = self.cap.read()
        if not ret:
            if self.recording:
                self.stop_recording()
            self.read_failures += 1
            if self.read_failures >= 10:
                self.status.set("映像を取得できません。カメラを再検索します...")
                self.after_id = self.root.after(500, self.initialize_camera)
            else:
                self.status.set("カメラ映像を取得できません。再試行中...")
                self.after_id = self.root.after(100, self.update_frame)
            return

        self.read_failures = 0
        self.current_frame = frame
        if self.recording and self.writer is not None:
            self.writer.write(frame)

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
        if not self.recording:
            self.status.set("プレビュー中")

        interval_ms = max(1, round(1000 / self.fps))
        self.after_id = self.root.after(interval_ms, self.update_frame)

    def show_camera_help(self):
        if not self.running or self.current_frame is not None:
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
        self.cancel_scheduled_update()
        if self.recording:
            self.stop_recording()
        if self.cap is not None:
            self.cap.release()
        self.root.destroy()


def main():
    root = tk.Tk()
    CameraApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
