import os
import subprocess
import hashlib
import logging
from pathlib import Path

from aip import AipSpeech
from typing import Optional

from fastapi import FastAPI


MAX_FILES = 500
MP3_FOLDER = Path('./audio_files')

app = FastAPI()
client = AipSpeech(
    os.getenv('APP_ID'), os.getenv('APP_KEY'), os.getenv('APP_SECRET')
)


def purge_files():
    audio_files = list(MP3_FOLDER.iterdir())
    n_audio_files = len(audio_files)
    if n_audio_files <= MAX_FILES:
        return

    audio_files.sort(key=os.path.getmtime, reverse=True)
    for i in range(MAX_FILES, n_audio_files):
        audio_files[i].unlink()


def play_mp3(path):
    subprocess.Popen(['mpg123', '-q', path])


def file_name(text:str):
    return hashlib.md5(text.encode('utf-8')).hexdigest() + '.mp3'


def text_to_mp3(text:str) -> Path:
    if not text:
        return

    if not MP3_FOLDER.exists():
        MP3_FOLDER.mkdir()

    path = MP3_FOLDER / file_name(text)
    if path.exists():
        path.touch()
        return path

    result  = client.synthesis(text, 'zh', 1, {'vol': 5})

    if not isinstance(result, dict):
        path.write_bytes(result)
        purge_files()
        return path

    logging.error('Failed to convert text:' + result)


@app.get("/v1/{text}")
def speak(text: str):
    if not text:
        return

    mp3_path = text_to_mp3(text)
    if mp3_path:
        play_mp3(str(mp3_path))
