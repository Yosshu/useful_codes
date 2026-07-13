"""画像フォーマット変換ツール。

論文投稿などで、画像の形式（png / jpg / pdf / eps / tiff …）や DPI を
まとめて変換したいときに使う。入力はファイル・ディレクトリ・ワイルドカード可。

注意: pdf / eps はラスタ画像として書き出す（ベクタ化はしない）。
      入力 pdf / eps の読み込みには別途 Ghostscript が必要になる場合がある。

例:
    # フォルダ内の画像をすべて 300dpi の PDF に
    python img_convert.py figs/ -f pdf --dpi 300

    # png を高品質 jpg に、余白（透過）は白で埋める
    python img_convert.py a.png b.png -f jpg --quality 95

    # 出力先を指定して eps に
    python img_convert.py plot.png -f eps -o submission/
"""
import argparse
import glob
import os
import sys

from PIL import Image

IMG_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".gif"}

# 拡張子 -> Pillow のフォーマット名
FORMAT_MAP = {
    "png": "PNG", "jpg": "JPEG", "jpeg": "JPEG", "pdf": "PDF", "eps": "EPS",
    "tif": "TIFF", "tiff": "TIFF", "bmp": "BMP", "webp": "WEBP", "gif": "GIF",
}
# 透過を扱えない（RGB へ変換が必要な）フォーマット
NO_ALPHA = {"JPEG", "PDF", "EPS", "BMP"}


def parse_color(text):
    s = text.strip()
    if "," in s:
        parts = [int(p) for p in s.split(",")]
        if len(parts) != 3:
            raise argparse.ArgumentTypeError("色は R,G,B の3値で指定してください")
        return tuple(parts)
    from PIL import ImageColor
    return ImageColor.getrgb(s)


def collect_inputs(paths):
    files = []
    for p in paths:
        if os.path.isdir(p):
            for name in sorted(os.listdir(p)):
                fp = os.path.join(p, name)
                if os.path.isfile(fp) and os.path.splitext(name)[1].lower() in IMG_EXTS:
                    files.append(fp)
        elif os.path.isfile(p):
            files.append(p)
        else:
            files.extend(sorted(glob.glob(p)))
    return files


def flatten(im, bg):
    """透過を背景色で塗りつぶして RGB にする。"""
    if im.mode == "RGBA":
        base = Image.new("RGB", im.size, bg)
        base.paste(im, mask=im.split()[-1])
        return base
    if im.mode == "P" and "transparency" in im.info:
        return flatten(im.convert("RGBA"), bg)
    if im.mode != "RGB":
        return im.convert("RGB")
    return im


def save_image(im, path, fmt, dpi, quality):
    """dpi 指定が古い Pillow で弾かれても保存できるようにフォールバックする。"""
    kwargs = {}
    if dpi:
        kwargs["dpi"] = (dpi, dpi)
    if fmt in ("JPEG", "WEBP"):
        kwargs["quality"] = quality
    if fmt in ("JPEG", "PNG"):
        kwargs["optimize"] = True
    try:
        im.save(path, fmt, **kwargs)
    except (TypeError, OSError):
        kwargs.pop("dpi", None)  # dpi が原因のことがあるので外して再試行
        im.save(path, fmt, **kwargs)


def parse_args():
    p = argparse.ArgumentParser(
        description="画像フォーマット / DPI をまとめて変換する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("inputs", nargs="+", help="画像ファイル / ディレクトリ / ワイルドカード")
    p.add_argument("-f", "--to", "--format", dest="to", required=True,
                   help="変換先の形式（png, jpg, pdf, eps, tiff, bmp, webp, gif）")
    p.add_argument("-o", "--output", help="出力ディレクトリ（省略時は入力と同じ場所）")
    p.add_argument("--dpi", type=int, help="DPI を設定（pdf / tiff / 印刷用に有効）")
    p.add_argument("--quality", type=int, default=95, help="jpg / webp の品質 1-100（既定: 95）")
    p.add_argument("--bg", type=parse_color, default=(255, 255, 255),
                   help="透過を埋める背景色。色名/#RRGGBB/R,G,B（既定: white）")
    return p.parse_args()


def main():
    args = parse_args()
    ext = args.to.lower().lstrip(".")
    fmt = FORMAT_MAP.get(ext)
    if not fmt:
        print(f"未対応の形式です: {args.to}（対応: {', '.join(sorted(FORMAT_MAP))}）", file=sys.stderr)
        sys.exit(1)

    files = collect_inputs(args.inputs)
    if not files:
        print("画像が見つかりませんでした。", file=sys.stderr)
        sys.exit(1)

    ok = 0
    for f in files:
        try:
            im = Image.open(f)
        except Exception as e:  # noqa: BLE001  読めないファイルはスキップ
            print(f"  スキップ（読み込み失敗）: {f} ({e})", file=sys.stderr)
            continue

        if fmt in NO_ALPHA:
            im = flatten(im, args.bg)

        stem = os.path.splitext(os.path.basename(f))[0]
        outdir = args.output or os.path.dirname(f) or "."
        os.makedirs(outdir, exist_ok=True)
        outpath = os.path.join(outdir, stem + "." + ext)
        # 入力と同名になってしまう場合は上書きを避ける
        if os.path.abspath(outpath) == os.path.abspath(f):
            outpath = os.path.join(outdir, stem + "_conv." + ext)

        save_image(im, outpath, fmt, args.dpi, args.quality)
        print(f"  保存: {outpath}")
        ok += 1

    print(f"完了: {ok}/{len(files)} 件を {ext} に変換しました。")


if __name__ == "__main__":
    main()
