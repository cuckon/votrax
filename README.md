VOTRAX
======
![](https://img.shields.io/badge/python-3.7%2B-blue) ![](https://img.shields.io/badge/fastapi-0.63.0-blue)

It speaks what you requests.

现在托管在我树莓派上，提供公共的语音播报服务。

## 亮点
- 语音文件缓存，减少对baidu语音合成服务的request
- 并发友好

## 运行
基于Azure的[文本转语音服务](https://azure.microsoft.com/zh-cn/services/cognitive-services/text-to-speech/).

```sh
sudo apt-get install mpg321
pip install -r requirements.txt

export AZ_REGION=<REGION>
export AZ_TOKEN=<SUBSCRIPTION KEY>
uvicorn app:app --reload --host 0.0.0.0
```