import os
import json
import uuid
import time
import shutil
import threading
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import video_engine
import analyzer
import rules_engine

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
RULES_DIR = os.path.join(UPLOADS_DIR, "rules")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SAMPLES_DIR = os.path.join(BASE_DIR, "samples")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(RULES_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SAMPLES_DIR, exist_ok=True)

app = FastAPI(title="Opus AutoClipper AI", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory jobs tracking
JOBS: Dict[str, Dict[str, Any]] = {}

class VideoInfoRequest(BaseModel):
    url: Optional[str] = None
    sample_id: Optional[str] = None
    upload_id: Optional[str] = None

class ProcessRequest(BaseModel):
    source_type: str = "youtube" # "youtube", "upload", "sample"
    url: Optional[str] = None
    sample_id: Optional[str] = None
    upload_id: Optional[str] = None
    clip_count: int = 10
    target_duration: str = "auto" # "auto", "short", "medium", "extended"
    aspect_ratio: str = "9:16" # "9:16", "16:9", "1:1"
    crop_style: str = "blurred_background" # "blurred_background", "black_background", "center_crop"
    campaign_rules: Optional[Dict[str, Any]] = None

class RulesParseRequest(BaseModel):
    rules_text: Optional[str] = ""
    keywords: Optional[List[str]] = None
    banned_keywords: Optional[List[str]] = None
    hook_preference: Optional[str] = "any"
    min_compliance: Optional[float] = 65.0

class TrimRequest(BaseModel):
    job_id: str
    clip_id: int
    start: float
    end: float

# Serve output and sample media files
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")
app.mount("/samples", StaticFiles(directory=SAMPLES_DIR), name="samples")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Opus AutoClipper AI Server is running."}

@app.get("/api/samples")
def get_samples():
    samples_json = os.path.join(SAMPLES_DIR, "samples.json")
    if os.path.exists(samples_json):
        with open(samples_json, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@app.post("/api/video-info")
def get_video_info(req: VideoInfoRequest):
    try:
        if req.sample_id:
            samples_json = os.path.join(SAMPLES_DIR, "samples.json")
            if os.path.exists(samples_json):
                with open(samples_json, "r", encoding="utf-8") as f:
                    samples = json.load(f)
                    for s in samples:
                        if s["id"] == req.sample_id:
                            return s
            raise HTTPException(status_code=404, detail="Sample not found")

        if req.upload_id:
            upload_meta_path = os.path.join(UPLOADS_DIR, f"{req.upload_id}.json")
            if os.path.exists(upload_meta_path):
                with open(upload_meta_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            raise HTTPException(status_code=404, detail="Uploaded file not found")

        if req.url:
            yt_id = video_engine.extract_youtube_id(req.url)
            if not yt_id:
                raise HTTPException(status_code=400, detail="Invalid YouTube URL format")
            info = video_engine.fetch_youtube_metadata(req.url)
            return info

        raise HTTPException(status_code=400, detail="No source provided")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    try:
        upload_id = str(uuid.uuid4())
        ext = os.path.splitext(file.filename)[1].lower() or ".mp4"
        saved_filename = f"{upload_id}{ext}"
        saved_path = os.path.join(UPLOADS_DIR, saved_filename)
        
        with open(saved_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
            
        duration = video_engine.get_media_duration(saved_path)
        
        # Generate thumbnail
        thumb_filename = f"{upload_id}.jpg"
        thumb_path = os.path.join(UPLOADS_DIR, thumb_filename)
        video_engine.generate_clip_thumbnail(saved_path, thumb_path, at_second=min(2.0, duration / 2.0))
        
        meta = {
            "id": upload_id,
            "filename": file.filename,
            "title": os.path.splitext(file.filename)[0],
            "uploader": "Uploaded File",
            "duration": int(duration),
            "view_count": 0,
            "thumbnail": f"/uploads/{thumb_filename}",
            "file_path": saved_path
        }
        
        with open(os.path.join(UPLOADS_DIR, f"{upload_id}.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
            
        return meta
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/api/rules/upload-images")
async def upload_rule_images(files: List[UploadFile] = File(...)):
    """
    Accepts one or multiple campaign rule screenshots/images, extracts text via OCR,
    and analyzes the rules for AI-guided video clipping.
    """
    try:
        combined_text_parts = []
        image_records = []
        
        for file in files:
            file_id = str(uuid.uuid4())[:8]
            ext = os.path.splitext(file.filename)[1].lower() or ".jpg"
            saved_name = f"rule_{file_id}{ext}"
            saved_path = os.path.join(RULES_DIR, saved_name)
            
            with open(saved_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
                
            # Perform OCR on image
            extracted_text = rules_engine.ocr_image_file(saved_path)
            if extracted_text:
                combined_text_parts.append(extracted_text)
                
            image_records.append({
                "id": file_id,
                "filename": file.filename,
                "url": f"/uploads/rules/{saved_name}",
                "ocr_text": extracted_text
            })
            
        full_text = "\n\n".join(combined_text_parts)
        parsed_rules = rules_engine.parse_campaign_rules(rules_text=full_text)
        
        return {
            "status": "success",
            "extracted_text": full_text,
            "rules": parsed_rules,
            "images": image_records
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rule image analysis failed: {str(e)}")

@app.post("/api/rules/parse-text")
def parse_rules_text(req: RulesParseRequest):
    """Parses user-edited rules text or parameters into structured clipping guidelines."""
    try:
        parsed = rules_engine.parse_campaign_rules(
            rules_text=req.rules_text or "",
            custom_keywords=req.keywords,
            custom_banned=req.banned_keywords,
            hook_preference=req.hook_preference,
            min_compliance=req.min_compliance or 65.0
        )
        return parsed
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def run_clipping_pipeline(job_id: str, req: ProcessRequest):
    job = JOBS[job_id]
    job_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)
    
    try:
        # Step 1: Ingest source media & resolve transcript
        job["status"] = "processing"
        job["stage"] = "Resolving video source and transcript..."
        job["progress"] = 10
        
        source_video_path = ""
        transcript_data = []
        video_duration = 0.0
        
        if req.source_type == "sample":
            samples_json = os.path.join(SAMPLES_DIR, "samples.json")
            with open(samples_json, "r", encoding="utf-8") as f:
                samples = json.load(f)
            sample_item = next((s for s in samples if s["id"] == req.sample_id), samples[0])
            source_video_path = os.path.join(SAMPLES_DIR, f"{sample_item['id']}.mp4")
            transcript_data = sample_item.get("transcript", [])
            video_duration = sample_item.get("duration", 120.0)
            job["video_title"] = sample_item.get("title", "Sample Video")
            job["thumbnail"] = sample_item.get("thumbnail", "")

        elif req.source_type == "upload":
            upload_meta_path = os.path.join(UPLOADS_DIR, f"{req.upload_id}.json")
            with open(upload_meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            source_video_path = meta["file_path"]
            video_duration = meta.get("duration", 60.0)
            job["video_title"] = meta.get("title", "Uploaded Video")
            job["thumbnail"] = meta.get("thumbnail", "")

        elif req.source_type == "youtube":
            yt_id = video_engine.extract_youtube_id(req.url)
            if not yt_id:
                raise Exception("Invalid YouTube URL")
            
            job["stage"] = "Fetching YouTube metadata and transcript..."
            job["progress"] = 15
            meta = video_engine.fetch_youtube_metadata(req.url)
            job["video_title"] = meta.get("title", "YouTube Video")
            job["thumbnail"] = meta.get("thumbnail", "")
            video_duration = meta.get("duration", 180.0)
            
            # Fetch transcript via youtube_transcript_api
            transcript_data = video_engine.fetch_transcript(yt_id)
            
            # Download video stream
            job["stage"] = "Downloading YouTube video stream for clipping..."
            job["progress"] = 25
            
            download_dest = os.path.join(job_dir, "master_source.mp4")
            def on_download_progress(pct, msg):
                job["progress"] = 25 + int(pct * 0.25)
                job["stage"] = msg
                
            source_video_path = video_engine.download_video_stream(req.url, download_dest, on_download_progress)
            
        # Step 2: Virality Analysis & Hook Identification
        has_campaign_rules = bool(req.campaign_rules and req.campaign_rules.get("has_rules"))
        if has_campaign_rules:
            job["stage"] = "Evaluating campaign rules, speech patterns, hooks, and retention peaks..."
        else:
            job["stage"] = "Analyzing speech patterns, hooks, and retention peaks..."
        job["progress"] = 55
        time.sleep(0.5)
        
        selected_moments = []
        if transcript_data:
            selected_moments = analyzer.find_viral_moments_from_transcript(
                transcript_data,
                requested_clips=req.clip_count,
                target_duration_mode=req.target_duration,
                campaign_rules=req.campaign_rules
            )
        else:
            # Fallback to audio peak & dynamic silence analysis via FFmpeg
            job["stage"] = "Detecting high-energy speech bursts & audio volume peaks..."
            actual_dur = video_engine.get_media_duration(source_video_path) or video_duration
            selected_moments = video_engine.analyze_audio_peaks_ffmpeg(
                source_video_path,
                duration=actual_dur,
                clip_count=req.clip_count
            )
            
        if not selected_moments:
            raise Exception("No usable speech or high-interest moments could be isolated from this video.")

        # Ensure we cap to user-requested clip count
        selected_moments = selected_moments[:req.clip_count]
        total_clips = len(selected_moments)
        job["total_clips"] = total_clips
        job["source_video_path"] = source_video_path

        # Step 3: FFmpeg clipping & layout formatting
        generated_clips = []
        clip_file_paths = []
        
        for idx, moment in enumerate(selected_moments):
            clip_num = idx + 1
            progress_pct = 60 + int((clip_num / total_clips) * 35)
            job["progress"] = progress_pct
            job["stage"] = f"Generating viral clip {clip_num} of {total_clips} in {req.aspect_ratio} ({req.crop_style.replace('_', ' ')}) format..."
            
            clip_filename = f"clip_{clip_num}.mp4"
            clip_output_path = os.path.join(job_dir, clip_filename)
            thumb_filename = f"thumb_{clip_num}.jpg"
            thumb_output_path = os.path.join(job_dir, thumb_filename)
            
            # Perform high quality FFmpeg cut
            success = video_engine.cut_clip_ffmpeg(
                source_video=source_video_path,
                start_sec=moment["start"],
                end_sec=moment["end"],
                output_video=clip_output_path,
                aspect_ratio=req.aspect_ratio,
                crop_style=req.crop_style
            )
            
            if success:
                # Generate thumbnail
                video_engine.generate_clip_thumbnail(clip_output_path, thumb_output_path, at_second=1.0)
                clip_file_paths.append(clip_output_path)
                
                generated_clips.append({
                    "id": clip_num,
                    "title": moment.get("title", f"Viral Moment #{clip_num}"),
                    "start": moment["start"],
                    "end": moment["end"],
                    "duration": round(moment["end"] - moment["start"], 1),
                    "virality_score": moment["virality_score"],
                    "hook_score": moment["hook_score"],
                    "retention_score": moment["retention_score"],
                    "energy_score": moment.get("energy_score", 85),
                    "rule_score": moment.get("rule_score", 100),
                    "rule_compliant": moment.get("rule_compliant", True),
                    "rule_badge": moment.get("rule_badge", "🎯 Rule Match"),
                    "rule_matched_keywords": moment.get("rule_matched_keywords", []),
                    "rule_reasons": moment.get("rule_reasons", []),
                    "badge": moment.get("badge", "🔥 Mega Viral"),
                    "badge_class": moment.get("badge_class", "badge-mega"),
                    "hook_type": moment.get("hook_type", "topic_hook"),
                    "trigger": moment.get("trigger", "High Retention Point"),
                    "summary": moment.get("summary", ""),
                    "video_url": f"/output/{job_id}/{clip_filename}",
                    "thumbnail_url": f"/output/{job_id}/{thumb_filename}",
                    "download_name": f"viral_clip_{clip_num}_{int(moment['start'])}s_{int(moment['end'])}s.mp4"
                })
                
        if not generated_clips:
            raise Exception("FFmpeg could not produce any video clips from the selected moments. Please check the video source.")

        # Step 4: Package batch ZIP archive
        job["stage"] = "Packaging all clips into instant batch ZIP archive..."
        job["progress"] = 96
        zip_filename = f"viral_clips_{job_id}.zip"
        zip_output_path = os.path.join(job_dir, zip_filename)
        video_engine.package_clips_to_zip(clip_file_paths, zip_output_path)
        
        job["zip_url"] = f"/output/{job_id}/{zip_filename}"
        job["clips"] = generated_clips
        job["status"] = "completed"
        job["stage"] = "All viral clips generated and ready for preview & download!"
        job["progress"] = 100
        
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        job["stage"] = f"Failed: {str(e)}"
        print(f"Error in job {job_id}: {e}")

@app.post("/api/process")
def process_video(req: ProcessRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]
    JOBS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "stage": "Job queued for viral analysis...",
        "clips": [],
        "created_at": time.time(),
        "req_params": req.dict()
    }
    background_tasks.add_task(run_clipping_pipeline, job_id, req)
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/job/{job_id}")
def get_job_status(job_id: str):
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    return JOBS[job_id]

@app.post("/api/trim")
def trim_clip(req: TrimRequest):
    if req.job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
        
    job = JOBS[req.job_id]
    source_video = job.get("source_video_path")
    if not source_video or not os.path.exists(source_video):
        raise HTTPException(status_code=400, detail="Master video source not found for re-trimming")
        
    clip = next((c for c in job["clips"] if c["id"] == req.clip_id), None)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
        
    clip_output_path = os.path.join(OUTPUT_DIR, req.job_id, f"clip_{req.clip_id}.mp4")
    aspect = job.get("req_params", {}).get("aspect_ratio", "9:16")
    crop_style = job.get("req_params", {}).get("crop_style", "blurred_background")
    
    success = video_engine.cut_clip_ffmpeg(
        source_video=source_video,
        start_sec=req.start,
        end_sec=req.end,
        output_video=clip_output_path,
        aspect_ratio=aspect,
        crop_style=crop_style
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to re-render trimmed clip")
        
    # Update clip attributes
    clip["start"] = round(req.start, 2)
    clip["end"] = round(req.end, 2)
    clip["duration"] = round(req.end - req.start, 1)
    # Refresh cache buster
    clip["video_url"] = f"/output/{req.job_id}/clip_{req.clip_id}.mp4?v={int(time.time())}"
    
    return {"success": True, "clip": clip}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
