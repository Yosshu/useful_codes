# useful_codes

画像・映像処理まわりでよく使う小さな Python スクリプト集です。OpenCV を中心に、カメラ入力・動画からのフレーム抽出・キャリブレーション用点群取得などをまとめています。

## 必要環境

- Python 3.8+
- opencv-python
- numpy
- Pillow（`trim.py` / `camera_app.py` / `uniform_size.py` / `img_convert.py` で使用）
- Tkinter（`trim.py` / `camera_app.py` で使用。標準では同梱、Linux では別途 `python3-tk` の導入が必要な場合あり）
- NVIDIA ドライバ・`nvidia-smi`（`gpu_watch.py` で使用）

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

カメラ映像をウィンドウで常時プレビューし、キー操作で録画を開始・停止して `.mp4` として保存します。

**実行方法**

```bash
python record_video.py
```

**操作**

| キー | 動作 |
| --- | --- |
| `R` | 録画を開始。録画中にもう一度押すと停止して保存 |
| `Esc` | 終了。録画中の場合は、その時点までを保存 |

録画ファイルは、録画開始日時を含む `recorded_video_YYYYMMDD_HHMMSS_mmm.mp4` 形式で保存されます。

**設定項目（`__main__` 内の変数を編集）**

- `output_file` — 出力ファイル名のベース（既定: `recorded_video.mp4`。保存時に日時が自動挿入されます）
- `recording_fps` — 録画フレームレート（既定: 10 fps）
- `recording_width` / `recording_height` — プレビュー・録画解像度（既定: 1280×720）

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

### camera_app.py

Tkinter のウィンドウでカメラ映像を確認しながら、写真撮影と動画録画の両方を行えるアプリです。

**実行方法**

```bash
python camera_app.py
```

**操作**

| ボタン / キー | 動作 |
| --- | --- |
| 「写真撮影」 / `P` | 現在の映像を PNG 画像として保存 |
| 「録画開始・停止」 / `R` | MP4 動画の録画を開始・停止 |
| 「カメラ再検索」 | カメラID `0`〜`4` を再検索し、映像を取得できるカメラへ接続 |
| 「終了」 / `Esc` | アプリを終了。録画中の場合は、その時点までを保存 |

写真は `camera_output/photos/photo_YYYYMMDD_HHMMSS_mmm.png`、動画は `camera_output/videos/video_YYYYMMDD_HHMMSS_mmm.mp4` 形式で保存されます。

> 起動時は既定のOpenCVバックエンドを使い、カメラID `0`〜`4` のうち実際に映像を取得できるものへ自動接続します。映像が表示されない場合は「カメラ再検索」を押してください。macOSでは「システム設定 > プライバシーとセキュリティ > カメラ」の権限も確認してください。

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

### uniform_size.py

複数画像のサイズ（アスペクト比）を一括で揃えるツール。論文の subfigure などで、画像の大きさを合わせたいときに使います。揃えた画像は出力ディレクトリ（既定: `uniform_output/`）に保存されます。入力はファイル・ディレクトリ・ワイルドカードで指定できます。

**実行方法**

```bash
# フォルダ内の画像を、最大サイズに合わせて余白パディングで統一
python uniform_size.py figs/

# 幅640×高さ480に、中央クロップで統一
python uniform_size.py a.png b.png c.png --size 640x480 --mode crop

# 基準画像に合わせ、余白は黒で
python uniform_size.py figs/ --match ref.png --bg black
```

**主なオプション**

| オプション | 説明 |
| --- | --- |
| `-o, --output` | 出力ディレクトリ（既定: `uniform_output`） |
| `--size 幅x高さ` | 目標サイズを直接指定 |
| `--match FILE` | 指定ファイルのサイズに合わせる（省略時は入力中の最大サイズ） |
| `--mode` | `pad`=余白で揃える（既定） / `crop`=中央クロップ / `stretch`=引き伸ばし |
| `--bg` | 余白の色。色名 / `#RRGGBB` / `R,G,B`（既定: white） |
| `--format` | 出力形式を変換（例: `png`, `jpg`） |

### img_convert.py

画像フォーマット・DPI をまとめて変換するツール。論文投稿で png → pdf / eps などに変換したいときに使います。入力はファイル・ディレクトリ・ワイルドカードで指定できます。

> 注: pdf / eps はラスタ画像として書き出します（ベクタ化はしません）。

**実行方法**

```bash
# フォルダ内の画像をすべて 300dpi の PDF に
python img_convert.py figs/ -f pdf --dpi 300

# png を高品質 jpg に（透過は白で埋める）
python img_convert.py a.png b.png -f jpg --quality 95

# 出力先を指定して eps に
python img_convert.py plot.png -f eps -o submission/
```

**主なオプション**

| オプション | 説明 |
| --- | --- |
| `-f, --to` | 変換先の形式（`png` / `jpg` / `pdf` / `eps` / `tiff` / `bmp` / `webp` / `gif`）※必須 |
| `-o, --output` | 出力ディレクトリ（省略時は入力と同じ場所） |
| `--dpi` | DPI を設定（pdf / tiff / 印刷用に有効） |
| `--quality` | jpg / webp の品質 1-100（既定: 95） |
| `--bg` | 透過を埋める背景色（既定: white） |

### gpu_watch.py

`nvidia-smi` をもとに GPU の空き状況を監視するツール。共用サーバーなどで空いている GPU を待ちたいときに使います。標準では見やすい表をリアルタイム更新し、GPU が空くとベルで通知します。「空き」は、使用メモリが `--mem-threshold` 以下 かつ 使用率が `--util-threshold` 以下、で判定します。

**実行方法**

```bash
# 2秒ごとに監視（Ctrl-C で終了）
python gpu_watch.py

# 空き GPU が出るまで待って終了（スクリプトで連結できる）
python gpu_watch.py --wait && python train.py

# 空いた GPU を掴んで学習を開始（CUDA_VISIBLE_DEVICES を自動設定）
python gpu_watch.py --run "python train.py"

# 現在の状態を1回だけ表示
python gpu_watch.py --once
```

**主なオプション**

| オプション | 説明 |
| --- | --- |
| `-n, --interval` | 更新間隔（秒、既定: 2.0） |
| `--mem-threshold` | 空きとみなす使用メモリの上限 MiB（既定: 1000） |
| `--util-threshold` | 空きとみなす GPU 使用率の上限 %（既定: 10） |
| `--gpu` | 特定の GPU 番号だけを対象にする |
| `--wait` | 空き GPU が出たら表示して終了 |
| `--run CMD` | 空き GPU を掴んでコマンドを実行 |
| `--once` | 現在の状態を1回だけ表示して終了 |
