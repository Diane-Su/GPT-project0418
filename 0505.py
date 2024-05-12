import discord
import os
from openai import OpenAI, OpenAIError  
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
from PIL import Image
from io import BytesIO 
import io
import requests
import textwrap
import re

# OpenAI API 金鑰
openai_client = OpenAI(api_key="Your OpenAI Key!")

# client是跟discord連接，intents是要求機器人的權限
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# 創建一個列表來存儲訊息
message_log = []

responses = {}

# 載入字體
pdfmetrics.registerFont(TTFont('ChineseFont', 'C:/Users/scream/OneDrive/桌面/專題/jf-openhuninn-2.0.ttf'))

# 調用event函式庫
@client.event
# 當機器人完成啟動
async def on_ready():
    print(f"目前登入身份 --> {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("我要製作一份報告"):
        await message.channel.send("請問您想要做什麼樣的報告？請提供主題。")
        message_log.append(message.content)  # 儲存以便日後處理

    elif len(message_log) == 1 and not message.content.startswith('存檔'):
        report_topic = message.content
        supplemental_text = "請針對該主題，提出四個跟該主題有關的報告標題。"
        question_with_supplement = f"{report_topic}\n\n{supplemental_text}"
        
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4", 
                messages=[{"role": "user", "content": question_with_supplement}],
            )
            response_text = response.choices[0].message.content
            report_titles = response_text.split("\n")
            await message.channel.send(f"選擇的報告主題為：\n" + "\n".join(report_titles))

            response = openai_client.images.generate(
                model="dall-e-3",
                prompt=report_topic,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            image_url = response.data[0].url
            responses['image_url'] = image_url
            responses['report_titles'] = report_titles
            responses['report_topic'] = report_topic
            message_log.append(message.content)  # 更新日誌
        except OpenAIError as e:
            await message.channel.send(f"OpenAI 連接錯誤: {e}")

    elif len(message_log) == 2:
        selected_index = int(message.content.strip()) - 1
        selected_topic = responses['report_titles'][selected_index]
        await message.channel.send(f"你選擇的報告主題是：{selected_topic}。正在生成前言，請稍後......")
        
        try:
            summary_response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": f"生成關於'{selected_topic}'的前言"}],
            )
            summary = summary_response.choices[0].message.content
            await message.channel.send(f"生成的前言：\n{summary}")
            responses['summary'] = summary
            await message.channel.send("你要進行存檔嗎？請回覆‘是’或‘否’。")
            responses['save_request'] = True  # 標記為需要等待存檔確認
            message_log.append(message.content)  # 更新日誌
        except OpenAIError as e:
            await message.channel.send(f"OpenAI 連接錯誤: {e}")

    elif responses.get('save_request') and message.content == '是':
        # 使用者要存檔
        path = "C:/Users/scream/Downloads/"  # 設置默認保存路徑
        response_text = responses['summary']
        report_topic = responses['report_topic']
        image_url = responses['image_url']
        image_data = requests.get(image_url).content
        image = Image.open(BytesIO(image_data))
        temp_image_path = f"{path}temp_image.png"
        image.save(temp_image_path)
        generate_pdf(report_topic, response_text, temp_image_path, path)
        await message.channel.send("檔案已成功儲存!")
        await message.channel.send(file=discord.File(f"{path}response.pdf"))
        responses['save_request'] = False  # 重置保存請求狀態

# 生成 PDF 的函數
def generate_pdf(direction, content, image_path, path):
    lines = textwrap.wrap(content, width=50) # 根據頁面寬度進行換行
    # 設定行高
    line_height = 25
    # 計算文本總高度
    text_height = len(lines) * line_height
    # 計算頁面總高度
    page_height = text_height + 800
    
    # 創建 PDF 並設定頁面大小
    c = canvas.Canvas(f"{path}response.pdf", pagesize=(A4[0], page_height))
    # 設定使用的字體
    c.setFont("ChineseFont", 12)
    # 寫入 PDF 標題和摘要
    c.drawString(100, page_height - 50, "標題：")
    c.drawString(150, page_height - 50, direction)
    c.drawString(100, page_height - 80, "摘要：")
    
    # 設定寫入文本的起始位置
    text_x = 100
    text_y = page_height - 80 - line_height
    # 遍歷每行文本並寫入 PDF
    for line in lines:
        c.drawString(text_x, text_y, line)
        text_y -= line_height
    
    # 調整圖像大小
    image = Image.open(image_path)
    image_width, image_height = image.size
    max_image_width = A4[0] - 200
    max_image_height = page_height - 200 - text_height
    if image_width > max_image_width or image_height > max_image_height:
        ratio = min(max_image_width / image_width, max_image_height / image_height)
        image = image.resize((int(image_width * ratio), int(image_height * ratio)))
    # Draw image on PDF
    c.drawImage(image_path, 100, 100, width=image.size[0], height=image.size[1])

    # 保存 PDF 文件
    c.save()
    os.remove(image_path)

client.run("Your Discord Key!")