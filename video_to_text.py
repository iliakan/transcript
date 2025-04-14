import subprocess
import requests
import sys
import os
import hashlib
import pathlib
import json
import shutil

def get_video_dir(video_path):
    # Get the video filename without extension
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    # Create videos directory if it doesn't exist
    videos_dir = pathlib.Path("videos")
    videos_dir.mkdir(exist_ok=True)

    # Create a directory for this specific video
    video_dir = videos_dir / video_name
    video_dir.mkdir(exist_ok=True)

    # Create subdirectories
    (video_dir / "audio").mkdir(exist_ok=True)
    (video_dir / "transcripts").mkdir(exist_ok=True)
    (video_dir / "summaries").mkdir(exist_ok=True)

    return video_dir

def get_audio_path(video_path):
    # Get the video directory
    video_dir = get_video_dir(video_path)

    # Get the video filename without extension
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    return video_dir / "audio" / f"{video_name}.mp3"

def get_transcript_path(video_path):
    # Get the video directory
    video_dir = get_video_dir(video_path)

    # Get the video filename without extension
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    return video_dir / "transcripts" / f"{video_name}.txt"

def extract_audio(video_path):
    audio_path = get_audio_path(video_path)

    # Check if the cached audio file already exists
    if audio_path.exists():
        print(f"Using cached audio: {audio_path}")
        return str(audio_path)

    # Get video duration using ffprobe
    duration_cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path
    ]
    duration = float(subprocess.check_output(duration_cmd).decode().strip())
    print(f"Video duration: {duration:.2f} seconds")

    # Calculate target bitrate to keep file under 25MB
    # Formula: bitrate = (target_size_bytes * 8) / duration_seconds
    # 25MB = 25 * 1024 * 1024 bytes
    max_size_bytes = 25 * 1024 * 1024
    target_bitrate = int((max_size_bytes * 8) / duration * 0.95)  # 95% of max to be safe

    # Ensure minimum quality
    min_bitrate = 16000  # 16kbps minimum
    if target_bitrate < min_bitrate:
        target_bitrate = min_bitrate
        print(f"Warning: Long video may exceed 25MB size limit")

    # Cap at 64kbps for good quality
    max_bitrate = 64000  # 64kbps maximum
    if target_bitrate > max_bitrate:
        target_bitrate = max_bitrate

    bitrate_str = f"{target_bitrate // 1000}k"  # Convert to kbps format
    print(f"Using bitrate: {bitrate_str} to keep file under 25MB")

    # Extract audio with calculated bitrate
    print(f"Extracting audio to: {audio_path} (optimized for transcription)")
    subprocess.run([
        "ffmpeg",
        "-i", video_path,
        "-vn",                # No video
        "-ac", "1",          # Mono channel (Whisper works best with mono)
        "-ar", "24000",      # 24kHz sample rate (better for speech recognition)
        "-b:a", bitrate_str, # Calculated bitrate
        "-af", "highpass=f=50, lowpass=f=8000, afftdn",  # Audio filtering to reduce noise
        "-f", "mp3",         # MP3 format
        str(audio_path)
    ], check=True)
    return str(audio_path)

def transcribe(audio_path, video_path):
    # Get the transcript path for caching
    transcript_path = get_transcript_path(video_path)

    # Check if the cached transcript already exists
    if transcript_path.exists():
        print(f"Using cached transcript: {transcript_path}")
        with open(transcript_path, "r") as f:
            return f.read()

    print(f"Transcribing audio: {audio_path}")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)

    with open(audio_path, "rb") as f:
        response = requests.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": f},
            data={
                "model": "whisper-1",
                "response_format": "vtt"
            }
        )
    response.raise_for_status()

    # Get the response data as VTT format
    vtt_content = response.text

    # Cache the VTT content
    with open(transcript_path, "w") as f:
        f.write(vtt_content)

    # Return the VTT content
    return vtt_content

def make_readable(transcript_data):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    prompt = (
        "You are an expert at formatting video transcripts. "
        "I'm providing a transcript in VTT format. Make it more readable by: "
        "1. Converting it to clean HTML with proper headings, paragraphs, and emphasis "
        "2. Appending timestamps ONLY to each section header"
        "3. Adding proper paragraphs where appropriate "
        "4. Preserving all the original content and meaning "
        "\n\nVTT Transcript:\n"
    )

    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are an assistant that formats video transcripts into readable HTML."},
            {"role": "user", "content": prompt + transcript_data}
        ],
        "temperature": 0.1
    }

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=data
    )

    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]

    # Remove ```html and ``` wrapper if present
    if content.startswith("```html") and content.endswith("```"):
        content = content[7:-3].strip()
    elif content.startswith("```") and content.endswith("```"):
        content = content[3:-3].strip()

    return content

def generate_summary(transcript):
    """
    Generate a concise summary of the transcript in HTML format
    """
    print("Generating summary of the transcript...")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set.")
        sys.exit(1)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    prompt = (
        "You are an expert at summarizing video content. "
        "Create a concise summary of the following transcript that: "
        "1. Captures the main topics and key points "
        "2. Includes a brief overview at the top "
        "3. Lists the most important information in bullet points "
        "4. Is formatted in clean HTML with proper headings, sections, and styling "
        "5. Is well-structured and easy to scan "
        "6. Timestamps are appended to each section header only"
        "\n\nTranscript:\n"
    )

    data = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": "You are an assistant that summarizes video transcripts into concise HTML summaries."},
            {"role": "user", "content": prompt + transcript}
        ],
        "temperature": 0.3
    }

    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=data
    )

    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]

    # Remove ```html and ``` wrapper if present
    if content.startswith("```html") and content.endswith("```"):
        content = content[7:-3].strip()
    elif content.startswith("```") and content.endswith("```"):
        content = content[3:-3].strip()

    return content

def ensure_video_in_videos_dir(video_path):
    # Check if the video is already in the videos directory
    if not video_path.startswith("videos/") and not os.path.dirname(video_path) == "videos":
        # Get the video filename
        video_filename = os.path.basename(video_path)
        # New path in videos directory
        new_video_path = os.path.join("videos", video_filename)

        # Check if the video already exists in the videos directory
        if not os.path.exists(new_video_path):
            # Copy the video to the videos directory
            print(f"Moving video to videos directory: {new_video_path}")
            shutil.copy2(video_path, new_video_path)

        return new_video_path
    return video_path

def main(video_path):
    # Ensure the video is in the videos directory
    video_path = ensure_video_in_videos_dir(video_path)

    # Get the video directory
    video_dir = get_video_dir(video_path)
    video_name = os.path.splitext(os.path.basename(video_path))[0]

    audio_path = extract_audio(video_path)
    transcript = transcribe(audio_path, video_path)

    # Make the transcript readable and format in HTML
    print("Making transcript readable and formatting in HTML...")
    readable_html = make_readable(transcript)

    # Save the HTML version
    html_path = video_dir / "transcripts" / f"{video_name}.html"
    with open(html_path, "w") as f:
        f.write(readable_html)
    print(f"Readable HTML transcript saved to {html_path}")

    # Generate and save a summary of the transcript
    summary_html = generate_summary(transcript)

    # Save the summary HTML version
    summary_path = video_dir / "summaries" / f"{video_name}.html"
    with open(summary_path, "w") as f:
        f.write(summary_html)
    print(f"Summary saved to {summary_path}")

    # No need to clean up cached audio as it will be reused

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python video_to_text.py <video_file>")
        sys.exit(1)

    main(sys.argv[1])
