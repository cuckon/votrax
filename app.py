import os
import subprocess
import hashlib
import logging
from typing import Optional
from pathlib import Path

import requests

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


MAX_FILES = 500
MP3_FOLDER = Path('./audio_files')
REGION = os.getenv('AZ_REGION')
HEADERS = {
    'Ocp-Apim-Subscription-Key': os.getenv('AZ_TOKEN'),
    'Content-Type': 'application/ssml+xml',
    'X-Microsoft-OutputFormat': 'audio-16khz-128kbitrate-mono-mp3',
    'User-Agent': 'curl',
}

app = FastAPI()
app.mount('/static', StaticFiles(directory='static'), name='static')


def purge_files():
    """Keep the number of files within `MAX_FILES`."""
    audio_files = list(MP3_FOLDER.iterdir())
    n_audio_files = len(audio_files)
    if n_audio_files <= MAX_FILES:
        return

    audio_files.sort(key=os.path.getmtime, reverse=True)
    for i in range(MAX_FILES, n_audio_files):
        audio_files[i].unlink()


def play_mp3(path):
    subprocess.Popen(['mpg123', '-q', path])


def hashed_file_name(text:str):
    """Generate a proper mp3 file name by hashing the text."""
    return hashlib.md5(text.encode('utf-8')).hexdigest() + '.mp3'


def _azure_synthesis(text, name, style, gender):
    raw = f"""
    <speak xmlns="http://www.w3.org/2001/10/synthesis"
        xmlns:mstts="http://www.w3.org/2001/mstts"
        xmlns:emo="http://www.w3.org/2009/10/emotionml"
        version="1.0" xml:lang="en-US"
    >
        <voice xml:lang='zh-CN' xml:gender='{gender}' name='{name}'>
        <mstts:express-as style='{style}' >
            {text}
        </mstts:express-as>
        </voice>
    </speak>""".encode()

    # https://portal.azure.com/#@cuckonsgmail.onmicrosoft.com/resource/subscriptions/81e0d15b-786f-4a9a-a36c-818f32416dad/resourcegroups/Resource01/providers/Microsoft.CognitiveServices/accounts/Votrax/overview

    url = f'https://{REGION}.tts.speech.microsoft.com/cognitiveservices/v1'
    r = requests.post(url, data=raw, headers=HEADERS)
    return r.content

def text_to_mp3(text:str, name, style, gender) -> Path:
    """Convert text to mp3 file."""
    if not text:
        return

    if not MP3_FOLDER.exists():
        MP3_FOLDER.mkdir()

    path = MP3_FOLDER / hashed_file_name(text + name + style + gender)
    if path.exists():
        path.touch()
        return path


    result = _azure_synthesis(text, name, style, gender)

    path.write_bytes(result)
    purge_files()
    return path

    logging.error('Failed to convert text:' + result)


def make_html(payload):
    return f'''
    <head><title>机器猫广播站</title></head>
    <body>{payload}</body>
    '''


@app.get("/v1/{text}", response_class=HTMLResponse)
def speak(
        text: str,
        name: Optional[str]='zh-CN-XiaoxiaoNeural',
        style: Optional[str]='affectionate',
        gender: Optional[str]='Female',
    ):
    """Main entrance."""
    mp3_path = text_to_mp3(text, name, style, gender)
    if mp3_path:
        play_mp3(str(mp3_path))
    return make_html(f'已广播: "{text}"')


@app.get("/v1", response_class=HTMLResponse)
def help():
    """Get available parameters."""
    from json2html import json2html

    url = f'https://{REGION}.tts.speech.microsoft.com/cognitiveservices/voices/list'
    info = requests.get(url, headers=HEADERS).json()

    keys = ['ShortName', 'Gender', 'StyleList']
    simplified = [
        {k: i[k]}
        for i in info
        for k in keys if k in i
    ]
    html = json2html.convert(json=simplified)
    return make_html(html)