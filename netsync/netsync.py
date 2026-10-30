#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""netsync —— 内网 <-> 外网代码同步工具（纯 Python 标准库，两侧通用）

通道约束：
  - 内网 -> 外网：只能人工复制粘贴【文本】。本工具把代码打成 tar.gz，
    base64 编码后切成多个块文件（每块一次粘贴），每块带 sha256 校验，
    坏了只需重拷那一块。内容为 ASCII，对编辑器/剪贴板最免疫。
  - 外网 -> 内网：可传文件，直接用 git bundle（见配套文档），不经本脚本。

用法：
  内网（Windows，在代码仓库根目录）：
    python netsync.py pack --out out_sync            # 首次=全量快照；之后=增量补丁(要求已 commit)
    python netsync.py pack --full --out out_sync     # 强制全量
  外网（macOS/Linux/Windows，把粘贴出来的 txt 放进一个文件夹）：
    python3 netsync.py unpack --indir pasted_dir --dest 目标目录
      - 全量快照：解压出整棵代码树
      - 增量补丁：dest 必须是 git 仓库（桥接分支工作区），自动 git apply

块文件带 `NETSYNC-CHUNK` 头；manifest 带 `NETSYNC-MANIFEST` 头。
匹配按 sha256 内容匹配，文件名丢了/乱了也能拼回去。
"""

import argparse
import base64
import datetime
import hashlib
import io
import json
import lzma
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

MANIFEST_MAGIC = "NETSYNC-MANIFEST v1"
CHUNK_MAGIC = "NETSYNC-CHUNK v1"
STATE_FILE = ".netsync-state.json"
DEFAULT_CHUNK_KB = 200         # 默认每块约 200KB 文本（记事本不卡、粘贴快；--chunk-kb 调整）
B64_LINE = 100                 # base64 输出行宽

EXCLUDE_DIRS = {".git", "venv", ".venv", "node_modules", "__pycache__", ".pytest_cache",
                ".idea", ".vscode", ".vite", "dist", "coverage",
                ".bench_results", "out_sync", "release",
                "site-packages", "target", "build", "out", "htmlcov",
                ".mypy_cache", ".ruff_cache", ".tox", ".nox", ".eggs", ".cache"}
EXCLUDE_FILES = {".DS_Store", ".netsync-state.json"}
EXCLUDE_SUFFIX = (".pyc", ".pyo", ".db", ".log")
MAX_FILE_MB = 10          # 单文件超过此值默认跳过并警告（--max-file-mb 0 = 不限制）
BUDGET_MB = 25            # 全量打包产物超过此值：中止并列出大头（--yes 强行继续）


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


# ---- 载荷压缩：xz(LZMA)。比 gzip 少约 25~30% 粘贴量；解包按魔数自动兼容旧 gzip 包 ----
XZ_MAGIC = b"\xfd7zXZ\x00"
GZIP_MAGIC = b"\x1f\x8b"


def compress_payload(raw):
    return lzma.compress(raw, preset=9)


def decompress_payload(blob):
    if blob[:6] == XZ_MAGIC:
        return lzma.decompress(blob)
    if blob[:2] == GZIP_MAGIC:
        import gzip
        return gzip.decompress(blob)
    raise RuntimeError("无法识别的载荷格式（既非 xz 也非 gzip）。")


def build_excludes(extra):
    """内置排除名单 + --add-exclude（目录/文件名，或以 . 开头的扩展名如 .pdf）。"""
    dirs, sufs = set(EXCLUDE_DIRS), list(EXCLUDE_SUFFIX)
    for it in (extra or "").split(","):
        it = it.strip()
        if not it:
            continue
        if it.startswith(".") and len(it) > 2:
            sufs.append(it)
        else:
            dirs.add(it)
    return dirs, tuple(sufs)


def scan_tree(src, include_env=False, extra_exclude=None, max_file_mb=MAX_FILE_MB):
    """返回 (要打包的 [(rel, path, size)], 因超限跳过的 [(rel, size)])"""
    dirs, sufs = build_excludes(extra_exclude)
    limit = max_file_mb * 1048576 if max_file_mb else None
    root = os.path.abspath(src)
    keep, skipped = [], []
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d not in dirs]
        for fn in filenames:
            if fn in EXCLUDE_FILES or fn.endswith(sufs):
                continue
            if fn == ".env" and not include_env:
                continue
            full = os.path.join(dirpath, fn)
            if not (os.path.isfile(full) and not os.path.islink(full)):
                continue
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            sz = os.path.getsize(full)
            if limit and sz > limit:
                skipped.append((rel, sz))
            else:
                keep.append((rel, full, sz))
    return keep, skipped


def top_report(keep, skipped, topn=20):
    lines = ["体积最大的 %d 个文件:" % topn]
    for rel, _, sz in sorted(keep, key=lambda x: -x[2])[:topn]:
        lines.append("  %8.2f MB  %s" % (sz / 1048576, rel))
    agg = {}
    for rel, _, sz in keep:
        top = rel.split("/")[0]
        agg[top] = agg.get(top, 0) + sz
    lines.append("顶层目录合计（前 10）:")
    for d, sz in sorted(agg.items(), key=lambda x: -x[1])[:10]:
        lines.append("  %8.2f MB  %s/" % (sz / 1048576, d))
    if skipped:
        lines.append("因超过单文件上限(--max-file-mb)被跳过的 %d 个文件:" % len(skipped))
        for rel, sz in sorted(skipped, key=lambda x: -x[1])[:10]:
            lines.append("  %8.2f MB  %s" % (sz / 1048576, rel))
    return "\n".join(lines)


def chunk_bytes_of(chunk_kb):
    return chunk_kb * 1000 // 4 * 3   # 每块约 chunk_kb KB 的 base64 文本

def estimate_chunks(total_bytes, chunk_kb=DEFAULT_CHUNK_KB):
    """乐观(压缩一半)与悲观(不压缩)的块数估计"""
    cb = chunk_bytes_of(chunk_kb)
    lo = max(1, -(-int(total_bytes / 2) // cb))
    hi = max(1, -(-int(total_bytes) // cb))
    return lo, hi


def cmd_analyze(args):
    src = os.path.abspath(args.src)
    keep, skipped = scan_tree(src, args.include_env, args.add_exclude, args.max_file_mb)
    total = sum(s for _, _, s in keep)
    lo, hi = estimate_chunks(total)
    print("目录: %s" % src)
    print("将打包 %d 个文件，合计 %.2f MB" % (len(keep), total / 1048576))
    print("估计 %d ~ %d 个块文件（每块一次粘贴）。" % (lo, hi))
    print("排除目录名单: %s" % ", ".join(sorted(build_excludes(args.add_exclude)[0])))
    print()
    print(top_report(keep, skipped))
    print()
    print("若上面出现不该带的目录/文件，用 --add-exclude 名字1,名字2,.扩展名 裁剪后重新 pack。")


def make_tarball_bytes(src, include_env=False, extra_exclude=None, max_file_mb=MAX_FILE_MB):
    """把 src 下的文件树打成内存中的 xz 压缩 tar，返回 (bytes, 文件数, 大文件跳过清单)。"""
    keep, skipped = scan_tree(src, include_env, extra_exclude, max_file_mb)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for rel, full, _sz in keep:
            info = tf.gettarinfo(full, arcname=rel)
            with open(full, "rb") as f:
                tf.addfile(info, f)
    return compress_payload(buf.getvalue()), len(keep), skipped


def git(src, *args, check=True):
    r = subprocess.run(["git", "-C", src] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError("git %s 失败:\n%s" % (" ".join(args), r.stderr.strip()))
    return r


def real_status(src):
    """git status --porcelain，但忽略本工具自己的状态文件（它不该挡住打包）。"""
    out = git(src, "status", "--porcelain").stdout
    return "\n".join(l for l in out.splitlines()
                     if l[3:] != STATE_FILE and not l[3:].startswith("out_sync")).strip()


# 本工具自身产生的文件，git diff/未跟踪清单里都要排除，避免污染补丁
SELF_EXCLUDE_PATHSPECS = [":(exclude).netsync-state.json", ":(exclude)out_sync",
                          ":(exclude)out_sync/*"]


def make_patch_payload(src, since):
    """增量：git diff(since..工作区) + 未跟踪新文件 -> tar.gz bytes"""
    meta = {"mode": "patch", "since": since,
            "time": datetime.datetime.now().isoformat(timespec="seconds")}
    patch = git(src, "diff", "--binary", "--full-index", "--no-color", since, "--",
                *SELF_EXCLUDE_PATHSPECS).stdout
    untracked = []
    r = git(src, "ls-files", "--others", "--exclude-standard", "-z", check=False)
    if r.stdout:
        for name in r.stdout.split("\0"):
            if name and name != STATE_FILE and not name.startswith("out_sync" + os.sep) \
                    and name != "out_sync":
                untracked.append(name)

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        def add_str(name, text):
            data = text.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = int(datetime.datetime.now().timestamp())
            tf.addfile(info, io.BytesIO(data))
        add_str("meta.json", json.dumps(meta, ensure_ascii=True, indent=1))
        add_str("patch.diff", patch)
        for name in untracked:
            full = os.path.join(src, name)
            if os.path.isfile(full):
                info = tf.gettarinfo(full, arcname="untracked/" + name)
                with open(full, "rb") as f:
                    tf.addfile(info, f)
    return compress_payload(buf.getvalue()), len(untracked)


def split_chunks(payload, out_dir, chunk_kb=DEFAULT_CHUNK_KB):
    chunk_chars = chunk_kb * 1000
    """payload(bytes) 切块 -> base64 文本文件 + manifest dict"""
    os.makedirs(out_dir, exist_ok=True)
    chunk_bytes = chunk_chars // 4 * 3          # base64 每 4 字符对应 3 字节
    total = max(1, (len(payload) + chunk_bytes - 1) // chunk_bytes)
    chunks_meta = []
    for idx in range(1, total + 1):
        piece = payload[(idx - 1) * chunk_bytes: idx * chunk_bytes]
        b64 = base64.b64encode(piece).decode("ascii")
        body = "\n".join(b64[i:i + B64_LINE] for i in range(0, len(b64), B64_LINE))
        sha = sha256_bytes(piece)
        header = "%s id=%d/%d sha256=%s" % (CHUNK_MAGIC, idx, total, sha)
        fname = os.path.join(out_dir, "%03d_chunk.txt" % idx)
        with open(fname, "w", encoding="ascii", newline="\n") as f:
            f.write(header + "\n" + body + "\n")
        chunks_meta.append({"id": idx, "sha256": sha, "size": len(piece)})

    manifest = {
        "magic": MANIFEST_MAGIC, "mode": None,
        "chunks": chunks_meta, "total_sha256": sha256_bytes(payload),
        "payload_bytes": len(payload), "time": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    return manifest


def write_manifest(out_dir, manifest):
    path = os.path.join(out_dir, "000_manifest.txt")
    body = json.dumps(manifest, ensure_ascii=True, indent=1)
    with open(path, "w", encoding="ascii", newline="\n") as f:
        f.write(MANIFEST_MAGIC + "\n" + body + "\n")
    return path


def load_state(src):
    p = os.path.join(src, STATE_FILE)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(src, state):
    with open(os.path.join(src, STATE_FILE), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=True, indent=1)


def cmd_ok(args):
    """外网应用成功后，回内网执行一次，推进增量基线。"""
    src = os.path.abspath(args.src)
    state = load_state(src)
    pending = state.get("pending_basis")
    if not pending:
        sys.exit("没有待确认的打包记录（pending_basis 为空），无需 ok。")
    state["next_basis"] = pending
    state.pop("pending_basis", None)
    state["confirmed_at"] = datetime.datetime.now().isoformat(timespec="seconds")
    save_state(src, state)
    print("已确认，增量基线推进至 %s。下次 pack 将只发这之后的新改动。" % pending[:10])


def cmd_pack(args):
    src = os.path.abspath(args.src)
    if not (10 <= args.chunk_kb <= 2000):
        sys.exit("--chunk-kb 取值 10~2000（KB）。")
    state = load_state(src)
    mode = args.mode
    basis = None

    if mode == "patch" or (mode is None and state.get("next_basis")):
        head = git(src, "rev-parse", "HEAD").stdout.strip()
        basis = state.get("next_basis") or args.since or head
        status = real_status(src)
        if status and not args.allow_dirty:
            sys.exit("工作区不干净，增量打包要求先 commit（git add -A && git commit）。\n"
                     "当前改动:\n" + status[:2000] +
                     "\n\n确要带着未提交改动打包请加 --allow-dirty（本次内容下次还会重发）。")
        payload, extra = make_patch_payload(src, basis)
        manifest = split_chunks(payload, args.out, args.chunk_kb)
        manifest["mode"] = "patch"
        manifest["codec"] = "xz"
        manifest["basis"] = basis
        manifest["untracked_files"] = extra
        state.update({"pending_basis": head,
                      "last_pack": manifest["time"], "mode": "patch"})
        save_state(src, state)
    else:
        payload, count, skipped = make_tarball_bytes(
            src, include_env=args.include_env, extra_exclude=args.add_exclude,
            max_file_mb=args.max_file_mb)
        if skipped and not args.quiet:
            print("警告: %d 个文件超过单文件上限 %.0fMB 被跳过:" % (len(skipped), args.max_file_mb))
            for rel, sz in sorted(skipped, key=lambda x: -x[1])[:5]:
                print("  %8.2f MB  %s" % (sz / 1048576, rel))
            print("（要带上它们请加 --max-file-mb <更大值> 或 0）")
        if len(payload) > BUDGET_MB * 1048576 and not args.yes:
            keep, _ = scan_tree(src, args.include_env, args.add_exclude, args.max_file_mb)
            est = estimate_chunks(len(payload), args.chunk_kb)[1]
            print("中止: 打包产物 %.1fMB 超过预算 %dMB，按当前块大小约 %d 个块文件（%d 次复制），"
                  "与同步初衷不符。" % (len(payload) / 1048576, BUDGET_MB, est, est))
            print()
            print(top_report(keep, skipped))
            print()
            print("处理办法:\n"
                  "  1. 看上面的大头，用  --add-exclude 目录1,目录2,.扩展名  排除后重试；\n"
                  "  2. 先运行  python netsync.py analyze  查看完整清单；\n"
                  "  3. 确实全都要带，加 --yes 强制继续。")
            sys.exit(2)
        manifest = split_chunks(payload, args.out, args.chunk_kb)
        manifest["mode"] = "full"
        manifest["codec"] = "xz"
        manifest["files"] = count
        try:
            head = git(src, "rev-parse", "HEAD").stdout.strip()
            status = real_status(src)
            manifest["git_head"] = head
            manifest["git_dirty"] = bool(status)
            if not status:
                state.update({"pending_basis": head,
                              "last_pack": manifest["time"], "mode": "full"})
                save_state(src, state)
            else:
                print("注意: 内网工作区不干净。快照已含未提交改动，但无法记增量基线。\n"
                      "建议: git add -A && git commit 后重新 pack --full，之后走增量。")
        except Exception:
            pass

    write_manifest(args.out, manifest)
    print("打包完成 [%s]: %d 个块文件 + 1 个 manifest，位于 %s" %
          (manifest["mode"], len(manifest["chunks"]), os.path.abspath(args.out)))
    print("总体积 %.2f MB（压缩后），每块约 %d KB 文本。" %
          (manifest["payload_bytes"] / 1048576, args.chunk_kb))
    print("复制提示: 块大->复制次数少但单次久；块小->单次快但次数多。"
          "不合意可用 --chunk-kb <50~700> 调整后重打包。")
    if state.get("pending_basis"):
        print("重要: 外网 unpack 成功后，回内网执行  python netsync.py ok  确认基线，"
              "否则下次会把本轮内容重发一遍。")


# ---------------- unpack ----------------

def _try_b64(b64):
    """容错解码：补 padding；长度非法（如被截断）返回 None 而不是抛异常。"""
    try:
        return base64.b64decode(b64 + "=" * (-len(b64) % 4))
    except Exception:
        return None


def parse_txt(path):
    """读取一个粘贴出来的 txt -> (kind, payload_bytes|manifest_dict)"""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = [ln.strip() for ln in lines if ln.strip()]
    if not lines:
        return None, None
    first = lines[0]
    if first.startswith(MANIFEST_MAGIC):
        payload = "\n".join(lines[1:])
        return "manifest", json.loads(payload)
    if first.startswith(CHUNK_MAGIC):
        payload = _try_b64("".join(lines[1:]))
        if payload is None:
            return "corrupt", None      # 带头但正文解不开（多半被截断）
        return "chunk", {"header": first, "sha256": sha256_bytes(payload), "payload": payload}
    # 没识别出头：可能是粘贴时丢了第一行，按裸 base64 试
    b64 = "".join(lines)
    if b64 and all(c in
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for c in b64):
        payload = _try_b64(b64)
        if payload is not None:
            return "chunk?", {"header": None, "sha256": sha256_bytes(payload), "payload": payload}
    return "unknown", None


def collect(indir):
    manifest = None
    payloads = {}      # sha -> payload（按内容去重）
    corrupt = []
    unknown = []
    for fn in sorted(os.listdir(indir)):
        if not fn.lower().endswith(".txt"):
            continue
        kind, data = parse_txt(os.path.join(indir, fn))
        if kind == "manifest":
            manifest = data
        elif kind in ("chunk", "chunk?"):
            payloads[data["sha256"]] = data["payload"]
        elif kind == "corrupt":
            corrupt.append(fn)
        elif kind == "unknown":
            unknown.append(fn)
    return manifest, payloads, corrupt, unknown


def safe_extract(tf, dest):
    dest = os.path.abspath(dest)
    for m in tf.getmembers():
        name = os.path.abspath(os.path.join(dest, m.name))
        if not (name == dest or name.startswith(dest + os.sep)):
            raise RuntimeError("可疑路径，拒绝解压: " + m.name)
    tf.extractall(dest)


def cmd_unpack(args):
    manifest, payloads, corrupt, unknown = collect(args.indir)
    if unknown:
        print("警告: 这些文件无法解析（若是误粘贴的其它文本可忽略）: %s" % ", ".join(unknown))
    if corrupt:
        print("以下文件内容损坏（多半是复制时被截断），请整份重拷对应块: %s" % ", ".join(corrupt))
    if manifest is None:
        sys.exit("缺 manifest（000_manifest.txt）。没有它无法校验与拼装，请把 manifest 也复制出来。")

    need = {c["sha256"] for c in manifest["chunks"]}
    missing = [c for c in manifest["chunks"] if c["sha256"] not in payloads]
    if missing:
        print("校验失败：以下 %d 个块缺失或损坏，只需【重拷这些块】（按 id 对应文件名）:" % len(missing))
        for c in missing:
            print("  - 块 %d/%d  (sha256=%s...)" % (c["id"], len(manifest["chunks"]), c["sha256"][:12]))
        bad_extra = [s for s in payloads if s not in need]
        if bad_extra:
            print("另有 %d 个粘贴内容与 manifest 不匹配（内容对不上，请整份重拷）。" % len(bad_extra))
        sys.exit(1)

    payload = b"".join(payloads[c["sha256"]] for c in sorted(manifest["chunks"], key=lambda x: x["id"]))
    if sha256_bytes(payload) != manifest["total_sha256"]:
        sys.exit("总体校验失败：块都对但拼装结果不符，请全部重拷一次。")
    print("校验通过: %d 块, %.2f MB, 模式=%s" %
          (len(manifest["chunks"]), len(payload) / 1048576, manifest["mode"]))

    dest = os.path.abspath(args.dest)
    with tempfile.TemporaryDirectory() as td:
        tar_path = os.path.join(td, "payload.tar")
        with open(tar_path, "wb") as f:
            f.write(decompress_payload(payload))
        with tarfile.open(tar_path, "r:") as tf:
            if manifest["mode"] == "full":
                if os.path.isdir(dest) and os.listdir(dest) and not args.force:
                    sys.exit("目标目录非空: %s（确认覆盖请加 --force）" % dest)
                os.makedirs(dest, exist_ok=True)
                safe_extract(tf, dest)
                print("已解出快照到 %s（含 %d 个文件）。git_head=%s dirty=%s" %
                      (dest, manifest.get("files", "?"), manifest.get("git_head", "?"),
                       manifest.get("git_dirty", "?")))
                print("下一步(外网): 在该目录 git init && git add -A && git commit 建为桥接分支基线。")
            else:
                extract_dir = os.path.join(td, "x")
                os.makedirs(extract_dir)
                safe_extract(tf, extract_dir)
                patch = os.path.join(extract_dir, "patch.diff")
                untracked_dir = os.path.join(extract_dir, "untracked")
                patch_text = open(patch, encoding="utf-8", errors="replace").read().strip()
                if patch_text:
                    r = git(dest, "apply", "--binary", "--whitespace=nowarn", patch, check=False)
                    if r.returncode != 0:
                        print("git apply 失败:\n" + r.stderr[:2000])
                        sys.exit("请确认 dest 是【上次同步点】的桥接分支工作区。\n"
                                 "若上一轮补丁其实已应用成功过，说明本轮是重发——回内网执行 "
                                 "netsync.py ok 后重新打包即可。\n"
                                 "实在不行让对方改发 --full 全量。")
                else:
                    print("本轮无文本改动（只有新文件）。")
                n = 0
                if os.path.isdir(untracked_dir):
                    for dirpath, _, files in os.walk(untracked_dir):
                        for fn in files:
                            srcf = os.path.join(dirpath, fn)
                            rel = os.path.relpath(srcf, untracked_dir)
                            to = os.path.join(dest, rel)
                            os.makedirs(os.path.dirname(to), exist_ok=True)
                            shutil.copy2(srcf, to)
                            n += 1
                print("已应用（basis=%s），复制 %d 个新文件。" % (manifest.get("basis", "?")[:12], n))
                print("下一步: ① 外网 git add -A && git commit 记录本次同步；"
                      "② 回内网执行 netsync.py ok 确认基线。")


def main():
    p = argparse.ArgumentParser(description="内外网代码同步打包/解包工具")
    sub = p.add_subparsers(dest="cmd", required=True)

    pk = sub.add_parser("pack", help="内网侧：打包生成待粘贴的块文件")
    pk.add_argument("--src", default=".", help="代码目录（默认当前目录）")
    pk.add_argument("--out", default="out_sync", help="块文件输出目录")
    pk.add_argument("--full", dest="mode", action="store_const", const="full", help="强制全量快照")
    pk.add_argument("--since", help="增量的起点 commit（默认自动记录）")
    pk.add_argument("--allow-dirty", action="store_true", help="允许带未提交改动做增量（不推荐）")
    pk.add_argument("--include-env", action="store_true", help="包含 .env 文件（默认排除）")
    pk.add_argument("--add-exclude", default="", help="额外排除：目录/文件名或扩展名，逗号分隔，如 junkDir,.pdf")
    pk.add_argument("--chunk-kb", type=int, default=DEFAULT_CHUNK_KB,
                    help="每个块文件的文本大小上限KB（默认 %d）。手机复制卡顿就调小，"
                         "嫌复制次数多就调大" % DEFAULT_CHUNK_KB)
    pk.add_argument("--max-file-mb", type=float, default=MAX_FILE_MB,
                    help="单文件体积上限MB，超过则跳过（0=不限制，默认 %.0f）" % MAX_FILE_MB)
    pk.add_argument("--yes", action="store_true", help="产物超过预算时仍强制打包")
    pk.add_argument("--quiet", action="store_true", help="少打印跳过明细")
    pk.set_defaults(func=cmd_pack)

    an = sub.add_parser("analyze", help="内网侧：只分析将打包什么，不生成文件")
    an.add_argument("--src", default=".", help="代码目录（默认当前目录）")
    an.add_argument("--include-env", action="store_true")
    an.add_argument("--add-exclude", default="")
    an.add_argument("--max-file-mb", type=float, default=MAX_FILE_MB)
    an.set_defaults(func=cmd_analyze)

    up = sub.add_parser("unpack", help="外网侧：校验并拼装/解压/应用")
    up.add_argument("--indir", required=True, help="存放粘贴出来的 txt 的文件夹")
    up.add_argument("--dest", required=True, help="全量=解压目标目录；增量=git 仓库根")
    up.add_argument("--force", action="store_true", help="目标目录非空仍解压")
    up.set_defaults(func=cmd_unpack)

    ok = sub.add_parser("ok", help="内网侧：外网应用成功后确认，推进增量基线")
    ok.add_argument("--src", default=".", help="代码目录（默认当前目录）")
    ok.set_defaults(func=cmd_ok)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
