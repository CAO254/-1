# [工单21] 人工智能NLP-Agent数字人项目-教育智能体-虚拟教室/讲课页 —— 内置轻量成课管线（纯 CPU）
"""降级成课管线：课件页画面 + Edge-TTS 教师配音 + 头像小窗 → 讲课视频。

设计背景
========
工单21 的主链路依赖**外部 Wav2Lip 离线管线**（``C:/Users/.../wav2lip/gen_lecture.py``
+ 约 400MB 模型权重），权重不入仓库、且无独显机器基本跑不动。为了让「成课」在没有
Wav2Lip 的机器上依然可用，本模块提供一条纯 CPU 降级管线：

1. 每段讲稿按句切块 → Edge-TTS 逐块合成 MP3 → ffmpeg 无损拼接成段音频；
2. Pillow 把每页课件（标题 + 正文）渲染成 1280×720 帧，右下角贴圆形教师头像小窗；
3. ffmpeg 把「静态帧 + 段音频」编码成段视频（H.264 / AAC / yuv420p）；
4. concat 各段得到整课 ``video.mp4``；
5. 解析各段实际时长，写 ``timeline.json``（前端按它翻课件页 + 同步字幕）与
   ``course.json``。

产物结构与外部 Wav2Lip 管线**完全同构**，前端虚拟教室页（Room.vue）无需任何改动：

    out_dir/
      video.mp4       整课视频
      course.json     {courseId,title,subject,pages:[{title,body,note}]}
      timeline.json   [{idx,start,end,page,text}]

注意：降级管线没有口型同步（照片是静态小窗），只做「翻课件 + 配音 + 字幕联动」；
若检测到外部 Wav2Lip 管线存在，app/api/lecture.py 会优先走外部管线。
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import subprocess
from pathlib import Path
from typing import Callable

from app.config import settings

logger = logging.getLogger(__name__)

# 进度回调：on_progress(done, total, message)。done==total 且 message=="CONCAT" 时进入拼接
ProgressCb = Callable[[int, int, str], None]

# ------------------------------------------------------------ 视频规格
WIDTH, HEIGHT = 1280, 720
FPS = 25
# 单块送 TTS 的字符上限：Edge-TTS 对长文本也能合成，但切块更稳（失败可定位到句），
# 且与 .env 的 TTS_MAX_CHARS（问答实时朗读用 300）区分开——成课不是实时链路，取宽一些
_TTS_BLOCK_CHARS = 240

# 课件正文按句读切分（同时兼容中英文标点）
_SENT_SPLIT_RE = re.compile(r"(?<=[。！？!?；;\n])")
# 正文里需要去掉/规整的 Markdown 行内标记（课件页是给视频帧用的纯文本）
_MD_LINE_RE = re.compile(r"^\s{0,3}#{1,6}\s*|^\s*[-*+]\s+|^\s*\d+[.、)]\s+")
_MD_INLINE_RE = re.compile(r"\*\*|__|`|!\[[^\]]*\]\([^)]*\)|\[([^\]]*)\]\([^)]*\)|\\(.)")
_MD_MATH_RE = re.compile(r"\${1,2}[^$]+\${1,2}")

# Windows 自带中文字体（微软雅黑），缺失时回退黑体
_FONT_CANDIDATES = (
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
)

# 配色（与前端浅色主题一致：紫主色 + 深色文字 + 浅灰背景）
_COLOR_BG = (245, 247, 250)
_COLOR_TITLE = (31, 41, 55)
_COLOR_BODY = (55, 65, 81)
_COLOR_ACCENT = (155, 81, 224)
_COLOR_MUTED = (156, 163, 175)


class LecturePipelineError(RuntimeError):
    """内置成课管线失败（TTS/ffmpeg/渲染任一环节），错误信息直达任务状态。"""


# ================================================================ ffmpeg
def _ffmpeg_exe() -> str:
    """imageio-ffmpeg 自带的静态 ffmpeg 二进制（pip 安装，约 30MB，不依赖系统 PATH）。"""
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # noqa: BLE001
        raise LecturePipelineError(
            "未找到 ffmpeg。请在后端虚拟环境执行：pip install imageio-ffmpeg"
        ) from exc


def _run_ffmpeg(args: list[str], *, cwd: Path) -> None:
    """跑 ffmpeg，失败时把 stderr 尾部带进异常（ffmpeg 诊断信息全在 stderr）。"""
    cmd = [_ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-y", *args]
    proc = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="ignore"
    )
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip().splitlines()[-15:]
        raise LecturePipelineError(
            f"ffmpeg 退出码 {proc.returncode}：\n" + "\n".join(tail)
        )


_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def _probe_duration(path: Path, *, cwd: Path) -> float:
    """用 ffmpeg -i 解析媒体时长（秒）。error 级日志时没有 Duration 输出，故用 info 级。"""
    cmd = [_ffmpeg_exe(), "-hide_banner", "-i", str(path)]
    proc = subprocess.run(
        cmd, cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="ignore"
    )
    m = _DURATION_RE.search(proc.stderr or "")
    if not m:
        raise LecturePipelineError(f"无法解析媒体时长：{path.name}")
    h, mm, ss = m.groups()
    return int(h) * 3600 + int(mm) * 60 + float(ss)


# ================================================================ TTS
def _split_for_tts(text: str) -> list[str]:
    """长讲稿按句读切成不超过 _TTS_BLOCK_CHARS 的块；超长无标点句硬切。"""
    sentences = [s.strip() for s in _SENT_SPLIT_RE.split(text) if s.strip()]
    blocks: list[str] = []
    buf = ""
    for sent in sentences:
        if len(sent) > _TTS_BLOCK_CHARS:
            if buf:
                blocks.append(buf)
                buf = ""
            for i in range(0, len(sent), _TTS_BLOCK_CHARS):
                blocks.append(sent[i : i + _TTS_BLOCK_CHARS])
            continue
        if len(buf) + len(sent) <= _TTS_BLOCK_CHARS:
            buf += sent
        else:
            if buf:
                blocks.append(buf)
            buf = sent
    if buf:
        blocks.append(buf)
    return blocks


async def _edge_synthesize_one(text: str) -> bytes:
    """单块文本 → MP3 字节。参数与 services/tts.py 的 edge 分支保持一致。

    Edge-TTS 是免费在线服务，**偶发断流/空音频很常见**（尤其一段课程要串行合成
    十几个分块，单块失败概率会叠加）。这里对「网络异常 / 超时 / 空音频」做 3 次
    重试，指数退避；3 次都失败才抛错，错误信息保留真实异常类型，便于区分网络问题
    与配置问题。
    """
    try:
        import edge_tts
    except ImportError as exc:
        raise LecturePipelineError(
            "未安装 edge-tts。请在后端虚拟环境执行：pip install edge-tts"
        ) from exc

    timeout = int(settings.TTS_TIMEOUT_SECONDS)
    last_exc: Exception | None = None

    for attempt in range(1, 4):
        try:
            communicate = edge_tts.Communicate(
                text,
                settings.TTS_VOICE,
                rate=settings.TTS_RATE,
                volume=settings.TTS_VOLUME,
                connect_timeout=10,
                receive_timeout=timeout,
                proxy=settings.TTS_PROXY or None,
            )
            buffer = bytearray()
            async with asyncio.timeout(timeout + 10):
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        buffer.extend(chunk["data"])
            if buffer:
                if attempt > 1:
                    logger.info("TTS 第 %d 次尝试成功（%d 字节）", attempt, len(buffer))
                return bytes(buffer)
            # 空音频：edge-tts 偶发只回元事件不给音频，按瞬时故障重试
            last_exc = RuntimeError("edge-tts 返回空音频")
            logger.warning("TTS 第 %d 次返回空音频，准备重试", attempt)
        except TimeoutError as exc:
            last_exc = exc
            logger.warning("TTS 第 %d 次超时：%s", attempt, exc)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning("TTS 第 %d 次失败：%s: %s", attempt, type(exc).__name__, exc)

        if attempt < 3:
            await asyncio.sleep(attempt * 2)  # 2s、4s 退避

    raise LecturePipelineError(
        f"语音合成连续 3 次失败（最后错误：{type(last_exc).__name__}: {last_exc}）。"
        "Edge-TTS 需要联网，请检查网络连接后重试；如长期失败可在 .env 配置 TTS_PROXY。"
    ) from last_exc


def _synthesize_segment_audio(text: str, out_mp3: Path, *, work_dir: Path) -> None:
    """整段讲稿 → 切块逐块合成 → ffmpeg 无损拼接为段音频 seg.mp3。

    MP3 帧直接 stream copy 拼接对 ffmpeg 是安全的（统一在后面转 AAC）；
    不走 services.tts.synthesize 是因为它带 TTS_MAX_CHARS=300 的实时朗读截断，
    成课讲稿一段可达上千字，不能截断。
    """
    blocks = _split_for_tts(text)
    if not blocks:
        raise LecturePipelineError("讲稿段落没有可朗读的文本。")

    async def _all() -> list[bytes]:
        return [await _edge_synthesize_one(b) for b in blocks]

    chunks = asyncio.run(_all())

    chunk_dir = work_dir / "tts_chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    list_lines: list[str] = []
    for i, audio in enumerate(chunks):
        p = chunk_dir / f"chunk_{i:03d}.mp3"
        p.write_bytes(audio)
        # concat 清单用相对路径，整个管线以 out_dir 为 cwd，规避中文路径/盘符转义问题
        list_lines.append(f"file '{p.relative_to(work_dir).as_posix()}'")
    concat_list = work_dir / f"_tts_concat_{out_mp3.stem}.txt"
    concat_list.write_text("\n".join(list_lines), encoding="utf-8")

    _run_ffmpeg(
        ["-f", "concat", "-safe", "0", "-i", concat_list.name, "-c", "copy", out_mp3.name],
        cwd=work_dir,
    )


# ================================================================ 课件帧渲染
def _clean_body(raw: str) -> list[str]:
    """课件 body（Markdown）→ 纯文本行：去标题/列表标记、加粗/链接/公式，丢表格分隔行。"""
    lines: list[str] = []
    for raw_line in (raw or "").splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue
        if line.count("|") >= 2 or re.match(r"^[-*_]{3,}$", line):
            continue
        line = _MD_LINE_RE.sub("", line)
        line = _MD_MATH_RE.sub("（公式）", line)
        line = _MD_INLINE_RE.sub(lambda m: m.group(1) or "", line)
        lines.append(line.strip())
    return lines


def _wrap_text(text: str, font, max_width: int, draw) -> list[str]:
    """按像素宽度折行（逐字符累加，中英文混排通用）。"""
    out: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            out.append("")
            continue
        line = ""
        for ch in paragraph:
            candidate = line + ch
            if draw.textlength(candidate, font=font) <= max_width:
                line = candidate
            else:
                if line:
                    out.append(line)
                line = ch
        if line:
            out.append(line)
    return out


def _load_fonts():
    from PIL import ImageFont

    path = next((p for p in _FONT_CANDIDATES if Path(p).exists()), None)
    if path is None:
        raise LecturePipelineError("未找到可用的中文字体（msyh.ttc / simhei.ttf）。")
    return (
        ImageFont.truetype(path, 44),  # 标题
        ImageFont.truetype(path, 27),  # 正文
        ImageFont.truetype(path, 20),  # 页脚/页码
    )


def _paste_avatar(canvas, avatar_path: Path) -> None:
    """右下角圆形教师头像小窗（白底 + 紫色描边）；素材缺失则静默跳过。"""
    if not avatar_path or not avatar_path.exists():
        return
    try:
        from PIL import Image, ImageDraw

        size = 188
        photo = Image.open(avatar_path).convert("RGB")
        # 居中正方形裁剪
        w, h = photo.size
        side = min(w, h)
        photo = photo.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
        photo = photo.resize((size, size), Image.LANCZOS)

        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)

        x, y = WIDTH - size - 56, HEIGHT - size - 56
        # 白色圆底 + 紫色描边环
        ring = Image.new("RGBA", (size + 16, size + 16), (0, 0, 0, 0))
        rd = ImageDraw.Draw(ring)
        rd.ellipse((0, 0, size + 15, size + 15), fill=(255, 255, 255, 255))
        rd.ellipse((0, 0, size + 15, size + 15), outline=_COLOR_ACCENT + (255,), width=4)
        canvas.alpha_composite(ring, (x - 8, y - 8))
        canvas.paste(photo, (x, y), mask)
    except Exception as exc:  # noqa: BLE001 - 头像只是装饰，失败不阻断成课
        logger.warning("教师头像渲染失败，已跳过：%s", exc)


def _render_page_png(page: dict, avatar_path: Path, idx: int, total: int, subject: str,
                     out_png: Path) -> None:
    """渲染单页课件为 1280×720 PNG。"""
    from PIL import Image, ImageDraw

    title_font, body_font, small_font = _load_fonts()
    canvas = Image.new("RGBA", (WIDTH, HEIGHT), _COLOR_BG + (255,))
    draw = ImageDraw.Draw(canvas)

    # 顶部紫色装饰条
    draw.rectangle((0, 0, WIDTH, 8), fill=_COLOR_ACCENT)

    # 标题（超长折两行）
    title_lines = _wrap_text(page.get("title", "")[:80], title_font, 1140, draw)[:2]
    y = 56
    for line in title_lines:
        draw.text((70, y), line, font=title_font, fill=_COLOR_TITLE)
        y += 62
    # 标题下紫色短横
    draw.rectangle((72, y + 6, 150, y + 10), fill=_COLOR_ACCENT)
    y += 40

    # 正文（给右下角头像预留：底部与右下不压字）
    body_text = "\n".join(_clean_body(page.get("body", "")))
    body_lines = _wrap_text(body_text, body_font, 1140, draw)
    max_body_lines = 15
    for i, line in enumerate(body_lines[:max_body_lines]):
        draw.text((72, y + i * 44), line or " ", font=body_font,
                  fill=_COLOR_BODY if line else _COLOR_BODY)
    if len(body_lines) > max_body_lines:
        draw.text((72, y + max_body_lines * 44), "……", font=body_font, fill=_COLOR_MUTED)

    # 左下角页码
    draw.text((70, HEIGHT - 58), f"{idx} / {total}", font=small_font, fill=_COLOR_MUTED)
    # 左下角课程/学科（避免和页码同行，放页码上方小字）
    if subject:
        sub = subject[:24]
        draw.text((150, HEIGHT - 58), sub, font=small_font, fill=_COLOR_MUTED)

    _paste_avatar(canvas, avatar_path)

    canvas.convert("RGB").save(out_png, "PNG")


# ================================================================ 主入口
def run_pipeline(spec_path: Path, out_dir: Path,
                 on_progress: ProgressCb | None = None) -> None:
    """读 spec.json 跑完内置成课管线，产物落 out_dir。

    任何环节失败都抛 LecturePipelineError，由调用方（api/lecture.py 工作线程）
    落到 job.error，保证任务状态闭环。
    """
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise LecturePipelineError(f"课程配置 spec.json 读取失败：{exc}") from exc

    pages = spec.get("pages") or []
    segments = spec.get("segments") or []
    if not pages or not segments:
        raise LecturePipelineError("课程配置缺少 pages 或 segments，无法成课。")

    avatar_path = Path(spec.get("image") or "")
    work_dir = out_dir / "_work"
    work_dir.mkdir(parents=True, exist_ok=True)
    total = len(segments)

    def emit(done: int, msg: str) -> None:
        if on_progress:
            on_progress(done, total, msg)

    # 1) 各页课件帧（同页多段复用一张图）
    page_pngs: dict[int, Path] = {}
    for i, page in enumerate(pages, start=1):
        png = work_dir / f"page_{i:02d}.png"
        _render_page_png(
            page, avatar_path, i, len(pages),
            str(spec.get("subject") or ""), png,
        )
        page_pngs[i] = png

    # 2) 逐段：TTS 配音 → 段视频
    seg_videos: list[Path] = []
    for i, seg in enumerate(segments, start=1):
        page_no = int(seg.get("page", 1))
        png = page_pngs.get(page_no) or next(iter(page_pngs.values()))
        mp3 = work_dir / f"seg_{i:02d}.mp3"
        mp4 = work_dir / f"seg_{i:02d}.mp4"

        emit(i - 1, f"第 {i}/{total} 段：合成配音")
        _synthesize_segment_audio(str(seg.get("text", "")), mp3, work_dir=work_dir)

        emit(i - 1, f"第 {i}/{total} 段：合成画面")
        _run_ffmpeg(
            [
                "-loop", "1", "-framerate", str(FPS), "-i", png.name,
                "-i", mp3.name,
                "-c:v", "libx264", "-tune", "stillimage", "-preset", "veryfast",
                "-vf", f"scale={WIDTH}:{HEIGHT},format=yuv420p",
                "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
                "-shortest", mp4.name,
            ],
            cwd=work_dir,
        )
        seg_videos.append(mp4)
        emit(i, f"已生成 {i}/{total} 段")

    # 3) 拼接整课
    emit(total, "CONCAT")
    concat_txt = work_dir / "video_concat.txt"
    concat_txt.write_text(
        "\n".join(f"file '{v.name}'" for v in seg_videos), encoding="utf-8"
    )
    _run_ffmpeg(
        ["-f", "concat", "-safe", "0", "-i", concat_txt.name,
         "-c", "copy", str(out_dir / "video.mp4")],
        cwd=work_dir,
    )
    if not (out_dir / "video.mp4").exists():
        raise LecturePipelineError("拼接结束但未产出 video.mp4")

    # 4) 各段实际时长 → timeline.json
    timeline: list[dict] = []
    cursor = 0.0
    for i, (seg, mp4) in enumerate(zip(segments, seg_videos)):
        dur = _probe_duration(mp4, cwd=work_dir)
        timeline.append({
            "idx": i,
            "start": round(cursor, 2),
            "end": round(cursor + dur, 2),
            "page": int(seg.get("page", 1)),
            "text": str(seg.get("text", ""))[:500],
        })
        cursor += dur
    (out_dir / "timeline.json").write_text(
        json.dumps(timeline, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # 5) course.json（pages 与 draft 结构对齐；note 留空，前端 v-if 已兼容）
    course = {
        "courseId": spec.get("courseId") or out_dir.name,
        "title": spec.get("title") or "未命名课程",
        "subject": spec.get("subject") or "",
        "pages": [
            {"title": p.get("title", ""), "body": p.get("body", ""), "note": ""}
            for p in pages
        ],
        "engine": "builtin-slides",
    }
    (out_dir / "course.json").write_text(
        json.dumps(course, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    # 6) 清理中间产物（chunk 音频/段视频可达几十 MB，course 列表只需要最终三件套）
    try:
        import shutil

        shutil.rmtree(work_dir, ignore_errors=True)
    except OSError:  # noqa: BLE001
        logger.warning("中间目录清理失败（不影响产物）：%s", work_dir)

    logger.info("内置成课管线完成：%s（%d 段，总时长 %.1f 秒）",
                out_dir.name, total, cursor)
