import cv2
import os


WINDOW_NAME = "Camera Preview"


def build_output_path(output_path, recording_index):
    """2回目以降の録画では、既存の録画を上書きしないファイル名を作る。"""
    if recording_index == 1:
        return output_path
    stem, ext = os.path.splitext(output_path)
    return f"{stem}_{recording_index}{ext}"


def open_writer(output_path, fps, frame):
    """現在のカメラフレームと同じサイズで MP4 の書き込みを開始する。"""
    height, width = frame.shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not writer.isOpened():
        writer.release()
        raise RuntimeError(f"録画ファイルを開けませんでした: {output_path}")
    return writer


def record_video(output_path, fps=30, width=640, height=480):
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("カメラが見つかりませんでした。")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)

    writer = None
    recording = False
    recording_index = 0
    current_output_path = None

    cv2.namedWindow(WINDOW_NAME)
    print("R: 録画開始 / 停止")
    print("Esc: 終了")

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("映像のキャプチャ中にエラーが発生しました。")
                break

            if recording:
                writer.write(frame)

            preview = frame.copy()
            status_text = "REC" if recording else "PREVIEW"
            status_color = (0, 0, 255) if recording else (0, 255, 0)
            cv2.putText(
                preview,
                status_text,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                status_color,
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                preview,
                "R: Start/Stop recording   Esc: Quit",
                (20, preview.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            cv2.imshow(WINDOW_NAME, preview)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("r"), ord("R")):
                if recording:
                    writer.release()
                    writer = None
                    recording = False
                    print("映像を保存しました:", current_output_path)
                else:
                    recording_index += 1
                    current_output_path = build_output_path(
                        output_path, recording_index
                    )
                    try:
                        writer = open_writer(current_output_path, fps, frame)
                    except RuntimeError as error:
                        print(error)
                        writer = None
                        continue
                    recording = True
                    print("録画を開始しました:", current_output_path)
            elif key == 27:
                break
    finally:
        if writer is not None:
            writer.release()
            print("映像を保存しました:", current_output_path)
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    output_file = "recorded_video.mp4"
    recording_fps = 10
    recording_width = 1280
    recording_height = 720

    record_video(
        output_file,
        fps=recording_fps,
        width=recording_width,
        height=recording_height,
    )
