
import logging
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import yt_dlp
import os
import uuid


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Vimeo Audio Downloader")

# Pydantic model for request body
class VideoRequest(BaseModel):
    url: str

# Function to download audio
def download_vimeo_audio(vimeo_url, output_file):
    base_filename = output_file.replace('.mp3', '')
    logger.info(f"Preparing to download audio from: {vimeo_url}")

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
        # Important fixes
        'nocheckcertificate': True,
        'extract_flat': False,
        'no_warnings': False,
        'quiet': False,  # Keep some logs for debugging
        'http_headers': {  # Add headers to bypass 401
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://vimeo.com'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(vimeo_url, download=False)
            if not info:
                logger.error("Could not extract video information")
                raise Exception("Could not extract video information")
            logger.info(f"Video info extracted: {info.get('title', 'No Title')}")
            ydl.download([vimeo_url])

        final_file_path = base_filename + '.mp3'
        if not os.path.exists(final_file_path):
            logger.error("Audio file was not created after download")
            raise Exception("Audio file was not created after download")

        logger.info(f"Audio file created: {final_file_path}")
        return final_file_path
    except Exception as e:
        final_file_path = base_filename + '.mp3'
        if os.path.exists(final_file_path):
            os.remove(final_file_path)
        logger.error(f"Error during download: {e}")
        raise e



@app.post("/download-audio")
async def download_audio(video_request: VideoRequest, request: Request):
    logger.info(f"Incoming /download-audio request from {request.client.host}")
    logger.info(f"Payload: {video_request}")
    try:
        filename = f"audio_{uuid.uuid4().hex}.mp3"
        file_path = os.path.abspath(filename)
        logger.info(f"Generated filename: {file_path}")
        audio_file = download_vimeo_audio(video_request.url, file_path)

        if not os.path.exists(audio_file):
            logger.error("Failed to download audio file")
            return JSONResponse(content={"error": "Failed to download audio file"}, status_code=500)

        logger.info(f"Returning audio file: {audio_file}")
        return FileResponse(
            audio_file,
            media_type="audio/mpeg",
            filename="audio.mp3"
        )
    except Exception as e:
        logger.error(f"Exception in /download-audio: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)



@app.post("/validate-url")
async def validate_url(video_request: VideoRequest, request: Request):
    logger.info(f"Incoming /validate-url request from {request.client.host}")
    logger.info(f"Payload: {video_request}")
    try:
        ydl_opts = {
            'quiet': True,
            'nocheckcertificate': True,
            'extract_flat': True,
            'http_headers': {  # Same headers here
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept': '*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://vimeo.com'
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_request.url, download=False)
            if info:
                logger.info(f"URL validated. Title: {info.get('title', 'Unknown')}")
                return JSONResponse(content={
                    "valid": True,
                    "title": info.get('title', 'Unknown'),
                    "duration": info.get('duration', 'Unknown'),
                    "uploader": info.get('uploader', 'Unknown')
                })
            else:
                logger.error("Could not extract video information")
                return JSONResponse(content={"valid": False, "error": "Could not extract video information"}, status_code=400)
    except Exception as e:
        logger.error(f"Exception in /validate-url: {e}")
        return JSONResponse(content={"valid": False, "error": str(e)}, status_code=400)



@app.get("/health")
async def health_check(request: Request):
    logger.info(f"Health check from {request.client.host}")
    return {"status": "Service is up and running"}
