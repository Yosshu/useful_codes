"""Tkinter で写真撮影と動画録画を行うカメラアプリ。"""

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

        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            self.cap.release()
            messagebox.showerror("カメラエラー", "カメラが見つかりませんでした。")
            raise RuntimeError("カメラが見つかりませんでした。")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

        self.current_frame = None
        self.writer = None
        self.recording = False
        self.current_video_path = None
        self.running = True
        self.after_id = None

        self.root.title("Camera App")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.bind("<Key-r>", self.toggle_recording)
        self.root.bind("<Key-R>", self.toggle_recording)
        self.root.bind("<Key-p>", self.take_photo)
        self.root.bind("<Key-P>", self.take_photo)
        self.root.bind("<Escape>", self.close)

        self.preview_label = tk.Label(self.root, bg="black")
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

        ttk.Button(controls, text="終了 (Esc)", command=self.close).pack(
            side="left"
        )

        self.status = tk.StringVar(value="プレビュー中")
        ttk.Label(controls, textvariable=self.status).pack(side="right")

        self.update_frame()

    @staticmethod
    def timestamp():
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]

    def update_frame(self):
        if not self.running:
            return

        ret, frame = self.cap.read()
        if not ret:
            if self.recording:
                self.stop_recording()
            self.status.set("カメラ映像を取得できませんでした。再試行中...")
            self.after_id = self.root.after(100, self.update_frame)
            return

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
        self.preview_label.configure(image=photo)
        self.preview_label.image = photo

        interval_ms = max(1, round(1000 / self.fps))
        self.after_id = self.root.after(interval_ms, self.update_frame)

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
            self.root.after_cancel(self.after_id)
            self.after_id = None
        if self.recording:
            self.stop_recording()
        self.cap.release()
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        CameraApp(root)
    except RuntimeError:
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
