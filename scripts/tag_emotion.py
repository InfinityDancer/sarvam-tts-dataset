import os
import sys
import glob
import json
import re
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
if not SARVAM_API_KEY:
    print("SARVAM_API_KEY not found in environment. Please set it in .env")
    exit(1)

HINDI_DIR = r"c:\Users\aasth\Documents\Sarvam\videos\Hindi_diarized"
HINDI_JSON_DIR = r"c:\Users\aasth\Documents\Sarvam\videos\Hindi_clipped\sarvam_outputs"
ENG_DIR = r"c:\Users\aasth\Documents\Sarvam\videos\IndianEng\IndianEng_transcripts"

OUTPUT_DIR = r"c:\Users\aasth\Documents\Sarvam\videos\Emotion_Tags"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Clear old tags on every run
for old_file in glob.glob(os.path.join(OUTPUT_DIR, "*_tag.txt")):
    os.remove(old_file)
print("Cleared old emotion tags.\n")

CHUNK_DURATION = 20.0  # seconds per chunk

def call_sarvam_tag(chunk_text):
    """Call Sarvam API to tag a single short chunk of text with descriptive emotions."""
    url = "https://api.sarvam.ai/v1/chat/completions"
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "model": "sarvam-105b",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are an emotion and style tagger. Given a short text segment, "
                    "provide 1 to 3 descriptive emotion/style tags that best capture its tone. "
                    "Examples of tags: happy, sad, excited, angry, formal, casual, humorous, "
                    "passionate, informative, contemplative, urgent, nostalgic, empathetic, etc.\n"
                    "Output ONLY the tags as a comma-separated list, in lowercase. Do not output anything else."
                )
            },
            {"role": "user", "content": f"Segment: {chunk_text}"}
        ],
        "temperature": 0.3,
        "max_tokens": 20
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        res_json = response.json()
        if "choices" in res_json and len(res_json["choices"]) > 0:
            content = res_json["choices"][0]["message"].get("content")
            if content:
                # Clean up and return the comma-separated tags
                tags = [t.strip() for t in content.strip().lower().rstrip(".").split(',')]
                return ", ".join([t for t in tags if t])
        else:
            print(f"  Warning: No choices in API response")
        return "neutral"
    except Exception as e:
        print(f"  Error calling Sarvam API: {e}")
        return "neutral"


def chunk_hindi_transcript(txt_file):
    """For Hindi files, split the text into 3 equal chunks."""
    return split_text_into_chunks(txt_file, num_chunks=3)



def split_text_into_chunks(txt_file, num_chunks=3):
    """Split a plain text transcript into roughly equal chunks by sentences."""
    with open(txt_file, "r", encoding="utf-8") as f:
        text = f.read().strip()
    
    if not text:
        return []
    
    # Split by sentence boundaries (periods, question marks, exclamation marks)
    # Handle both English and Hindi sentence endings
    sentences = re.split(r'(?<=[।.!?])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    
    if len(sentences) <= num_chunks:
        return sentences if sentences else [text]
    
    # Distribute sentences into chunks
    chunk_size = len(sentences) // num_chunks
    remainder = len(sentences) % num_chunks
    chunks = []
    idx = 0
    for i in range(num_chunks):
        end = idx + chunk_size + (1 if i < remainder else 0)
        chunk_text = " ".join(sentences[idx:end])
        if chunk_text:
            chunks.append(chunk_text)
        idx = end
    
    return chunks if chunks else [text]


def process_hindi_transcripts():
    txt_files = glob.glob(os.path.join(HINDI_DIR, "*.txt"))
    print(f"Found {len(txt_files)} Hindi transcript files.\n")
    
    for txt_file in txt_files:
        basename = os.path.basename(txt_file)
        file_prefix = os.path.splitext(basename)[0]
        out_file = os.path.join(OUTPUT_DIR, f"{file_prefix}_tag.txt")
        
        chunks = chunk_hindi_transcript(txt_file)
        if not chunks:
            print(f"{basename} -> (empty transcript)")
            continue
        
        tags = []
        for i, chunk in enumerate(chunks):
            tag = call_sarvam_tag(chunk)
            tags.append(tag)
            print(f"  Chunk {i+1}/{len(chunks)}: {tag}")
        
        # Deduplicate while preserving order
        seen = set()
        unique_tags = []
        for t in tags:
            if t not in seen:
                seen.add(t)
                unique_tags.append(t)
        
        result = ", ".join(unique_tags)
        print(f"{basename} -> {result}\n")
        
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(result)


def process_eng_transcripts():
    txt_files = glob.glob(os.path.join(ENG_DIR, "*.txt"))
    print(f"\nFound {len(txt_files)} English transcript files.\n")
    
    for txt_file in txt_files:
        basename = os.path.basename(txt_file)
        file_prefix = os.path.splitext(basename)[0]
        out_file = os.path.join(OUTPUT_DIR, f"{file_prefix}_tag.txt")
        
        chunks = split_text_into_chunks(txt_file)
        if not chunks:
            print(f"{basename} -> (empty transcript)")
            continue
        
        tags = []
        for i, chunk in enumerate(chunks):
            tag = call_sarvam_tag(chunk)
            tags.append(tag)
            print(f"  Chunk {i+1}/{len(chunks)}: {tag}")
        
        # Deduplicate while preserving order
        seen = set()
        unique_tags = []
        for t in tags:
            if t not in seen:
                seen.add(t)
                unique_tags.append(t)
        
        result = ", ".join(unique_tags)
        print(f"{basename} -> {result}\n")
        
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(result)


if __name__ == "__main__":
    process_hindi_transcripts()
    process_eng_transcripts()
    print("\nDone! All emotion tags saved to:", OUTPUT_DIR)
