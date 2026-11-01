import os
import re
import subprocess
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OCR_SCRIPT = os.path.join(BASE_DIR, "ocr_helper.ps1")

COMMON_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "over", "after", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did", "can", "could",
    "should", "would", "will", "shall", "may", "might", "must", "that", "which", "who",
    "whom", "this", "these", "those", "then", "there", "when", "where", "why", "how",
    "all", "any", "both", "each", "few", "more", "most", "other", "some", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t",
    "just", "don", "shouldn", "now", "rule", "rules", "campaign", "video", "clip", "clips"
}

def ocr_image_file(image_path: str) -> str:
    """
    Extracts text from an image file using Windows native OCR engine via ocr_helper.ps1.
    Fallback to clean error string if OCR fails.
    """
    if not os.path.exists(image_path):
        return ""

    if os.path.exists(OCR_SCRIPT):
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", OCR_SCRIPT,
                "-ImagePath", image_path
            ]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=25)
            if proc.returncode == 0 and proc.stdout.strip():
                return proc.stdout.strip()
        except Exception as e:
            print(f"Windows OCR error: {e}")

    # Fallback to basic image metadata / message
    return ""

def parse_campaign_rules(
    rules_text: str = "",
    custom_keywords: Optional[List[str]] = None,
    custom_banned: Optional[List[str]] = None,
    hook_preference: Optional[str] = None,
    min_compliance: float = 65.0
) -> Dict[str, Any]:
    """
    Analyzes raw campaign rules text and structured inputs to build
    a rigorous rule profile for filtering and ranking clips.
    """
    text_lower = rules_text.lower()
    
    # Extract keywords
    extracted_keywords = set()
    if custom_keywords:
        for k in custom_keywords:
            if k.strip():
                extracted_keywords.add(k.strip().lower())

    # Auto-extract high-value terms from text if provided
    words = re.findall(r"\b[a-zA-Z]{3,}\b", text_lower)
    for w in words:
        if w not in COMMON_STOP_WORDS and len(w) > 3:
            # Look for context indicators like "focus on X", "highlight X", "about X", "include X"
            if re.search(rf"\b(focus|highlight|include|about|topic|show|feature|mention|must have|target)\s+[^.\n]*?\b{w}\b", text_lower):
                extracted_keywords.add(w)

    # If still few, take frequent meaningful nouns/terms
    if len(extracted_keywords) < 3 and words:
        freq = {}
        for w in words:
            if w not in COMMON_STOP_WORDS and len(w) > 3:
                freq[w] = freq.get(w, 0) + 1
        sorted_by_freq = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        for w, count in sorted_by_freq[:8]:
            extracted_keywords.add(w)

    # Extract banned / negative words
    extracted_banned = set()
    if custom_banned:
        for b in custom_banned:
            if b.strip():
                extracted_banned.add(b.strip().lower())

    # Look for negative patterns: "avoid X", "no X", "don't include X", "exclude X", "never X"
    neg_matches = re.findall(r"\b(?:avoid|no|never|don't|do not|exclude|without|ban|forbidden)\s+([a-zA-Z\s,]+?)(?:[.\n;]|$)", text_lower)
    for neg_phrase in neg_matches:
        neg_words = re.findall(r"\b[a-zA-Z]{3,}\b", neg_phrase)
        for nw in neg_words:
            if nw not in COMMON_STOP_WORDS and nw not in extracted_keywords:
                extracted_banned.add(nw)

    # Detect preferred duration
    duration_mode = "auto"
    if re.search(r"\b(under 30|15\s*-\s*30|short|less than 30|quick|punchy|15s|30s)\b", text_lower):
        duration_mode = "short"
    elif re.search(r"\b(30\s*-\s*60|medium|standard|45s|60s)\b", text_lower):
        duration_mode = "medium"
    elif re.search(r"\b(over 60|60\s*-\s*90|extended|long|deep dive)\b", text_lower):
        duration_mode = "extended"

    # Detect hook preference
    detected_hook = hook_preference or "any"
    if detected_hook == "any":
        if re.search(r"\b(question|ask|rhetorical)\b", text_lower):
            detected_hook = "question_hook"
        elif re.search(r"\b(bold|stop doing|statement|controversial|shocking)\b", text_lower):
            detected_hook = "bold_statement"
        elif re.search(r"\b(story|personal|journey|lesson)\b", text_lower):
            detected_hook = "story_opener"
        elif re.search(r"\b(curiosity|secret|truth|nobody knows)\b", text_lower):
            detected_hook = "curiosity_gap"

    return {
        "raw_text": rules_text,
        "keywords": list(extracted_keywords),
        "banned_keywords": list(extracted_banned),
        "preferred_duration": duration_mode,
        "hook_preference": detected_hook,
        "min_compliance": min_compliance,
        "has_rules": bool(rules_text.strip() or extracted_keywords or extracted_banned)
    }

def score_clip_rule_compliance(
    clip_text: str,
    hook_text: str,
    hook_type: str,
    duration: float,
    rules: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Evaluates a candidate clip against active campaign rules.
    Returns compliance score (0-100), reasons, and status.
    """
    if not rules or not rules.get("has_rules"):
        return {
            "score": 100,
            "is_compliant": True,
            "violated": False,
            "matched_keywords": [],
            "reasons": ["Standard Clipping (No custom campaign rules specified)"],
            "badge": "✓ Standard"
        }

    clip_lower = clip_text.lower()
    hook_lower = hook_text.lower()
    
    score = 50.0  # baseline
    matched_keywords = []
    matched_banned = []
    reasons = []

    # 1. Check for Banned / Forbidden words (Critical penalty)
    banned_list = rules.get("banned_keywords", [])
    for b in banned_list:
        if re.search(rf"\b{re.escape(b)}\b", clip_lower):
            matched_banned.append(b)

    if matched_banned:
        # Severe penalty or disqualification
        score -= len(matched_banned) * 40.0
        reasons.append(f"Contains forbidden term(s): {', '.join(matched_banned)}")

    # 2. Check for Required / Target Keywords
    keywords_list = rules.get("keywords", [])
    if keywords_list:
        kw_hits = 0
        for kw in keywords_list:
            # Check presence in clip or hook
            in_hook = bool(re.search(rf"\b{re.escape(kw)}\b", hook_lower))
            in_body = bool(re.search(rf"\b{re.escape(kw)}\b", clip_lower))
            
            if in_hook:
                matched_keywords.append(f"{kw} (in Hook)")
                kw_hits += 2.0
            elif in_body:
                matched_keywords.append(kw)
                kw_hits += 1.0

        ratio = min(1.0, kw_hits / max(1.0, len(keywords_list) * 0.6))
        score += ratio * 35.0
        if matched_keywords:
            reasons.append(f"Matched {len(matched_keywords)} target keyword(s): {', '.join(matched_keywords[:4])}")
        else:
            score -= 15.0
            reasons.append("Low coverage of campaign target topics")

    # 3. Check Hook Preference
    target_hook = rules.get("hook_preference", "any")
    if target_hook and target_hook != "any":
        if hook_type == target_hook:
            score += 15.0
            reasons.append(f"Matches required hook style: {target_hook.replace('_', ' ').title()}")
        else:
            score -= 10.0
            reasons.append(f"Different hook style ({hook_type.replace('_', ' ').title()} vs requested {target_hook.replace('_', ' ').title()})")

    # 4. Check Duration Preference
    dur_pref = rules.get("preferred_duration", "auto")
    if dur_pref == "short":
        if 15.0 <= duration <= 32.0:
            score += 10.0
            reasons.append("Optimal short duration for campaign (15-30s)")
        else:
            score -= 8.0
    elif dur_pref == "medium":
        if 30.0 <= duration <= 60.0:
            score += 10.0
            reasons.append("Matches standard campaign duration (30-60s)")
        else:
            score -= 5.0
    elif dur_pref == "extended":
        if 55.0 <= duration <= 95.0:
            score += 10.0
            reasons.append("Matches extended campaign duration (60-90s)")
        else:
            score -= 8.0

    final_score = int(min(100.0, max(0.0, score)))
    min_thresh = rules.get("min_compliance", 65.0)
    is_compliant = (final_score >= min_thresh) and (len(matched_banned) == 0)
    violated = len(matched_banned) > 0

    badge = "🎯 Rule Match" if is_compliant else ("⚠️ Low Match" if not violated else "❌ Violates Rule")

    return {
        "score": final_score,
        "is_compliant": is_compliant,
        "violated": violated,
        "matched_keywords": matched_keywords,
        "banned_hits": matched_banned,
        "reasons": reasons,
        "badge": badge
    }
