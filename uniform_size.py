"""複数画像のサイズ（アスペクト比）を揃えるツール。

論文の subfigure などで、複数の画像を同じ大きさに揃えたいときに使う。
入力はファイル・ディレクトリ・ワイルドカードのいずれでも指定でき、
揃えた画像は出力ディレクトリ（既定: uniform_output/）に保存される。

例:
    # フォルダ内の画像を、最大サイズに合わせて余白パディングで統一
    python uniform_size.py figs/

    # 幅640x高さ480に、中央クロップで統一
    python uniform_size.py a.png b.png c.png --size 640x480 --mode crop

    # 基準画像に合わせ、余白は黒で
    python uniform_size.py figs/ --match ref.png --bg black
"""
import argparse
import glob
import os
import sys

from PIL import Image, ImageColor

# Pillow 9.1 以降とそれ以前でリサンプリング定数の場所が違う
try:
    RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:  # 古い Pillow
    RESAMPLE = Image.LANCZOS

IMG_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".gif"}


def parse_size(text):
    """"640x480" のような文字列を (640, 480) に変換する。"""
    s = text.lower().replace("×", "x").replace(" ", "")
    if "x" not in s:
        raise argparse.ArgumentTypeError("サイズは 幅x高さ（例: 640x480）の形式で指定してください")
    w, h = s.split("x", 1)
    return int(w), int(h)


def parse_color(text):
    """色名 / #RRGGBB / "R,G,B" を (R, G, B) タプルにする。"""
    s = text.strip()
    if "," in s:
        parts = [int(p) for p in s.split(",")]
        if len(parts) != 3:
            raise argparse.ArgumentTypeError("色は R,G,B の3値で指定してください")
        return tuple(parts)
    return ImageColor.getrgb(s)


def collect_inputs(paths):
    """ファイル・ディレクトリ・ワイルドカードをまとめて画像ファイル一覧にする。"""
    files = []
    for p in paths:
        if os.path.isdir(p):
            for name in sorted(os.listdir(p)):
                fp = os.path.join(p, name)
                if os.path.isfile(fp) and os.path.splitext(name)[1].lower() in IMG_EXTS:
                    files.append(fp)
        elif os.path.isfile(p):
            files.append(p)
        else:  # シェルが展開しなかった場合のワイルドカード対応
            files.extend(sorted(glob.glob(p)))
    return files


def flatten(im, bg):
    """透過を背景色 bg で塗りつぶして RGB 画像にする。"""
    if im.mode == "RGBA":
        base = Image.new("RGB", im.size, bg)
        base.paste(im, mask=im.split()[-1])
        return base
    if im.mode == "P" and "transparency" in im.info:
        return flatten(im.convert("RGBA"), bg)
    if im.mode != "RGB":
        return im.convert("RGB")
    return im


def fit_pad(im, tw, th, bg):
    """アスペクト比を保ったまま tw x th に収め、余白を bg で埋める（レターボックス）。"""
    iw, ih = im.size
    scale = min(tw / iw, th / ih)
    nw, nh = max(1, round(iw * scale)), max(1, round(ih * scale))
    resized = flatten(im.resize((nw, nh), RESAMPLE), bg)
    canvas = Image.new("RGB", (tw, th), bg)
    canvas.paste(resized, ((tw - nw) // 2, (th - nh) // 2))
    return canvas


def fit_crop(im, tw, th, bg):
    """アスペクト比を保ったまま tw x th を覆うように拡大し、はみ出しを中央クロップ。"""
    im = flatten(im, bg)
    iw, ih = im.size
    scale = max(tw / iw, th / ih)
    nw, nh = max(1, round(iw * scale)), max(1, round(ih * scale))
    resized = im.resize((nw, nh), RESAMPLE)
    left, top = (nw - tw) // 2, (nh - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def fit_stretch(im, tw, th, bg):
    """アスペクト比を無視して tw x th へ引き伸ばす（歪む）。"""
    return flatten(im, bg).resize((tw, th), RESAMPLE)


MODES = {"pad": fit_pad, "crop": fit_crop, "stretch": fit_stretch}


def compute_target(sizes, args):
    """目標サイズ (幅, 高さ) を決める。"""
    if args.size:
        return args.size
    if args.match:
        with Image.open(args.match) as im:
            return im.size
    # 既定: 入力中の最大幅・最大高さ（すべての画像が収まる）
    tw = max(w for w, h in sizes)
    th = max(h for w, h in sizes)
    return tw, th


def parse_args():
    p = argparse.ArgumentParser(
        description="複数画像のサイズ（アスペクト比）を揃える",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("inputs", nargs="+", help="画像ファイル / ディレクトリ / ワイルドカード")
    p.add_argument("-o", "--output", default="uniform_output", help="出力ディレクトリ（既定: uniform_output）")
    p.add_argument("--size", type=parse_size, help="目標サイズ 幅x高さ（例: 640x480）")
    p.add_argument("--match", help="このファイルのサイズに合わせる")
    p.add_argument(
        "--mode", choices=list(MODES), default="pad",
        help="pad=余白で揃える / crop=中央クロップ / stretch=引き伸ばし（既定: pad）",
    )
    p.add_argument("--bg", type=parse_color, default=(255, 255, 255),
                   help="余白の色。色名/#RRGGBB/R,G,B（既定: white）")
    p.add_argument("--format", help="出力形式を変換（例: png, jpg）。省略時は元の拡張子を維持")
    return p.parse_args()


def main():
    args = parse_args()
    files = collect_inputs(args.inputs)
    if not files:
        print("画像が見つかりませんでした。", file=sys.stderr)
        sys.exit(1)

    # 1回目: サイズだけ取得して目標サイズを決める
    sizes = []
    for f in files:
        with Image.open(f) as im:
            sizes.append(im.size)
    tw, th = compute_target(sizes, args)

    os.makedirs(args.output, exist_ok=True)
    func = MODES[args.mode]

    print(f"目標サイズ: {tw}x{th} / モード: {args.mode} / 対象: {len(files)}枚")
    for f in files:
        with Image.open(f) as im:
            out = func(im, tw, th, args.bg)
        stem = os.path.splitext(os.path.basename(f))[0]
        ext = ("." + args.format.lstrip(".")) if args.format else os.path.splitext(f)[1]
        outpath = os.path.join(args.output, stem + ext)
        # JPEG は RGB のみ
        if ext.lower() in (".jpg", ".jpeg"):
            out = out.convert("RGB")
        out.save(outpath)
        print(f"  保存: {outpath}")


if __name__ == "__main__":
    main()
