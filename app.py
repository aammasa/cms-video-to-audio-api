from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import yt_dlp
import os
import uuid

app = FastAPI(title="Vimeo Audio Downloader")

# Pydantic model for request body
class VideoRequest(BaseModel):
    url: str

# Function to download audio
def download_vimeo_audio(vimeo_url, output_file):
    # Remove .mp3 extension from output_file since yt-dlp will add it
    base_filename = output_file.replace('.mp3', '')
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': base_filename,
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }
        ],
        'quiet': False,  # Enable verbose output for debugging
        'nocheckcertificate': True,  # Disable SSL certificate verification
        'extract_flat': False,
        'no_warnings': False,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First, try to extract info to validate the URL
            info = ydl.extract_info(vimeo_url, download=False)
            if not info:
                raise Exception("Could not extract video information")
            
            # Then download the audio
            ydl.download([vimeo_url])
            
        # Check if the file was actually created (with .mp3 extension)
        final_file_path = base_filename + '.mp3'
        if not os.path.exists(final_file_path):
            raise Exception("Audio file was not created after download")
            
        return final_file_path
    except Exception as e:
        # Clean up any partial files
        final_file_path = base_filename + '.mp3'
        if os.path.exists(final_file_path):
            os.remove(final_file_path)
        raise e

@app.post("/download-audio")
def download_audio(video_request: VideoRequest):
    try:
        # Generate unique filename with absolute path
        filename = f"audio_{uuid.uuid4().hex}.mp3"
        file_path = os.path.abspath(filename)
        
        # Download and convert
        audio_file = download_vimeo_audio(video_request.url, file_path)
        
        # Check if file exists before returning
        if not os.path.exists(audio_file):
            return JSONResponse(content={"error": "Failed to download audio file"}, status_code=500)
        
        # Return as file download
        return FileResponse(
            audio_file,
            media_type="audio/mpeg",
            filename="audio.mp3"
        )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/validate-url")
def validate_url(video_request: VideoRequest):
    """Test endpoint to validate if a Vimeo URL can be processed"""
    try:
        ydl_opts = {
            'quiet': True,
            'nocheckcertificate': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_request.url, download=False)
            if info:
                return JSONResponse(content={
                    "valid": True,
                    "title": info.get('title', 'Unknown'),
                    "duration": info.get('duration', 'Unknown'),
                    "uploader": info.get('uploader', 'Unknown')
                })
            else:
                return JSONResponse(content={"valid": False, "error": "Could not extract video information"}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"valid": False, "error": str(e)}, status_code=400)


@app.get("/health")
def health_check():
    return {"status": "Service is up and running"}
