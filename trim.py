import cv2
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from PIL import Image, ImageTk
import os
import time

class VideoTrimmerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("動画から画像の切り出し")

        # 画像を表示するためのキャンバス
        self.canvas = tk.Canvas(self.root)
        self.canvas.pack()

        # シークバーの設定
        self.slider = ttk.Scale(self.root, from_=0, to=0, orient="horizontal", command=self.show_frame, state="disabled")
        self.slider.pack(fill="x", padx=10, pady=10)

        # ボタンフレーム
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=10)

        self.select_button = tk.Button(button_frame, text="動画ファイルの選択", command=self.select_video_file)
        self.select_button.pack(side="left", padx=5)

        self.trim_button = tk.Button(button_frame, text="トリミング", command=self.trim_frame)
        self.trim_button.pack(side="left", padx=5)

        self.cancel_button = tk.Button(button_frame, text="トリミング範囲をキャンセル", command=self.cancel_selection)
        self.cancel_button.pack(side="left", padx=5)

        self.rect_start = None
        self.rect_end = None
        self.rect_id = None
        self.frame = None
        self.trimming_rect = None
        self.cap = None

        self.canvas.bind("<ButtonPress-1>", self.on_left_click_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_click_up)

        # 保存先のフォルダを準備
        self.output_dir = "output"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def select_video_file(self):
        video_path = filedialog.askopenfilename(title="動画ファイルの選択", filetypes=[("動画ファイル", "*.mp4 *.avi *.mov")])
        if video_path:
            self.video_path = video_path
            self.load_video()

    def load_video(self):
        if self.cap:
            self.cap.release()

        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            print("動画の読み込みに失敗しました。")
            return

        self.slider.config(to=self.cap.get(cv2.CAP_PROP_FRAME_COUNT) - 1, state="normal")
        self.show_frame(0)

    def show_frame(self, frame_idx):
        if not self.cap or not self.cap.isOpened():
            return

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, int(float(frame_idx)))
        ret, frame = self.cap.read()
        if not ret:
            return

        self.frame = frame

        frame_h, frame_w, _ = frame.shape
        self.canvas.config(width=frame_w, height=frame_h)

        self.image = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
        self.canvas.create_image(0, 0, image=self.image, anchor="nw")

        if self.trimming_rect:
            self.canvas.delete(self.rect_id)
            self.rect_id = self.canvas.create_rectangle(self.trimming_rect[0], self.trimming_rect[1], self.trimming_rect[2], self.trimming_rect[3], outline="red")

    def on_left_click_down(self, event):
        self.rect_start = (event.x, event.y)

    def on_mouse_drag(self, event):
        if self.rect_start:
            self.rect_end = (event.x, event.y)
            if self.rect_id:
                self.canvas.delete(self.rect_id)
            self.rect_id = self.canvas.create_rectangle(self.rect_start[0], self.rect_start[1], self.rect_end[0], self.rect_end[1], outline="red")

    def on_left_click_up(self, event):
        self.rect_end = (event.x, event.y)
        self.trimming_rect = (*self.rect_start, *self.rect_end)

    def cancel_selection(self):
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_start = None
        self.rect_end = None
        self.trimming_rect = None

    def trim_frame(self):
        if self.frame is None:
            return

        if self.rect_start and self.rect_end:
            x1, y1 = self.rect_start
            x2, y2 = self.rect_end

            trimmed_frame = self.frame[int(y1):int(y2), int(x1):int(x2)]
        else:
            trimmed_frame = self.frame

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(self.output_dir, f"trimmed_frame_{timestamp}.jpg")
        cv2.imwrite(output_path, trimmed_frame)
        print(f"画像を保存しました: {output_path}")

        if self.trimming_rect:
            self.canvas.delete(self.rect_id)
            self.rect_id = self.canvas.create_rectangle(self.trimming_rect[0], self.trimming_rect[1], self.trimming_rect[2], self.trimming_rect[3], outline="red")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoTrimmerApp(root)
    root.mainloop()
