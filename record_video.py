import cv2
import numpy as np

def record_video(output_path, duration=10, fps=30, width=640, height=480):
    # カメラキャプチャの初期化
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("カメラが見つかりませんでした。")
        return

    # 映像の解像度とフレームレートを設定
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)

    # ビデオエンコーダーの設定
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    # 指定された秒数だけ映像を撮影して保存
    frames_to_record = int(duration * fps)
    for _ in range(frames_to_record):
        ret, frame = cap.read()
        if not ret:
            print("映像のキャプチャ中にエラーが発生しました。")
            break
        out.write(frame)

    # キャプチャを解放して、ファイルを保存
    cap.release()
    out.release()
    print("映像を保存しました:", output_path)

if __name__ == "__main__":
    output_file = "recorded_video.mp4"
    recording_duration = 10  # 秒
    recording_fps = 10
    recording_width = 1280  # 720pの幅
    recording_height = 720  # 720pの高さ

    record_video(output_file, duration=recording_duration, fps=recording_fps,
                 width=recording_width, height=recording_height)
