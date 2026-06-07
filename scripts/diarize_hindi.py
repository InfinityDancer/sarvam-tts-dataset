import os
import sys
import glob
import json
import subprocess
from dotenv import load_dotenv
from sarvamai import SarvamAI

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
if not SARVAM_API_KEY:
    print("SARVAM_API_KEY not found in environment. Please set it in .env")
    exit(1)

client = SarvamAI(api_subscription_key=SARVAM_API_KEY)

INPUT_DIR = r"c:\Users\aasth\Documents\Sarvam\videos\Hindi_clipped"
OUTPUT_DIR = r"c:\Users\aasth\Documents\Sarvam\videos\Hindi_diarized"
SARVAM_OUT_DIR = os.path.join(INPUT_DIR, "sarvam_outputs")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(SARVAM_OUT_DIR, exist_ok=True)

# Find audio files in INPUT_DIR
audio_files = []
for ext in ["*.wav", "*.m4a", "*.mp3", "*.webm"]:
    audio_files.extend(glob.glob(os.path.join(INPUT_DIR, ext)))

print(f"Found {len(audio_files)} audio files to process in {INPUT_DIR}.")

def slice_audio(input_file, output_file, start_sec, end_sec):
    duration = end_sec - start_sec
    cmd = [
        "ffmpeg", "-y", "-i", input_file,
        "-ss", str(start_sec), "-t", str(duration),
        "-c", "copy", output_file
    ]
    if output_file.endswith(".wav"):
        cmd = [
            "ffmpeg", "-y", "-i", input_file,
            "-ss", str(start_sec), "-t", str(duration),
            "-c:a", "pcm_s16le", output_file
        ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error slicing {input_file} with ffmpeg: {e}")
        return False

def process_file(file_path):
    basename = os.path.basename(file_path)
    print(f"\nProcessing {basename}")
    file_prefix = os.path.splitext(basename)[0]
    
    # Check if we already processed this file by looking for the output txt file
    existing_txts = glob.glob(os.path.join(OUTPUT_DIR, f"{file_prefix}_*.txt"))
    if existing_txts:
        print(f"Already processed {basename}, skipping.")
        return
        
    try:
        json_file = os.path.join(SARVAM_OUT_DIR, f"{basename}.json")
        if os.path.exists(json_file):
            print(f"Using existing JSON output for {basename}")
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            # Create a batch job for speech-to-text with diarization enabled
            job = client.speech_to_text_job.create_job(
                model="saaras:v3",
                language_code="hi-IN",
                mode="transcribe",
                with_diarization=True
            )

            job.upload_files(file_paths=[file_path])
            job.start()

            print(f"Waiting for job completion for {basename}...")
            job.wait_until_complete()

            job.download_outputs(output_dir=SARVAM_OUT_DIR)
            
            if not os.path.exists(json_file):
                print(f"Warning: expected JSON output {json_file} not found.")
                return

            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        diarized_data = data.get("diarized_transcript", {})
        
        # In some versions, diarized_transcript is a list, in others it is a dict with {"entries": [...]}
        entries = []
        if isinstance(diarized_data, list):
            entries = diarized_data
        elif isinstance(diarized_data, dict):
            entries = diarized_data.get("entries", [])

        if not entries:
            print("No diarized transcript entries found in JSON.")
            transcript = data.get("transcript", "")
            if transcript:
                print("Found standard transcript. Saving without diarization/slice.")
                txt_filename = os.path.join(OUTPUT_DIR, f"{file_prefix}_unknown.txt")
                with open(txt_filename, "w", encoding="utf-8") as f:
                    f.write(transcript)
            return

        MAX_DURATION = 60.0  # Target duration for concatenated single-speaker transcript

        # Collect all segments grouped by speaker
        from collections import defaultdict
        speaker_to_segments = defaultdict(list)

        for segment in entries:
            speaker = segment.get("speaker_id") or segment.get("speaker")
            start = float(segment.get("start_time_seconds") or segment.get("start_time") or 0)
            end = float(segment.get("end_time_seconds") or segment.get("end_time") or 0)
            text = segment.get("transcript", "")
            speaker_to_segments[speaker].append({
                "start": start,
                "end": end,
                "text": text,
                "duration": end - start
            })

        # Pick the speaker with the most total speaking time
        speaker_totals = {
            spk: sum(seg["duration"] for seg in segs)
            for spk, segs in speaker_to_segments.items()
        }
        dominant_speaker = max(speaker_totals, key=speaker_totals.get)

        # Concatenate dominant speaker's segments (in chronological order) up to ~60s
        selected_texts = []
        total_duration = 0.0
        for seg in speaker_to_segments[dominant_speaker]:
            if total_duration + seg["duration"] > MAX_DURATION and selected_texts:
                break  # Stop once we'd exceed 60s (but always include at least one)
            selected_texts.append(seg["text"])
            total_duration += seg["duration"]

        if selected_texts:
            combined_text = " ".join(selected_texts)
            txt_filename = os.path.join(OUTPUT_DIR, f"{file_prefix}_{dominant_speaker}.txt")
            with open(txt_filename, "w", encoding="utf-8") as f:
                f.write(combined_text)
            print(f"Saved transcript to {txt_filename} (Duration: {total_duration:.2f}s, Speaker: {dominant_speaker})")
            
            # Audio slicing is disabled since segments are non-contiguous and ffmpeg is not installed.
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

for f in audio_files:
    process_file(f)
