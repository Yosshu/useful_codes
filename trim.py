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

        # === Canvas ===
        self.canvas = tk.Canvas(self.root)
        self.canvas.pack()

        # === Slider ===
        self.slider = ttk.Scale(
            self.root, from_=0, to=0,
            orient="horizontal",
            command=self.show_frame,
            state="disabled"
        )
        self.slider.pack(fill="x", padx=10, pady=5)

        # === Frame index input ===
        frame_input_frame = tk.Frame(self.root)
        frame_input_frame.pack(pady=5)

        self.frame_var = tk.StringVar()
        tk.Label(frame_input_frame, text="frame").pack(side="left")
        tk.Entry(frame_input_frame, textvariable=self.frame_var, width=8).pack(side="left", padx=5)
        tk.Button(
            frame_input_frame,
            text="フレーム指定反映",
            command=self.apply_frame_input
        ).pack(side="left", padx=5)

        # === Buttons ===
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5)

        tk.Button(button_frame, text="動画ファイル選択 (O)", command=self.select_video_file).pack(side="left", padx=5)
        tk.Button(button_frame, text="トリミング (T)", command=self.trim_frame).pack(side="left", padx=5)
        tk.Button(button_frame, text="キャンセル (Esc)", command=self.cancel_selection).pack(side="left", padx=5)

        # === Pixel input ===
        pixel_frame = tk.Frame(self.root)
        pixel_frame.pack(pady=5)

        self.x1_var = tk.StringVar()
        self.y1_var = tk.StringVar()
        self.x2_var = tk.StringVar()
        self.y2_var = tk.StringVar()

        for label, var in [("x1", self.x1_var), ("y1", self.y1_var),
                           ("x2", self.x2_var), ("y2", self.y2_var)]:
            tk.Label(pixel_frame, text=label).pack(side="left")
            tk.Entry(pixel_frame, textvariable=var, width=6).pack(side="left", padx=3)

        tk.Button(pixel_frame, text="ピクセル指定反映", command=self.apply_pixel_input).pack(side="left", padx=10)

        # === Info ===
        self.original_size_label = tk.Label(self.root, text="トリミング範囲: 未選択", anchor="w")
        self.original_size_label.pack(fill="x", padx=10)

        # === State ===
        self.cap = None
        self.frame = None
        self.scale = 1.0
        self.rect_start = None
        self.rect_id = None
        self.trim_pixels = None  # (x1,y1,x2,y2) in original pixels

        # === Bindings ===
        self.canvas.bind("<ButtonPress-1>", self.on_left_click_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_click_up)

        self.root.bind("o", lambda e: self.select_video_file())
        self.root.bind("t", lambda e: self.trim_frame())
        self.root.bind("<Escape>", lambda e: self.cancel_selection())
        self.root.bind("<Left>", lambda e: self.move_frame(-1))
        self.root.bind("<Right>", lambda e: self.move_frame(1))

        # === Output dir ===
        self.output_dir = "output"
        os.makedirs(self.output_dir, exist_ok=True)

    # ---------------- Video ----------------
    def select_video_file(self):
        path = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.avi *.mov")])
        if path:
            self.video_path = path
            self.load_video()

    def load_video(self):
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(self.video_path)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.slider.config(to=self.frame_count - 1, state="normal")
        self.show_frame(0)

    def show_frame(self, idx):
        if not self.cap:
            return

        idx = int(float(idx))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = self.cap.read()
        if not ret:
            return

        self.frame = frame
        self.frame_var.set(str(idx))  # sync entry

        h, w, _ = frame.shape
        self.scale = min(800 / w, 600 / h, 1)

        disp_w, disp_h = int(w * self.scale), int(h * self.scale)
        self.canvas.config(width=disp_w, height=disp_h)

        img = cv2.resize(frame, (disp_w, disp_h))
        self.image = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)))
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.image, anchor="nw")

        if self.trim_pixels:
            self.draw_rect_from_pixels()

    def apply_frame_input(self):
        if not self.cap:
            return
        try:
            idx = int(self.frame_var.get())
        except ValueError:
            return

        idx = max(0, min(self.frame_count - 1, idx))
        self.slider.set(idx)
        self.show_frame(idx)

    # ---------------- Interaction ----------------
    def on_left_click_down(self, e):
        self.rect_start = (e.x, e.y)

    def on_mouse_drag(self, e):
        if not self.rect_start:
            return
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.rect_start[0], self.rect_start[1], e.x, e.y, outline="red"
        )

    def on_left_click_up(self, e):
        x1, y1 = self.rect_start
        x2, y2 = e.x, e.y
        self.set_trim_from_canvas(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))

    # ---------------- Sync logic ----------------
    def set_trim_from_canvas(self, cx1, cy1, cx2, cy2):
        px1 = int(cx1 / self.scale)
        py1 = int(cy1 / self.scale)
        px2 = int(cx2 / self.scale)
        py2 = int(cy2 / self.scale)

        self.trim_pixels = (px1, py1, px2, py2)
        self.update_entries()
        self.draw_rect_from_pixels()
        self.update_label()

    def apply_pixel_input(self):
        try:
            px1 = int(self.x1_var.get())
            py1 = int(self.y1_var.get())
            px2 = int(self.x2_var.get())
            py2 = int(self.y2_var.get())
        except ValueError:
            return

        self.trim_pixels = (px1, py1, px2, py2)
        self.draw_rect_from_pixels()
        self.update_label()

    def draw_rect_from_pixels(self):
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        cx1 = int(self.trim_pixels[0] * self.scale)
        cy1 = int(self.trim_pixels[1] * self.scale)
        cx2 = int(self.trim_pixels[2] * self.scale)
        cy2 = int(self.trim_pixels[3] * self.scale)
        self.rect_id = self.canvas.create_rectangle(cx1, cy1, cx2, cy2, outline="red")

    def update_entries(self):
        x1, y1, x2, y2 = self.trim_pixels
        self.x1_var.set(x1)
        self.y1_var.set(y1)
        self.x2_var.set(x2)
        self.y2_var.set(y2)

    def update_label(self):
        x1, y1, x2, y2 = self.trim_pixels
        self.original_size_label.config(
            text=f"トリミング範囲: ({x1},{y1}) - ({x2},{y2})  サイズ {x2-x1}×{y2-y1}"
        )

    # ---------------- Save ----------------
    def trim_frame(self):
        if self.frame is None:
            return

        frame_idx = int(self.slider.get())

        if self.trim_pixels:
            x1, y1, x2, y2 = self.trim_pixels
            cropped = self.frame[y1:y2, x1:x2]
            suffix = f"_f{frame_idx}_x{x1}_y{y1}_x{x2}_y{y2}"
        else:
            cropped = self.frame
            suffix = f"_f{frame_idx}"

        path = os.path.join(self.output_dir, f"trimmed{suffix}.jpg")
        cv2.imwrite(path, cropped)
        print(f"保存: {path}")

    # ---------------- Cancel ----------------
    def cancel_selection(self):
        if self.rect_id:
            self.canvas.delete(self.rect_id)
            self.rect_id = None

        self.trim_pixels = None
        self.rect_start = None

        self.x1_var.set("")
        self.y1_var.set("")
        self.x2_var.set("")
        self.y2_var.set("")

        self.original_size_label.config(text="トリミング範囲: 未選択")

    # ---------------- Move ----------------
    def move_frame(self, step):
        idx = int(self.slider.get())
        idx = max(0, min(self.frame_count - 1, idx + step))
        self.slider.set(idx)
        self.show_frame(idx)


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoTrimmerApp(root)
    root.mainloop()
