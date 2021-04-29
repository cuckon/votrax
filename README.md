VOTRAX
======
![](https://img.shields.io/badge/python-3.7%2B-blue) ![](https://img.shields.io/badge/fastapi-0.63.0-blue)

It speaks what you requests.

现在托管在我树莓派上，提供公共的语音播报服务。

## 亮点
- 语音文件缓存，减少对baidu语音合成服务的request
- 并发友好

## 运行
需要提前创建百度语音合成应用。文档：https://ai.baidu.com/ai-doc/SPEECH/zk4nlz99s

```sh
sudo apt-get install mpg321
pip install -r requirements.txt

export APP_ID=your-app-id
export APP_KEY=app-key
export APP_SECRET=secret
uvicorn app:app --reload
```