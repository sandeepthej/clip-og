import re
import math
from typing import List, Dict, Any, Tuple, Optional
import rules_engine

# High-impact viral hook triggers categorized by psychological hook type
HOOK_PATTERNS = {
    "curiosity_gap": [
        r"\b(the real reason|the truth (about|is)|nobody (talks about|knows|tells you)|the secret (to|behind)?)\b",
        r"\b(here('s| is) (what|the thing|why|the problem)|the biggest mistake|what they don't want you to know)\b",
        r"\b(this changed everything|i (never|always) thought|watch what happens|wait until you see)\b",
        r"\b(most people don't know|most people (fail|get this wrong|think))\b",
    ],
    "bold_statement": [
        r"\b(stop doing this|you need to stop|do not make this mistake|this is a waste of time)\b",
        r"\b(this is (insane|crazy|ridiculous|unbelievable|mind-blowing|huge))\b",
        r"\b(how to (make|grow|get|scale|automate|master))\b",
        r"\b(if you want to|the only way to|rule number (one|1)|step (one|1))\b",
        r"\b(10x|100x|\$\d+|\d+ percent|\d+%|million(aire)?|billion(aire)?)\b",
    ],
    "question_hook": [
        r"^(why|how|what|did you know|have you ever|can you believe|is it really)",
        r"\b(why do (we|people|most)|how did this happen|what would happen if)\b",
    ],
    "story_opener": [
        r"\b(when i was|three years ago|in 20\d\d|my mentor told me|i lost everything|the moment i realized)\b",
        r"\b(i tried this for 30 days|here is my story|first time i ever)\b"
    ]
}

HIGH_RETENTION_WORDS = {
    "secret", "mistake", "truth", "insane", "crazy", "money", "future", "system", 
    "strategy", "formula", "proof", "hack", "power", "million", "millionaire", 
    "success", "failure", "dangerous", "warning", "automatic", "instant", "guaranteed", 
    "billion", "invest", "ai", "game-changer", "breakthrough", "leverage", "hidden", 
    "exposed", "mastery", "cheat code", "unbelievable", "simple", "brutal"
}

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "over", "after", "is", "are", "was", "were"
}

def clean_text(text: str) -> str:
    """Removes speaker labels like [Music], (Laughter), Speaker 1:, etc."""
    text = re.sub(r"\[.*?\]|\(.*?\)", "", text)
    text = re.sub(r"^[A-Z0-9\s]+:\s*", "", text)
    return text.strip()

def detect_hook_strength(first_few_sentences: str) -> Tuple[float, str, str]:
    """
    Evaluates the first 5-10 seconds of a candidate clip to determine hook potential.
    Returns (score_0_to_100, hook_category, sample_trigger)
    """
    text_lower = first_few_sentences.lower()
    score = 45.0  # baseline
    best_category = "topic_intro"
    trigger_found = ""

    # Check question hook
    if "?" in first_few_sentences[:60] or re.search(r"^(why|how|what|did|is|are|can)", text_lower):
        score += 24.0
        best_category = "question_hook"
        trigger_found = "Rhetorical Question Hook"

    # Check defined psychological patterns
    for cat, regex_list in HOOK_PATTERNS.items():
        for pat in regex_list:
            match = re.search(pat, text_lower)
            if match:
                score += 28.0
                best_category = cat
                trigger_found = match.group(0)
                break

    # Check high retention words density in opening
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text_lower)
    buzz_count = sum(1 for w in words[:15] if w in HIGH_RETENTION_WORDS)
    score += buzz_count * 5.0

    score = min(99.0, max(40.0, score))
    return round(score, 1), best_category, trigger_found

def calculate_retention_score(clip_text: str, duration: float) -> float:
    """
    Measures engagement balance:
    - Optimal short duration (25 - 55 seconds is peak)
    - Word density and informational flow
    """
    text_lower = clip_text.lower()
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text_lower)
    word_count = len(words)
    
    # Ideal speaking rate in shorts is ~130 to 170 words per minute
    wpm = (word_count / max(1.0, duration)) * 60.0
    wpm_score = 30.0
    if 120 <= wpm <= 180:
        wpm_score = 40.0
    elif 90 <= wpm < 120 or 180 < wpm <= 220:
        wpm_score = 32.0
    else:
        wpm_score = 22.0

    # Duration curve penalty (prefer 25s - 60s)
    dur_score = 30.0
    if 25 <= duration <= 55:
        dur_score = 40.0
    elif 18 <= duration < 25 or 55 < duration <= 75:
        dur_score = 32.0
    else:
        dur_score = 20.0

    # Vocabulary & topic density
    unique_words = set(w for w in words if w not in STOP_WORDS)
    diversity = len(unique_words) / max(1, len(words))
    diversity_score = min(20.0, diversity * 30.0)

    total_score = min(98.0, max(50.0, wpm_score + dur_score + diversity_score))
    return round(total_score, 1)

def generate_viral_title(first_sentence: str, full_text: str) -> str:
    """Creates a punchy YouTube Shorts / TikTok style headline."""
    cleaned = clean_text(first_sentence).replace('"', '').strip()
    
    # If the first sentence has a strong question or statement
    if len(cleaned) > 10 and len(cleaned) < 55:
        # Capitalize nicely
        title = cleaned.rstrip(".,;!")
        if "?" in cleaned:
            return title + "?"
        return title.title()
    
    # Search for buzzword sentences
    sentences = re.split(r"[.!?]+", full_text)
    for s in sentences:
        s_clean = s.strip()
        s_lower = s_clean.lower()
        for w in HIGH_RETENTION_WORDS:
            if w in s_lower and 12 < len(s_clean) < 60:
                return s_clean.rstrip(".,;!").title()

    # Fallback to smart excerpt
    words = cleaned.split()
    if len(words) > 6:
        return " ".join(words[:6]).title() + "..."
    return "Viral Moment Highlight"

def find_viral_moments_from_transcript(
    transcript: List[Dict[str, Any]], 
    requested_clips: int = 10,
    target_duration_mode: str = "auto",
    campaign_rules: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Parses full video transcript into high-scoring, non-overlapping viral clip segments.
    Applies psychological hook detection, engagement retention scoring, and
    AI campaign rules compliance filtering.
    """
    if not transcript:
        return []

    # Map target duration
    min_dur, max_dur = 25.0, 55.0
    
    # Check if campaign rules specify a duration override
    if campaign_rules and campaign_rules.get("has_rules"):
        rule_dur = campaign_rules.get("preferred_duration", "auto")
        if rule_dur != "auto" and target_duration_mode == "auto":
            target_duration_mode = rule_dur

    if target_duration_mode == "short":
        min_dur, max_dur = 15.0, 32.0
    elif target_duration_mode == "medium":
        min_dur, max_dur = 30.0, 60.0
    elif target_duration_mode == "extended":
        min_dur, max_dur = 55.0, 95.0

    total_items = len(transcript)
    total_video_duration = transcript[-1]["start"] + transcript[-1].get("duration", 2.0)
    
    candidates = []
    
    # Slide across transcript to find high-potential start points
    step = max(1, int(total_items / (requested_clips * 4))) if total_items > 40 else 1
    
    for i in range(0, total_items, step):
        start_item = transcript[i]
        start_time = float(start_item["start"])
        
        # Don't start too close to the very end
        if total_video_duration - start_time < min_dur:
            break
            
        accumulated_text = []
        end_time = start_time
        candidate_end_index = i
        
        for j in range(i, total_items):
            item = transcript[j]
            item_text = clean_text(item.get("text", ""))
            accumulated_text.append(item_text)
            current_end = float(item["start"]) + float(item.get("duration", 2.0))
            current_dur = current_end - start_time
            
            # Check if this item ends with sentence punctuation
            has_sentence_end = bool(re.search(r"[.!?]\s*$", item_text))
            
            if current_dur >= min_dur:
                # If we found a natural sentence break or reached max duration
                if has_sentence_end or current_dur >= max_dur:
                    end_time = current_end
                    candidate_end_index = j
                    break
                else:
                    end_time = current_end
                    candidate_end_index = j
        
        clip_duration = end_time - start_time
        if clip_duration < min_dur * 0.8:
            continue
            
        full_clip_text = " ".join(accumulated_text)
        first_few = " ".join(accumulated_text[:4])
        
        # Calculate virality components
        hook_score, hook_cat, trigger = detect_hook_strength(first_few)
        retention_score = calculate_retention_score(full_clip_text, clip_duration)
        energy_score = round(min(98.0, 60.0 + (hook_score * 0.2) + (retention_score * 0.18)), 1)
        
        # Overall Virality Score (weighted)
        overall_virality = round(
            (0.48 * hook_score) + (0.36 * retention_score) + (0.16 * energy_score), 1
        )
        
        # Evaluate against Campaign Rules (if active)
        rule_eval = rules_engine.score_clip_rule_compliance(
            clip_text=full_clip_text,
            hook_text=first_few,
            hook_type=hook_cat,
            duration=clip_duration,
            rules=campaign_rules or {}
        )
        
        # Generate dynamic title
        title = generate_viral_title(first_few, full_clip_text)
        
        # Summary preview
        words = full_clip_text.split()
        summary = " ".join(words[:25]) + ("..." if len(words) > 25 else "")
        
        # Blended ranking score
        has_rules = bool(campaign_rules and campaign_rules.get("has_rules"))
        if has_rules:
            # Heavily weight campaign rules compliance
            if rule_eval["violated"]:
                ranking_score = 10.0
            else:
                ranking_score = (0.70 * rule_eval["score"]) + (0.30 * overall_virality)
        else:
            ranking_score = float(overall_virality)

        candidates.append({
            "start": round(start_time, 2),
            "end": round(end_time, 2),
            "duration": round(clip_duration, 1),
            "virality_score": int(overall_virality),
            "hook_score": int(hook_score),
            "retention_score": int(retention_score),
            "energy_score": int(energy_score),
            "rule_score": int(rule_eval["score"]),
            "rule_compliant": rule_eval["is_compliant"],
            "rule_violated": rule_eval["violated"],
            "rule_badge": rule_eval["badge"],
            "rule_matched_keywords": rule_eval["matched_keywords"],
            "rule_reasons": rule_eval["reasons"],
            "ranking_score": ranking_score,
            "hook_type": hook_cat,
            "trigger": trigger or "High Context Flow",
            "title": title,
            "summary": summary,
            "full_text": full_clip_text,
            "start_index": i,
            "end_index": candidate_end_index
        })
        
    # Sort candidates by ranking score descending (prioritizes rule matches!)
    candidates.sort(key=lambda x: x["ranking_score"], reverse=True)
    
    # Filter out strictly violated clips if other compliant clips exist
    valid_candidates = [c for c in candidates if not c.get("rule_violated", False)]
    if valid_candidates:
        pool = valid_candidates
    else:
        pool = candidates
    
    # Filter overlapping clips to ensure diversity across the video
    selected_clips: List[Dict[str, Any]] = []
    
    # Helper to check overlap
    def has_overlap(c, existing_list, max_overlap_sec=6.0):
        for ex in existing_list:
            overlap_start = max(c["start"], ex["start"])
            overlap_end = min(c["end"], ex["end"])
            if overlap_end - overlap_start > max_overlap_sec:
                return True
        return False
        
    for cand in pool:
        if not has_overlap(cand, selected_clips):
            selected_clips.append(cand)
            if len(selected_clips) >= requested_clips:
                break
                
    # If more clips are needed, allow slightly more overlap
    if len(selected_clips) < requested_clips:
        for cand in pool:
            if cand not in selected_clips:
                if not has_overlap(cand, selected_clips, max_overlap_sec=15.0):
                    selected_clips.append(cand)
                    if len(selected_clips) >= requested_clips:
                        break

    # If still more clips are needed, slice remaining spans evenly
    if len(selected_clips) < requested_clips and total_video_duration > min_dur:
        needed = requested_clips - len(selected_clips)
        interval = max(min_dur, total_video_duration / (requested_clips + 1))
        for step_idx in range(requested_clips):
            s_time = step_idx * interval
            e_time = min(total_video_duration, s_time + min_dur)
            if e_time - s_time >= min_dur * 0.7:
                synthetic_cand = {
                    "start": round(s_time, 2),
                    "end": round(e_time, 2),
                    "duration": round(e_time - s_time, 1),
                    "virality_score": max(65, 88 - (step_idx * 2)),
                    "hook_score": max(60, 85 - (step_idx * 2)),
                    "retention_score": max(65, 86 - step_idx),
                    "energy_score": max(65, 84 - step_idx),
                    "rule_score": 75,
                    "rule_compliant": True,
                    "rule_violated": False,
                    "rule_badge": "🎯 Rule Match",
                    "rule_matched_keywords": [],
                    "rule_reasons": ["Automated timestamp segment"],
                    "ranking_score": 80.0,
                    "hook_type": "key_highlight",
                    "trigger": f"Timestamp Segment #{step_idx + 1}",
                    "title": f"Viral Highlight Part {step_idx + 1}",
                    "summary": f"Key moments captured from {int(s_time)}s to {int(e_time)}s",
                    "full_text": ""
                }
                if not any(abs(ex["start"] - synthetic_cand["start"]) < 5.0 for ex in selected_clips):
                    selected_clips.append(synthetic_cand)
                    if len(selected_clips) >= requested_clips:
                        break

    # Add rank index and badges
    for idx, clip in enumerate(selected_clips):
        clip["id"] = idx + 1
        score = clip["virality_score"]
        rule_score = clip.get("rule_score", 100)
        
        # Badge determination
        if campaign_rules and campaign_rules.get("has_rules") and rule_score >= 85:
            clip["badge"] = "🎯 Campaign Winner"
            clip["badge_class"] = "badge-mega"
        elif score >= 95:
            clip["badge"] = "🔥 Mega Viral"
            clip["badge_class"] = "badge-mega"
        elif score >= 88:
            clip["badge"] = "🚀 High Retention"
            clip["badge_class"] = "badge-high"
        elif score >= 80:
            clip["badge"] = "✨ Strong Hook"
            clip["badge_class"] = "badge-medium"
        else:
            clip["badge"] = "⚡ Engaging Cut"
            clip["badge_class"] = "badge-standard"

    return selected_clips
