import os
import subprocess
import hashlib
import logging
import asyncio
from functools import lru_cache
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


@lru_cache()
def get_voice_list():
    url = f'https://{REGION}.tts.speech.microsoft.com/cognitiveservices/voices/list'
    info = requests.get(url, headers=HEADERS).json()

    keys = ['ShortName', 'Gender', 'StyleList', 'LocalName']
    return [
        {k:i[k] for k in keys if k in i }
        for i in info if i['Locale'] == 'zh-CN'
    ]


def play_mp3(path):
    subprocess.Popen(['mpg123', '-q', path])


def hashed_file_name(text:str):
    """Generate a proper mp3 file name by hashing the text."""
    return hashlib.md5(text.encode('utf-8')).hexdigest() + '.mp3'


def _get_gender_by_name(name):
    for i in get_voice_list():
        if i['ShortName'] == name:
            return i['Gender']
    return 'Female'


def _azure_synthesis(text, name, style):
    voice_list = get_voice_list()
    gender = _get_gender_by_name(name)
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


async def text_to_mp3(text:str, name, style) -> Path:
    """Convert text to mp3 file."""
    if not text:
        return

    if not MP3_FOLDER.exists():
        MP3_FOLDER.mkdir()

    path = MP3_FOLDER / hashed_file_name(text + name + style)
    if path.exists():
        path.touch()
        return path

    result = _azure_synthesis(text, name, style)

    path.write_bytes(result)
    purge_files()
    return path

    logging.error('Failed to convert text:' + result)


async def make_html(payload):
    return f'''
    <head><title>机器猫广播站</title></head>
    <body>
        <div>
            {payload}
        </div>
        <hr>
        <div>
            🤗给机器猫转账，换更大的喇叭:<br><br>
            <img src="/static/qrcode.png" width="160" height="160">
        </div>

    </body>
    '''


async def convert_and_play(text, name, style):
    mp3_path = await text_to_mp3(text, name, style)
    if mp3_path:
        play_mp3(str(mp3_path))
    return mp3_path


@app.get('/v1/{text}', response_class=HTMLResponse)
async def speak(
        text: str,
        name: Optional[str]='zh-CN-XiaoxiaoNeural',
        style: Optional[str]='affectionate',
    ):
    """Main entrance."""
    res = await asyncio.gather(
        convert_and_play(text, name, style),
        make_html(f'🔊已广播: "<B>{text}</B>"'),
    )

    return res[1]



@app.get('/v1')
async def get_list_api():
    """Get available parameters."""
    return get_voice_list()


@app.get('/list', response_class=HTMLResponse)
async def get_list():
    """Get available parameters."""
    from json2html import json2html
    simplified = get_voice_list()

    html = json2html.convert(json=simplified)
    return await make_html(html)


@app.get('/', response_class=HTMLResponse)
async def help():
    """Get available parameters."""
    html = '''
    <h1>机器猫广播站</h1>
    <p>v1.0.1 2021.07.04
    <div><img src="/static/speaker.jpg"></div>
    <p>任意浏览器直接访问网址即可广播文字。可用于强提醒、广播找人等情景。
    <p>可用范围为所有内网的设备，比如💻电脑、📱手机、👩‍💻iPad。
    <p>目前喇叭的物理实体位于: 杭州一期B6F-B45。
    <p>⚠️<b>广播源暂时不设限，半匿名（必要时后台可跟踪）。请遵纪守法，勿广播不该广播的内容。</b>
    <hr>
    <h2>使用范例</h2>
    <p><a href="javascript:void(0)">http://10.240.154.195:8000/v1/周杰伦看一眼泡泡</a><br>
    🔊播放"周杰伦看一眼泡泡"
    <p><a href="javascript:void(0)">http://10.240.154.195:8000/v1/周杰伦看一眼泡泡?name=zh-CN-YunyeNeural</a><br>
    🔊播放"周杰伦看一眼泡泡"，使用“云野”的声音。
    <p><a href="javascript:void(0)">http://10.240.154.195:8000/v1/周杰伦看一眼泡泡?style=angry</a><br>
    🔊播放"周杰伦看一眼泡泡"，使用生气的语调。
    <p><a href="javascript:void(0)">http://10.240.154.195:8000/v1/周杰伦看一眼泡泡?name=zh-CN-YunyeNeural&style=angry</a><br>
    🔊播放"周杰伦看一眼泡泡"，使用“云野”的声音，配合生气的语调。
    <h2>可用声音和语调参考</h2>
    <p>在<a href="/list">此页面</a>查看列表。
    <p>在<a href="https://azure.microsoft.com/zh-cn/services/cognitive-services/text-to-speech/">微软 Azure官方</a>
    可试听.
    '''
    return await make_html(html)
