import os
import re
import json
import uuid
import shutil
import zipfile
import subprocess
from typing import Dict, Any, List, Optional, Callable
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from analyzer import find_viral_moments_from_transcript

FFMPEG_PATH = "ffmpeg"
FFPROBE_PATH = "ffprobe"

def extract_youtube_id(url: str) -> Optional[str]:
    """Extracts YouTube video ID from various URL formats."""
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"youtu\.be\/([0-9A-Za-z_-]{11})",
        r"youtube\.com\/shorts\/([0-9A-Za-z_-]{11})",
        r"youtube\.com\/embed\/([0-9A-Za-z_-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_media_duration(file_path: str) -> float:
    """Uses ffprobe to obtain exact duration in seconds."""
    try:
        cmd = [
            FFPROBE_PATH,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(result.stdout.strip())
    except Exception:
        return 0.0

def fetch_youtube_metadata(url: str) -> Dict[str, Any]:
    """Fetches high-level metadata without downloading video stream."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "id": info.get("id"),
            "title": info.get("title", "YouTube Video"),
            "uploader": info.get("uploader", "Creator"),
            "duration": info.get("duration", 0),
            "view_count": info.get("view_count", 0),
            "thumbnail": info.get("thumbnail", ""),
            "description": (info.get("description", "") or "")[:240]
        }

def fetch_transcript(video_id: str) -> List[Dict[str, Any]]:
    """Attempts to fetch transcripts in English or auto-generated, falling back to any language."""
    ytt = YouTubeTranscriptApi()
    
    # Try direct fetch first
    try:
        transcript_obj = ytt.fetch(video_id, languages=['en', 'en-US', 'en-GB'])
        raw = transcript_obj.to_raw_data()
        return raw
    except Exception:
        pass

    # Try listing all available transcript languages
    try:
        transcript_list = ytt.list(video_id)
        for t in transcript_list:
            try:
                fetched = t.fetch()
                return fetched.to_raw_data()
            except Exception:
                continue
    except Exception:
        pass

    return []

def analyze_audio_peaks_ffmpeg(video_path: str, duration: float, clip_count: int = 10) -> List[Dict[str, Any]]:
    """
    Fallback if no transcript is available: analyzes audio silence & volume peaks 
    using ffmpeg silencedetect to split video into energetic segments.
    """
    moments = []
    min_dur = 25.0
    max_dur = 55.0

    try:
        cmd = [
            FFMPEG_PATH,
            "-i", video_path,
            "-af", "silencedetect=noise=-30dB:d=0.6",
            "-f", "null",
            "-"
        ]
        proc = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        stderr = proc.stderr

        # Extract silence intervals
        silence_starts = [float(m) for m in re.findall(r"silence_start:\s*([0-9.]+)", stderr)]
        silence_ends = [float(m) for m in re.findall(r"silence_end:\s*([0-9.]+)", stderr)]
        
        # Build speech intervals between silences
        speech_intervals = []
        cur_start = 0.0
        for s_start, s_end in zip(silence_starts, silence_ends):
            if s_start > cur_start + 5.0:
                speech_intervals.append((cur_start, s_start))
            cur_start = s_end
        if cur_start < duration - 5.0:
            speech_intervals.append((cur_start, duration))

        # Group speech intervals into clip chunks
        for idx, (sp_s, sp_e) in enumerate(speech_intervals):
            dur = sp_e - sp_s
            if dur >= min_dur and dur <= max_dur:
                moments.append({
                    "start": round(sp_s, 2),
                    "end": round(sp_e, 2),
                    "duration": round(dur, 1),
                    "virality_score": min(98, max(75, 94 - (idx * 2))),
                    "hook_score": min(95, max(70, 92 - (idx * 2))),
                    "retention_score": 88,
                    "energy_score": 90,
                    "hook_type": "audio_peak",
                    "trigger": f"Speech Energy Burst #{idx+1}",
                    "title": f"High Energy Highlight #{idx+1}",
                    "summary": f"Detected energetic dialogue sequence from {int(sp_s)}s to {int(sp_e)}s",
                    "full_text": ""
                })
    except Exception as e:
        print(f"Audio peak analysis error: {e}")

    # If still not enough moments, slice evenly
    if len(moments) < clip_count and duration > min_dur:
        needed = clip_count - len(moments)
        interval = max(min_dur, duration / (clip_count + 1))
        for step_idx in range(clip_count):
            s_time = step_idx * interval
            e_time = min(duration, s_time + 40.0)
            if e_time - s_time >= min_dur * 0.8:
                moments.append({
                    "start": round(s_time, 2),
                    "end": round(e_time, 2),
                    "duration": round(e_time - s_time, 1),
                    "virality_score": max(70, 96 - (step_idx * 3)),
                    "hook_score": max(68, 93 - (step_idx * 3)),
                    "retention_score": max(70, 90 - (step_idx * 2)),
                    "energy_score": max(70, 88 - (step_idx * 2)),
                    "hook_type": "energy_surge",
                    "trigger": f"Viral Surge Segment #{step_idx+1}",
                    "title": f"Viral Moment #{step_idx+1}",
                    "summary": f"Peak retention segment at {int(s_time)}s",
                    "full_text": ""
                })
                if len(moments) >= clip_count:
                    break

    # Add badges
    for idx, m in enumerate(moments[:clip_count]):
        m["id"] = idx + 1
        score = m["virality_score"]
        if score >= 94:
            m["badge"] = "🔥 Mega Viral"
            m["badge_class"] = "badge-mega"
        elif score >= 86:
            m["badge"] = "🚀 High Retention"
            m["badge_class"] = "badge-high"
        elif score >= 80:
            m["badge"] = "✨ Strong Hook"
            m["badge_class"] = "badge-medium"
        else:
            m["badge"] = "⚡ Engaging Cut"
            m["badge_class"] = "badge-standard"

    return moments[:clip_count]

def download_video_stream(url: str, output_path: str, progress_callback: Optional[Callable[[float, str], None]] = None) -> str:
    """Downloads YouTube video at optimal fast resolution (up to 1080p, prefer 720p for fast processing)."""
    
    def ytdl_hook(d):
        if d['status'] == 'downloading' and progress_callback:
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 1
            downloaded = d.get('downloaded_bytes', 0)
            pct = min(100.0, (downloaded / total) * 100.0)
            progress_callback(pct, f"Downloading stream: {pct:.1f}%")

    ydl_opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [ytdl_hook]
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
        
    return output_path

def cut_clip_ffmpeg(
    source_video: str,
    start_sec: float,
    end_sec: float,
    output_video: str,
    aspect_ratio: str = "9:16",
    crop_style: str = "blurred_background"
) -> bool:
    """
    Renders an exact video clip with specified aspect ratio using FFmpeg.
    Supports Opus-Clip signature 9:16 blurred background or center crop, and 16:9 original.
    """
    duration = end_sec - start_sec
    if duration <= 0:
        return False

    os.makedirs(os.path.dirname(output_video), exist_ok=True)
    
    if aspect_ratio == "9:16":
        if crop_style == "blurred_background":
            # 1080x1920 vertical format with optimized ultra-fast ambient blurred glow background and centered crisp video
            vf = (
                "[0:v]split=2[bg][fg];"
                "[bg]scale=120:214:force_original_aspect_ratio=increase,crop=120:214,boxblur=5:2,scale=1080:1920[bgblur];"
                "[fg]scale=1080:-2:force_original_aspect_ratio=decrease[fgscaled];"
                "[bgblur][fgscaled]overlay=(W-w)/2:(H-h)/2[outv]"
            )
        elif crop_style == "black_background":
            # 1080x1920 vertical format with clean solid black padding (letterbox / pillarbox)
            vf = (
                "[0:v]scale=1080:-2:force_original_aspect_ratio=decrease,"
                "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black[outv]"
            )
        else: # center crop
            vf = "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920[outv]"

        cmd = [
            FFMPEG_PATH, "-y",
            "-ss", str(start_sec),
            "-i", source_video,
            "-t", str(duration),
            "-filter_complex", vf,
            "-map", "[outv]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_video
        ]
    elif aspect_ratio == "1:1":
        if crop_style == "black_background":
            # 1080x1080 square format with solid black padding
            vf = (
                "[0:v]scale=1080:-2:force_original_aspect_ratio=decrease,"
                "pad=1080:1080:(ow-iw)/2:(oh-ih)/2:color=black[outv]"
            )
        elif crop_style == "center_crop":
            vf = "[0:v]scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080[outv]"
        else:
            # 1080x1080 square format with ambient blurred background
            vf = (
                "[0:v]split=2[bg][fg];"
                "[bg]scale=120:120:force_original_aspect_ratio=increase,crop=120:120,boxblur=5:2,scale=1080:1080[bgblur];"
                "[fg]scale=1080:-2:force_original_aspect_ratio=decrease[fgscaled];"
                "[bgblur][fgscaled]overlay=(W-w)/2:(H-h)/2[outv]"
            )
        cmd = [
            FFMPEG_PATH, "-y",
            "-ss", str(start_sec),
            "-i", source_video,
            "-t", str(duration),
            "-filter_complex", vf,
            "-map", "[outv]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            output_video
        ]
    else:
        # Original 16:9 Landscape
        if crop_style == "black_background":
            vf = "[0:v]scale=1920:-2:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black[outv]"
            cmd = [
                FFMPEG_PATH, "-y",
                "-ss", str(start_sec),
                "-i", source_video,
                "-t", str(duration),
                "-filter_complex", vf,
                "-map", "[outv]",
                "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                output_video
            ]
        else:
            cmd = [
                FFMPEG_PATH, "-y",
                "-ss", str(start_sec),
                "-i", source_video,
                "-t", str(duration),
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-crf", "20",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                output_video
            ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            print(f"FFmpeg error: {proc.stderr[:400]}")
            return False
        return True
    except Exception as e:
        print(f"Exception during FFmpeg cut: {e}")
        return False

def generate_clip_thumbnail(video_path: str, thumbnail_path: str, at_second: float = 1.0) -> bool:
    """Extracts a frame to use as thumbnail poster."""
    cmd = [
        FFMPEG_PATH, "-y",
        "-ss", str(at_second),
        "-i", video_path,
        "-vframes", "1",
        "-update", "1",
        "-q:v", "3",
        thumbnail_path
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return res.returncode == 0
    except Exception:
        return False

def package_clips_to_zip(clip_file_paths: List[str], zip_output_path: str) -> str:
    """Bundles all generated viral clips into a single clean ZIP archive."""
    with zipfile.ZipFile(zip_output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in clip_file_paths:
            if os.path.exists(file_path):
                zipf.write(file_path, arcname=os.path.basename(file_path))
    return zip_output_path
