# qwen3-tts-flash
本文为您介绍语音合成-千问模型的输入与输出参数。

模型的使用方法请参见语音合成-千问。
请求体
非流式输出流式输出
PythonJavacurl
DashScope Python SDK中的SpeechSynthesizer接口已统一为MultiModalConversation，使用新接口只需替换名称即可，其他参数完全兼容。
 
# DashScope SDK 版本不低于 1.24.5
import os
import dashscope

# 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：https://dashscope-intl.aliyuncs.com/api/v1
dashscope.base_http_api_url = 'https://dashscope.aliyuncs.com/api/v1'

text = "那我来给大家推荐一款T恤，这款呢真的是超级好看，这个颜色呢很显气质，而且呢也是搭配的绝佳单品，大家可以闭眼入，真的是非常好看，对身材的包容性也很好，不管啥身材的宝宝呢，穿上去都是很好看的。推荐宝宝们下单哦。"
# SpeechSynthesizer接口使用方法：dashscope.audio.qwen_tts.SpeechSynthesizer.call(...)
response = dashscope.MultiModalConversation.call(
    # 如需使用指令控制功能，请将model替换为qwen3-tts-instruct-flash
    model="qwen3-tts-flash",
    # 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx"
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    text=text,
    voice="Cherry",
    # 如需使用指令控制功能，请取消下方注释，并将model替换为qwen3-tts-instruct-flash
    # instructions='语速较快，带有明显的上扬语调，适合介绍时尚产品。',
    # optimize_instructions=True,
    stream=True
)
for chunk in response:
    print(chunk)
实时播放Base64 音频的方法请参见：语音合成-千问。
model string （必选）

模型名称，详情请参见支持的模型。

text string （必选）

要合成的文本，支持多语种混合输入。千问-TTS模型最长输入为512 Token。其他模型最长输入为600字符。

voice string （必选）

使用的音色，参见支持的系统音色。

language_type string （可选）

指定合成音频的语种，默认为 Auto。

Auto：适用无法确定文本的语种或文本包含多种语言的场景，模型会自动为文本中的不同语言片段匹配各自的发音，但无法保证发音完全精准。

指定语种：适用于文本为单一语种的场景，此时指定为具体语种，能显著提升合成质量，效果通常优于 Auto。可选值包括：

Chinese

English

German

Italian

Portuguese

Spanish

Japanese

Korean

French

Russian

instructions string （可选）

设置指令，参见指令控制。

默认值：无默认值，不设置不生效。

长度限制：长度不得超过 1600 Token。

支持语言：仅支持中文和英文。

适用范围：该功能仅适用于千问3-TTS-Instruct-Flash-Realtime系列模型。

optimize_instructions boolean （可选）

是否对 instructions 进行优化，以提升语音合成的自然度和表现力。

默认值：false。

行为说明：当设置为 true 时，系统将对 instructions 的内容进行语义增强与重写，生成更适合语音合成的内部指令。

适用场景：推荐在追求高品质、精细化语音表达的场景下开启。

依赖关系：此参数依赖于 instructions 参数被设置。如果 instructions 为空，此参数不生效。

适用范围：该功能仅适用于千问3-TTS-Instruct-Flash系列模型。

stream boolean （可选）默认值为 false

是否流式输出回复。参数值：

模型生成完后返回音频的 URL。

边生成边输出 Base64 编码格式的音频数据。您需要实时地逐个读取这些片段以获得完整的结果。请参见：语音合成-千问。

该参数仅支持Python SDK。通过Java SDK实现流式输出请通过streamCall接口调用；通过HTTP实现流式输出请在Header中指定X-DashScope-SSE为enable。
返回对象（流式与非流式输出格式一致）
千问3-TTS-Flash千问-TTS
 
{
    "status_code": 200,
    "request_id": "5c63c65c-cad8-4bf4-959d-xxxxxxxxxxxx",
    "code": "",
    "message": "",
    "output": {
        "text": null,
        "finish_reason": "stop",
        "choices": null,
        "audio": {
            "data": "",
            "url": "http://dashscope-result-bj.oss-cn-beijing.aliyuncs.com/1d/ab/20251218/d2033070/39b6d8f2-c0db-4daa-9073-5d27bfb66b78.wav?Expires=1766113409&OSSAccessKeyId=LTAI5xxxxxxxxxxxx&Signature=NOrqxxxxxxxxxxxx%3D",
            "id": "audio_5c63c65c-cad8-4bf4-959d-xxxxxxxxxxxx",
            "expires_at": 1766113409
        }
    },
    "usage": {
        "input_tokens": 0,
        "output_tokens": 0,
        "characters": 195
    }
}
status_code integer

HTTP状态码。遵循 RFC 9110标准定义。例如：
• 200：请求成功，正常返回结果
• 400：客户端请求参数错误
• 401：未授权访问
• 404：资源未找到
• 500：服务器内部错误。





request_id string

本次请求的唯一标识。可用于定位和排查问题。

code string

请求失败时展示错误码（参见错误信息）。

message string

请求失败时展示错误信息（参见错误信息）。

output object

模型的输出。

属性

text string

始终为null，无需关注该参数。

choices string

始终为null，无需关注该参数。

finish_reason string

有两种情况：

正在生成时为"null"；

因模型输出自然结束，或触发输入参数中的stop条件而结束时为"stop"。

audio object

模型输出的音频信息。

属性

url string

模型输出的完整音频文件的URL，有效期24小时。

data string

流式输出时的Base64 音频数据。

id string

模型输出的音频信息对应的ID。

expires_at integer

url 将要过期的时间戳。

usage object

本次请求的 Token 或字符消耗信息。千问-TTS模型返回Token消耗信息，千问3-TTS-Flash模型返回字符消耗信息

属性

input_tokens_details object

输入文本的 Token消耗信息。仅千问-TTS模型返回该字段。

属性

text_tokens integer

输入文本的 Token 消耗量。

total_tokens integer

本次请求总共消耗的 Token 量。仅千问-TTS模型返回该字段。

output_tokens integer

输出音频的 Token 消耗量。对于千问3-TTS-Flash模型，该字段固定为0。

input_tokens integer

输入文本的 Token 消耗量。对于千问3-TTS-Flash模型，该字段固定为0。

output_tokens_details object

输出的 Token 消耗信息。仅千问-TTS模型返回该字段。

属性

audio_tokens integer

输出音频的 Token 消耗量。

text_tokens integer

输出文本的 Token 消耗量，当前固定为0。

characters integer

输入文本的字符数。仅千问3-TTS-Flash模型返回该字段。

request_id string

本次请求的 ID。