"""GPU の空き状況を監視するツール（nvidia-smi ベース）。

研究室の共用サーバーなどで、空いている GPU を待ちたいときに使う。
標準では見やすい表をリアルタイム更新し、GPU が空くとベルで知らせる。

例:
    # 2秒ごとに監視（Ctrl-C で終了）
    python gpu_watch.py

    # 空き GPU が出るまで待って終了（スクリプトで連結できる）
    python gpu_watch.py --wait && python train.py

    # 空いた GPU を掴んで学習を開始（CUDA_VISIBLE_DEVICES を自動設定）
    python gpu_watch.py --run "python train.py"

    # 現在の状態を1回だけ表示
    python gpu_watch.py --once

「空き」の判定は、使用メモリが --mem-threshold 以下 かつ
GPU 使用率が --util-threshold 以下、で行う。
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

QUERY = "index,name,utilization.gpu,memory.used,memory.total,temperature.gpu"

# ANSI エスケープ
CLEAR = "\033[H\033[J"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"


def to_int(s):
    """"[N/A]" などを含みうる数値文字列を int か None にする。"""
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def query_gpus():
    """nvidia-smi から GPU 情報を取得。見つからなければ None、失敗時は空リスト。"""
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.check_output(
            [exe, f"--query-gpu={QUERY}", "--format=csv,noheader,nounits"],
            text=True, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return []

    gpus = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 6:
            continue
        gpus.append({
            "index": to_int(parts[0]),
            "name": parts[1],
            "util": to_int(parts[2]),
            "mem_used": to_int(parts[3]),
            "mem_total": to_int(parts[4]),
            "temp": to_int(parts[5]),
        })
    return gpus


def is_free(g, mem_th, util_th):
    """使用メモリ・使用率がしきい値以下なら空きとみなす。"""
    mem_ok = g["mem_used"] is not None and g["mem_used"] <= mem_th
    util_ok = g["util"] is None or g["util"] <= util_th
    return mem_ok and util_ok


def color(text, code, enabled):
    return f"{code}{text}{RESET}" if enabled else text


def render(gpus, args, use_color):
    """GPU 一覧を表形式の文字列にする。"""
    lines = []
    header = f"{'GPU':<4}{'Name':<22}{'Util':>6}  {'Memory':<22}{'Temp':>6}  Status"
    lines.append(color(header, BOLD, use_color))
    lines.append("-" * len(header))
    for g in gpus:
        if args.gpu is not None and g["index"] != args.gpu:
            continue
        name = (g["name"][:20] + "..") if len(g["name"]) > 22 else g["name"]
        util = "N/A" if g["util"] is None else f"{g['util']}%"
        temp = "N/A" if g["temp"] is None else f"{g['temp']}C"
        if g["mem_used"] is not None and g["mem_total"]:
            pct = round(100 * g["mem_used"] / g["mem_total"])
            mem = f"{g['mem_used']}/{g['mem_total']}MiB ({pct}%)"
        else:
            mem = "N/A"
        free = is_free(g, args.mem_threshold, args.util_threshold)
        status = color("FREE", GREEN, use_color) if free else color("BUSY", YELLOW, use_color)
        lines.append(f"{g['index']:<4}{name:<22}{util:>6}  {mem:<22}{temp:>6}  {status}")
    return "\n".join(lines)


def free_gpus(gpus, args):
    """しきい値を満たす空き GPU（--gpu 指定があれば限定）の一覧。"""
    return [
        g for g in gpus
        if (args.gpu is None or g["index"] == args.gpu)
        and is_free(g, args.mem_threshold, args.util_threshold)
    ]


def require_gpus():
    gpus = query_gpus()
    if gpus is None:
        print("nvidia-smi が見つかりませんでした。NVIDIA ドライバが必要です。", file=sys.stderr)
        sys.exit(1)
    return gpus


def monitor(args, use_color):
    """リアルタイム監視。GPU が新たに空いたらベルで通知。"""
    prev_free = set()
    try:
        while True:
            gpus = require_gpus()
            frame = render(gpus, args, use_color)
            sys.stdout.write(CLEAR + frame + "\n")
            now_free = {g["index"] for g in free_gpus(gpus, args)}
            newly = now_free - prev_free
            if newly and not args.no_bell:
                sys.stdout.write("\a")
                sys.stdout.write(color(f"\n>> GPU {sorted(newly)} が空きました\n", GREEN, use_color))
            prev_free = now_free
            sys.stdout.flush()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print()


def wait_for_free(args, use_color):
    """空き GPU が現れるまで待ち、その一覧を返す。"""
    while True:
        gpus = require_gpus()
        free = free_gpus(gpus, args)
        if free:
            return free
        idxs = [g["index"] for g in gpus]
        sys.stdout.write(color(f"\r空き GPU を待機中... 監視対象: {idxs}   ", YELLOW, use_color))
        sys.stdout.flush()
        time.sleep(args.interval)


def parse_args():
    p = argparse.ArgumentParser(
        description="GPU の空き状況を監視する（nvidia-smi）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("-n", "--interval", type=float, default=2.0, help="更新間隔（秒、既定: 2.0）")
    p.add_argument("--mem-threshold", type=int, default=1000,
                   help="空きとみなす使用メモリの上限 MiB（既定: 1000）")
    p.add_argument("--util-threshold", type=int, default=10,
                   help="空きとみなす GPU 使用率の上限 %%（既定: 10）")
    p.add_argument("--gpu", type=int, help="特定の GPU 番号だけを対象にする")
    p.add_argument("--wait", action="store_true", help="空き GPU が出たら表示して終了")
    p.add_argument("--run", help="空き GPU を掴んでこのコマンドを実行する")
    p.add_argument("--once", action="store_true", help="現在の状態を1回だけ表示して終了")
    p.add_argument("--no-bell", action="store_true", help="空き時のベルを鳴らさない")
    p.add_argument("--no-color", action="store_true", help="色付けを無効にする")
    return p.parse_args()


def main():
    args = parse_args()
    use_color = not args.no_color and sys.stdout.isatty()

    if args.once:
        print(render(require_gpus(), args, use_color))
        return

    if args.run:
        free = wait_for_free(args, use_color)
        g = free[0]
        print(color(f"\n>> GPU {g['index']} ({g['name']}) を使用してコマンドを実行します。",
                    GREEN, use_color))
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = str(g["index"])
        sys.exit(subprocess.call(args.run, shell=True, env=env))

    if args.wait:
        free = wait_for_free(args, use_color)
        idxs = [g["index"] for g in free]
        print(color(f"\n空き GPU: {idxs}", GREEN, use_color))
        return

    monitor(args, use_color)


if __name__ == "__main__":
    main()
