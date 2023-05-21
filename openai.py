import requests
import json
import os

headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer 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',
}


def aiimg(prompt, size, name):
    json_data = {
        'prompt': prompt,
        'n': 1,
        'size': size,
    }
    response = requests.post(
        'https://api.openai-proxy.com/v1/images/generations', headers=headers, json=json_data)
    res = json.loads(response.text)
    image_url = res['data'][0]['url']
    # return res['data'][0]['url']
    # print(response.text)
    image = requests.get(image_url).content
    # name=msg.replace(' ','')
    if not os.path.exists('img/'):
        os.mkdir('img/')
    with open('img//' + name + '.jpg', 'wb') as f:
        f.write(image)


def aichat(content):
    json_data = {
        'model': 'gpt-3.5-turbo',
        'messages': [
            {
                'role': 'user',
                'content': content,
            },
        ],
    }

    response = requests.post(
        'https://api.openai-proxy.com/v1/chat/completions', headers=headers, json=json_data)
    res = json.loads(response.text)
    return res['choices'][0]['message']['content']


if __name__ == '__main__':
    # 生成文本
    # print(aichat("假设你是贪吃蛇游戏中的贪吃蛇，你的内心想法是怎样的，用幽默的语气回答，10到20个字"))
    # 画图
    aiimg("卡通游戏风格的森林", "512x512", "沙漠")
