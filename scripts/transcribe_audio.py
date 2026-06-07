import os
import sys
import glob
import json
from dotenv import load_dotenv
from sarvamai import SarvamAI

sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
if not SARVAM_API_KEY:
    print("SARVAM_API_KEY not found in environment. Please set it in .env")
    exit(1)

client = SarvamAI(api_subscription_key=SARVAM_API_KEY)

ENG_DIR = r"c:\Users\aasth\Documents\Sarvam\videos\IndianEng"
OUTPUT_DIR = r"c:\Users\aasth\Documents\Sarvam\videos\IndianEng_transcripts"
os.makedirs(OUTPUT_DIR, exist_ok=True)

audio_files = []
for ext in ["*.wav", "*.m4a", "*.mp3"]:
    audio_files.extend(glob.glob(os.path.join(ENG_DIR, ext)))

print(f"Found {len(audio_files)} Indian English audio files to process.")

def process_file(file_path):
    print(f"Processing {file_path}")
    basename = os.path.basename(file_path)
    file_prefix = os.path.splitext(basename)[0]
    out_file = os.path.join(OUTPUT_DIR, f"{file_prefix}.txt")
    
    if os.path.exists(out_file):
        print(f"Transcript already exists for {basename}, skipping.")
        return
        
    try:
        # Use speech-to-text batch API for transcription
        job = client.speech_to_text_job.create_job(
            model="saaras:v3",
            language_code="en-IN",
            mode="transcribe",
            with_diarization=False
        )

        job.upload_files(file_paths=[file_path])
        job.start()

        print(f"Waiting for job completion for {basename}...")
        job.wait_until_complete()

        # Temporary download dir for this file
        tmp_dir = os.path.join(OUTPUT_DIR, "tmp_sarvam_json")
        os.makedirs(tmp_dir, exist_ok=True)
        job.download_outputs(output_dir=tmp_dir)
        
        json_file = os.path.join(tmp_dir, f"{basename}.json")
        if not os.path.exists(json_file):
            print(f"Warning: expected JSON output {json_file} not found.")
            return

        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # ASR output transcript format: could be a top-level `transcript` or similar.
        transcript = data.get("transcript", "")
        if not transcript and "diarized_transcript" in data:
            transcript = " ".join([segment.get("transcript", "") for segment in data.get("diarized_transcript")])
            
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(transcript)
        print(f"Exported transcript to {out_file}")
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

for f in audio_files:
    process_file(f)
