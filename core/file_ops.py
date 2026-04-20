import os
import json
from datetime import datetime
from send2trash import send2trash


def delete_to_trash(file_paths: list) -> dict:
    """移入回收站"""
    success = []
    failed = []

    for path in file_paths:
        try:
            if not os.path.exists(path):
                failed.append({"path": path, "error": "文件不存在"})
                continue
            send2trash(path)
            success.append(path)
        except Exception as e:
            failed.append({"path": path, "error": str(e)})

    return {
        "success": success,
        "failed": failed,
        "success_count": len(success),
        "fail_count": len(failed),
    }


def delete_permanently(file_paths: list) -> dict:
    """永久删除文件"""
    success = []
    failed = []

    for path in file_paths:
        try:
            if not os.path.exists(path):
                failed.append({"path": path, "error": "文件不存在"})
                continue
            if os.path.isfile(path):
                os.remove(path)
                success.append(path)
            elif os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
                success.append(path)
        except PermissionError:
            failed.append({"path": path, "error": "权限不足，无法删除"})
        except Exception as e:
            failed.append({"path": path, "error": str(e)})

    return {
        "success": success,
        "failed": failed,
        "success_count": len(success),
        "fail_count": len(failed),
    }


def preview_file(file_path: str) -> dict:
    """
    预览文件内容
    返回：文本内容 / base64图片 / 视频 / 元信息
    """
    from pathlib import Path
    import base64
    from .rules import (
        TEXT_PREVIEW_EXTENSIONS,
        IMAGE_PREVIEW_EXTENSIONS,
        VIDEO_PREVIEW_EXTENSIONS,
        MAX_PREVIEW_SIZE,
        MAX_IMAGE_PREVIEW_SIZE,
    )

    if not os.path.exists(file_path):
        return {"type": "error", "content": "文件不存在"}

    ext = Path(file_path).suffix.lower()
    size = os.path.getsize(file_path)

    # ── 视频预览 ──
    if ext in VIDEO_PREVIEW_EXTENSIONS:
        mime_map = {
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".ogg": "video/ogg",
            ".mov": "video/quicktime",
            ".avi": "video/x-msvideo",
            ".mkv": "video/x-matroska",
        }
        mime = mime_map.get(ext, "video/mp4")
        return {"type": "video", "path": file_path, "mime": mime, "size": size}

    # ── 图片预览 ──
    if ext in IMAGE_PREVIEW_EXTENSIONS:
        if size > MAX_IMAGE_PREVIEW_SIZE:
            return {
                "type": "info",
                "content": f"图片过大（{_human_size(size)}），无法预览",
            }
        try:
            with open(file_path, "rb") as f:
                data = f.read()
            b64 = base64.b64encode(data).decode("utf-8")
            mime_map = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".gif": "image/gif",
                ".bmp": "image/bmp", ".webp": "image/webp",
                ".ico": "image/x-icon",
            }
            mime = mime_map.get(ext, "image/jpeg")
            return {"type": "image", "content": b64, "mime": mime}
        except Exception as e:
            return {"type": "error", "content": f"图片读取失败: {e}"}

    # ── 文本预览 ──
    if ext in TEXT_PREVIEW_EXTENSIONS or _is_text_file(file_path):
        if size > MAX_PREVIEW_SIZE:
            truncated = True
            read_size = MAX_PREVIEW_SIZE
        else:
            truncated = False
            read_size = size

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(read_size)
            return {
                "type": "text",
                "content": content,
                "truncated": truncated,
                "size": size,
            }
        except Exception as e:
            return {"type": "error", "content": f"文件读取失败: {e}"}

    # ── 其他文件：显示元信息 ──
    try:
        stat = os.stat(file_path)
        return {
            "type": "info",
            "content": (
                f"文件名：{os.path.basename(file_path)}\n"
                f"路径：{file_path}\n"
                f"大小：{_human_size(size)}\n"
                f"修改时间：{datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"创建时间：{datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"类型：{ext or '未知'}"
            ),
        }
    except Exception as e:
        return {"type": "error", "content": str(e)}


def export_list(results: list, export_path: str = None) -> str:
    """导出文件清单为 CSV"""
    import csv
    import tempfile

    if not export_path:
        export_path = os.path.join(
            tempfile.gettempdir(),
            f"file_cleaner_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )

    with open(export_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "文件名", "路径", "分类", "风险等级",
                "文件大小", "修改时间", "匹配原因"
            ],
        )
        writer.writeheader()
        for r in results:
            writer.writerow({
                "文件名": r.get("name", ""),
                "路径": r.get("path", ""),
                "分类": r.get("category_label", ""),
                "风险等级": r.get("risk", ""),
                "文件大小": r.get("size_human", ""),
                "修改时间": r.get("mtime", ""),
                "匹配原因": ", ".join(r.get("match_reason", [])),
            })

    return export_path


def _is_text_file(file_path: str, sample_size: int = 8192) -> bool:
    """简单判断是否为文本文件"""
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(sample_size)
        # 包含null字节则认为是二进制
        return b"\x00" not in chunk
    except Exception:
        return False


def _human_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"