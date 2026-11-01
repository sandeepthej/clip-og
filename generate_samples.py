import os
import json
import subprocess

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "samples")
os.makedirs(SAMPLE_DIR, exist_ok=True)

SAMPLES_META = [
    {
        "id": "sample_tech_talk",
        "title": "The Brutal Truth About Scaling AI Startups in 2026",
        "uploader": "Tech Founders Masterclass",
        "duration": 130,
        "view_count": 842000,
        "thumbnail": "/samples/sample_tech_talk.jpg",
        "transcript": [
            {"start": 0.0, "duration": 4.5, "text": "The real reason 99% of startups fail with AI today is simple."},
            {"start": 4.5, "duration": 4.0, "text": "Nobody talks about this, but they are building wrappers instead of value."},
            {"start": 8.5, "duration": 5.0, "text": "If you want to 10x your revenue, here is the secret formula we used."},
            {"start": 13.5, "duration": 5.2, "text": "Rule number one: Stop building chatbots and start automating end-to-end workflows."},
            {"start": 18.7, "duration": 4.8, "text": "When we switched our focus, our customer retention doubled within 30 days."},
            {"start": 23.5, "duration": 5.0, "text": "Most founders think you need millions of dollars in venture capital to scale."},
            {"start": 28.5, "duration": 4.5, "text": "That is completely insane. You can launch a profitable agentic workflow with zero upfront cost."},
            {"start": 33.0, "duration": 5.0, "text": "Why do people still believe you need a team of 50 engineers? Look at the evidence."},
            {"start": 38.0, "duration": 5.5, "text": "Small autonomous teams are outpacing giant corporations by a factor of ten."},
            {"start": 43.5, "duration": 4.5, "text": "The second biggest mistake is ignoring your distribution channels."},
            {"start": 48.0, "duration": 5.0, "text": "If you cannot capture attention in the first three seconds, your product is dead."},
            {"start": 53.0, "duration": 4.5, "text": "Here is what happens when you master short-form viral storytelling."},
            {"start": 57.5, "duration": 5.0, "text": "You gain organic leverage that money simply cannot buy in modern digital marketing."},
            {"start": 62.5, "duration": 5.0, "text": "Have you noticed how top creators dominate every single algorithm today?"},
            {"start": 67.5, "duration": 4.8, "text": "They repurpose one long-form conversation into twenty viral clips automatically."},
            {"start": 72.3, "duration": 5.2, "text": "That is the cheat code. Work once, distribute infinitely across TikTok, Reels, and Shorts."},
            {"start": 77.5, "duration": 4.5, "text": "Three years ago, my mentor told me something that transformed my entire career."},
            {"start": 82.0, "duration": 5.0, "text": "He said: Sandeep, the greatest leverage in the 21st century is automated media production."},
            {"start": 87.0, "duration": 5.0, "text": "Stop trading your hours for linear output. Build software machines that work while you sleep."},
            {"start": 92.0, "duration": 4.5, "text": "And that is why this moment in technology is the greatest opportunity in human history."},
            {"start": 96.5, "duration": 5.0, "text": "Do not wait until next year. The window to establish your media moat is right now."},
            {"start": 101.5, "duration": 5.0, "text": "If you follow these three principles, success is not just possible, it is guaranteed."}
        ]
    },
    {
        "id": "sample_mindset_podcast",
        "title": "Why Discipline Beats Motivation Every Single Time",
        "uploader": "Peak Performance Daily",
        "duration": 120,
        "view_count": 1420000,
        "thumbnail": "/samples/sample_mindset_podcast.jpg",
        "transcript": [
            {"start": 0.0, "duration": 5.0, "text": "Stop waiting for motivation. Motivation is a complete emotional trap."},
            {"start": 5.0, "duration": 4.5, "text": "Did you know that top performers feel lazy more than 60% of their mornings?"},
            {"start": 9.5, "duration": 5.2, "text": "The secret behind Olympic athletes and billionaire CEOs is unnegotiable discipline."},
            {"start": 14.7, "duration": 4.8, "text": "The moment you wake up, your brain starts negotiating reasons to stay comfortable."},
            {"start": 19.5, "duration": 5.0, "text": "Here is the brutal truth: if you listen to that voice, you have already surrendered."},
            {"start": 24.5, "duration": 5.5, "text": "How do you kill procrastination instantly? Follow the five-second ignition rule."},
            {"start": 30.0, "duration": 4.5, "text": "Count 5, 4, 3, 2, 1 and move your physical body immediately into action."},
            {"start": 34.5, "duration": 5.0, "text": "This simple psychological hack short-circuits your brain's fear mechanisms."},
            {"start": 39.5, "duration": 5.2, "text": "When I lost everything in my early twenties, I thought talent was the answer."},
            {"start": 44.7, "duration": 4.8, "text": "I was completely wrong. Talent without consistent execution is just wasted potential."},
            {"start": 49.5, "duration": 5.0, "text": "Small daily micro-wins compound into massive extraordinary transformations over time."},
            {"start": 54.5, "duration": 5.0, "text": "Never underestimate the power of showing up on the days you feel at your worst."},
            {"start": 59.5, "duration": 5.5, "text": "That is when real character and unstoppable confidence are forged in the fire."},
            {"start": 65.0, "duration": 5.0, "text": "Start today. Stop waiting for the perfect conditions. Perfect never arrives."}
        ]
    }
]

def generate_video_file(meta):
    vid_id = meta["id"]
    output_mp4 = os.path.join(SAMPLE_DIR, f"{vid_id}.mp4")
    output_jpg = os.path.join(SAMPLE_DIR, f"{vid_id}.jpg")
    duration = meta["duration"]
    title = meta["title"]
    
    if os.path.exists(output_mp4) and os.path.exists(output_jpg):
        return

    print(f"Generating sample video: {vid_id}...")
    
    # Generate 1080p sample video using FFmpeg with gradient / animated visuals and audio tone
    # Use color bars or gradient
    filter_expr = (
        f"testsrc=duration={duration}:size=1280x720:rate=30,"
        f"drawbox=y=0:color=black@0.6:width=iw:height=100:t=fill,"
        f"drawtext=text='{title[:40]}':fontsize=32:fontcolor=white:x=(w-text_w)/2:y=30:box=1:boxcolor=black@0.4,"
        f"drawtext=text='Opus AutoClipper Demo Master Video':fontsize=22:fontcolor=yellow:x=(w-text_w)/2:y=650"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", filter_expr,
        "-f", "lavfi", "-i", f"sine=frequency=432:duration={duration}",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k",
        "-t", str(duration),
        output_mp4
    ]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Generate thumbnail
    cmd_thumb = [
        "ffmpeg", "-y",
        "-ss", "2.0",
        "-i", output_mp4,
        "-vframes", "1",
        output_jpg
    ]
    subprocess.run(cmd_thumb, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print(f"Sample {vid_id} created successfully!")

def main():
    meta_json_path = os.path.join(SAMPLE_DIR, "samples.json")
    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump(SAMPLES_META, f, indent=2)
        
    for meta in SAMPLES_META:
        try:
            generate_video_file(meta)
        except Exception as e:
            print(f"Error creating sample {meta['id']}: {e}")

if __name__ == "__main__":
    main()
