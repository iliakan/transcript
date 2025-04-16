# Video Transcription Tool

A command-line utility that converts video files to readable transcripts and summaries using OpenAI's APIs.

## Features

- Extracts optimized audio from video files using FFmpeg
- Transcribes audio to text using OpenAI's Whisper API
- Formats transcripts into readable HTML with proper structure
- Generates concise summaries of video content
- Handles batch processing of multiple videos
- Intelligently caches intermediate files to avoid redundant processing

## Requirements

- Python 3.6+
- FFmpeg installed and available in PATH
- OpenAI API key

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/iliakan/transcript.git
   cd transcript
   ```

2. Install required Python packages:
   ```bash
   pip install requests
   ```

3. Set your OpenAI API key as an environment variable:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

## Usage

### Process a single video

```bash
python video_to_text.py /path/to/your/video.mp4
```

### Process all videos in the 'video' directory

```bash
python video_to_text.py
```

## How It Works

1. **Audio Extraction**: The tool extracts audio from the video file, optimizing it for transcription with appropriate bitrate and filtering.

2. **Transcription**: The audio is sent to OpenAI's Whisper API for transcription.

3. **Formatting**: The raw transcript is processed by GPT-4o to create a well-formatted HTML version with proper paragraphs and sections.

4. **Summarization**: GPT-4o generates a concise summary of the video content in HTML format.

5. **Output**: Both the formatted transcript and summary are saved in the project directory structure.

## Output Directory Structure

The tool organizes processed files in a flat structure with separate directories for each file type:

```
├── audio/
│   └── video_name.mp3       # Extracted audio files
├── transcript/
│   ├── video_name.txt       # Raw VTT transcripts
│   └── video_name.html      # Formatted HTML transcripts
├── summary/
│   └── video_name.html      # HTML summaries
└── video/
    └── video_name.mp4       # Source video files
```

## Notes

- The tool optimizes audio extraction to keep files under 25MB (OpenAI's file size limit)
- All files (audio, transcripts, HTML, and summaries) are cached to avoid redundant processing
- Place your video files in the 'video' directory for batch processing
- Detailed error information is displayed for OpenAI API errors to help with troubleshooting

## License

[MIT License](LICENSE)
