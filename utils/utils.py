import re
import os
from pytube import YouTube
import moviepy.editor as mp
from openai import OpenAI
import logging

def get_youtube_id(url):
    # Define the regex pattern for extracting the video ID
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    
    # Search for the pattern in the URL
    match = re.search(pattern, url)
    
    # If a match is found, return the video ID
    if match:
        return match.group(1)
    else:
        return None

def download_yt(url):
    yt = YouTube(url)
    unique_file_name = get_youtube_id(url)
    logging.info("Downloading ", unique_file_name)
    file_name = '/tmp/' + unique_file_name + '.mp4'
    # Select the best audio stream
    audio_stream = yt.streams.filter(only_audio=True).first()

    # Download the audio stream to a temporary file
    audio_stream.download(filename=file_name)
    logging.info("file downloaded")
    # Convert the downloaded file to MP3
    clip = mp.AudioFileClip(file_name)
    mp3_file = "/tmp/" + unique_file_name + ".mp3"
    clip.write_audiofile(mp3_file)

    logging.info("MP3 downloaded")

    # Remove the temporary MP4 file
    clip.close()
    return mp3_file
            

def transcript_yt(filepath):
    # Create OpenAI Connection
    client = OpenAI()
    client.api_key  = os.environ['OPENAI_API_KEY']
    audio_file= open(filepath, "rb")
    logging.info("transcripting")
    transcript = client.audio.transcriptions.create(
                model="whisper-1",

                file=audio_file,
                language="en",
                prompt="Can you interpret,explain, add a metaphor and summarize",
                response_format="text"
                )
    return transcript

# Example usage
# url = 'https://www.youtube.com/watch?v=5hMgUbmrENM'
# video_id = get_youtube_id(url)

# print(transcript_yt(download_yt(url)))

# print(f'The video ID is: {video_id}')