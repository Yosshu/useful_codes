# useful_codes

画像・映像処理まわりでよく使う小さな Python スクリプト集です。OpenCV を中心に、カメラ入力・動画からのフレーム抽出・キャリブレーション用点群取得などをまとめています。

## 必要環境

- Python 3.8+
- opencv-python
- numpy
- Pillow（`trim.py` で使用）
- Tkinter（`trim.py` で使用。標準では同梱、Linux では別途 `python3-tk` の導入が必要な場合あり）

```bash
pip install opencv-python numpy pillow
```

## スクリプト一覧

### get_imgpoints.py

カメラキャリブレーション用の画像座標を取得するツール。カメラ映像上の点をクリックして収集し、終了時に `[x1 y1 x2 y2 ...]` の 1 行形式で出力します。

**実行方法**

```bash
python get_imgpoints.py
```

**操作**

| キー / 操作 | 動作 |
| --- | --- |
| 左クリック | クリック位置を点として追加 |
| `W` / `A` / `S` / `D` | 直近に追加した点を 1 px 上/左/下/右に微調整 |
| `Z` | 直近に追加した点を取り消し |
| `R` | 押している間、映像を最新フレームに更新 |
| `Esc` | 終了。点群座標を標準出力へ出力 |

### record_video.py

指定した秒数だけカメラから動画を撮影して `.mp4` として保存します。

**実行方法**

```bash
python record_video.py
```

**設定項目（`__main__` 内の変数を編集）**

- `output_file` — 出力ファイル名（既定: `recorded_video.mp4`）
- `recording_duration` — 撮影秒数（既定: 10 秒）
- `recording_fps` — フレームレート（既定: 10 fps）
- `recording_width` / `recording_height` — 解像度（既定: 1280×720）

### takingpics.py

カメラ映像から任意のタイミングで静止画を撮影します。撮影した画像は `pic0.png`, `pic1.png`, ... と連番で保存されます。

**実行方法**

```bash
python takingpics.py
```

**操作**

| キー | 動作 |
| --- | --- |
| `A` | 現在のフレームを保存 |
| `Esc` | 終了 |

### trim.py

Tkinter ベースの GUI で、動画ファイルから任意のフレームを選び、範囲をトリミングして画像として保存します。切り出し画像は `output/` ディレクトリに保存されます。

**実行方法**

```bash
python trim.py
```

**主な機能**

- 動画ファイル（`.mp4` / `.avi` / `.mov`）を開いてスライダーやフレーム番号指定で表示位置を移動
- キャンバス上でドラッグして矩形範囲を選択、またはピクセル座標 (x1, y1, x2, y2) を直接入力
- 現在のフレームを選択範囲で切り出して `output/trimmed_f<frame>_x<..>_y<..>.jpg` として保存

**ショートカット**

| キー | 動作 |
| --- | --- |
| `O` | 動画ファイルを開く |
| `T` | 現在フレームをトリミング & 保存 |
| `←` / `→` | 1 フレーム戻る / 進む |
| `Esc` | 選択範囲をキャンセル |
