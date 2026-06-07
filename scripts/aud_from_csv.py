import csv
import os
import yt_dlp

def download_multiple_wavs(csv_file_path):
    # Check if the CSV file exists before proceeding
    if not os.path.exists(csv_file_path):
        print(f"Error: The file '{csv_file_path}' was not found.")
        return

    # Read the CSV file
    try:
        with open(csv_file_path, mode="r", encoding="utf-8") as file:
            # DictReader automatically uses the first row as keys (headers)
            reader = csv.DictReader(file)

            # Strip whitespace from headers just in case
            reader.fieldnames = [name.strip() for name in reader.fieldnames]

            # Convert to a list to easily count total rows for progress tracking
            rows = list(reader)

    except Exception as e:
        print(f"Failed to read CSV file: {e}")
        return

    # Generate the target IDs: H001, H002, ..., H030
    target_ids = [f"H{str(i).zfill(3)}" for i in range(1, 31)]
    
    # Filter rows to only include those in our target_ids
    filtered_rows = [row for row in rows if row.get("Aud_ID", "").strip() in target_ids]
    total_videos = len(filtered_rows)
    
    print(f"Found {total_videos} matching tracks (H001 - H030) to process.\n")

    # Loop through the filtered rows
    for index, row in enumerate(filtered_rows, start=1):
        # Extract data using exact column headers
        aud_id = row.get("Aud_ID", "").strip()
        video_url = row.get("URL", "").strip()

        # Skip row if URL is missing
        if not video_url:
            print(
                f"[{index}/{total_videos}] Skipping: Missing URL for ID {aud_id}."
            )
            continue

        # Use Aud_ID for the filename prefix if it exists; otherwise fall back to index
        prefix = aud_id if aud_id else str(index)

        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": f"{prefix}_%(title)s.%(ext)s",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav", # <-- Changed to wav here
                    # Removed "preferredquality" because wav is uncompressed/lossless
                }
            ],
            # Quiets the terminal output a bit, making your custom print statements easier to see
            "quiet": True,+
            "no_warnings": True,
        }

        try:
            print(f"[{index}/{total_videos}] Processing ID {prefix}: {video_url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            print(f"Finished downloading item {index}!")
        except Exception as e:
            print(f"Failed to process video {index} ({video_url}): {e}")


if __name__ == "__main__":
    # Path to your CSV file
    csv_file = "Youtube_audio_sources - Sheet2 - URLs_Youtube_audio_sources.csv"

    download_multiple_wavs(csv_file)