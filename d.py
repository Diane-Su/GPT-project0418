import discord  # 導入 Discord API 相關函式庫
import os  # 用於與作業系統進行互動的函式庫
from openai import OpenAI, OpenAIError  # 導入 OpenAI API 相關函式庫
from reportlab.lib.pagesizes import A4  # 導入用於設置 PDF 頁面大小的函式庫
from reportlab.pdfbase.ttfonts import TTFont  # 導入用於註冊 TrueType 字體的函式庫
from reportlab.pdfbase import pdfmetrics  # 導入用於處理 PDF 文本測量的函式庫
from reportlab.pdfgen import canvas  # 導入用於生成 PDF 的函式庫
from PIL import Image  # 導入用於處理圖像的函式庫
from io import BytesIO  # 導入用於處理二進制數據的函式庫
import io  # 導入用於處理 I/O 操作的函式庫
import requests  # 導入用於發送 HTTP 請求的函式庫
import textwrap  # 導入用於對文本進行格式化的函式庫
import re  # 導入用於正則表達式的函式庫

# 初始化 OpenAI 客戶端
openai_client = OpenAI(api_key="Your OpenAI Key!")

# 初始化 Discord 客戶端
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# 創建一個列表來存儲訊息
message_log = []

responses = {}

# 設置字體
pdfmetrics.registerFont(TTFont('ChineseFont', 'C:/Users/scream/OneDrive/桌面/專題/jf-openhuninn-2.0.ttf'))

# 調用event函式庫
@client.event
# 當機器人完成啟動
async def on_ready():
    print(f"目前登入身份 --> {client.user}")

@client.event  # 設定事件監聽器，監聽消息事件
async def on_message(message):
    if message.author == client.user:  # 若消息發送者是機器人自身，則忽略
        return

    if message.content.startswith("我要製作一份報告"):  # 若消息內容以指定字串開頭
        await message.channel.send("請問您想要做什麼樣的報告？請提供主題。")  # 回覆提問
        message_log.append(message.content)  # 儲存以便日後處理

    elif len(message_log) == 1 and not message.content.startswith('存檔'):  # 若日誌中有一條消息且不是存檔指令
        report_topic = message.content  # 提取報告主題
        supplemental_text = "請針對該主題，提出四個跟該主題有關的報告標題。"
        question_with_supplement = f"{report_topic}\n\n{supplemental_text}"  # 構建問題文本

        try:
            # 與 OpenAI 對話模型互動，生成報告標題
            response = openai_client.chat.completions.create(
                model="gpt-4", 
                messages=[{"role": "user", "content": question_with_supplement}],
            )
            response_text = response.choices[0].message.content
            report_titles = response_text.split("\n")  # 提取生成的報告標題
            await message.channel.send(f"選擇的報告主題為：\n" + "\n".join(report_titles))  # 回覆選擇的報告主題

            # 使用 DALL·E 模型生成與主題相關的圖像
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

    elif len(message_log) == 2:  # 若日誌中有兩條消息
        selected_index = int(message.content.strip()) - 1  # 提取所選報告標題的索引
        selected_topic = responses['report_titles'][selected_index]  # 提取所選報告主題
        await message.channel.send(f"你選擇的報告主題是：{selected_topic}。正在生成前言和實際應用案例，請稍後......")  # 回覆所選報告主題

        try:
            # 使用 GPT-4 生成報告前言
            summary_response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": f"生成關於'{selected_topic}'的前言"}],
            )
            summary = summary_response.choices[0].message.content
            await message.channel.send(f"前言：\n{summary}")  # 回覆生成的前言
            responses['summary'] = summary

            # 使用 GPT-4 生成報告實際應用案例
            applications_response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": f"生成關於'{selected_topic}'的實際應用案例"}],
            )
            applications = applications_response.choices[0].message.content
            await message.channel.send(f"實際應用案例：\n{applications}")  # 回覆生成的實際應用案例
            responses['applications'] = applications

            await message.channel.send("你要進行存檔嗎？請回覆‘是’或‘否’。")  # 提示是否要存檔
            responses['save_request'] = True  # 標記為需要等待存檔確認
            message_log.append(message.content)  # 更新日誌
        except OpenAIError as e:
            await message.channel.send(f"OpenAI 連接錯誤: {e}")

    elif responses.get('save_request') and message.content == '是':  # 若存在存檔請求且用戶確認要存檔
        # 使用者要存檔
        path = "C:/Users/scream/Downloads/"  # 設置默認保存路徑
        response_text = responses['summary']
        report_topic = responses['report_topic']
        image_url = responses['image_url']
        image_data = requests.get(image_url).content
        image = Image.open(BytesIO(image_data))
        temp_image_path = f"{path}temp_image.png"
        image.save(temp_image_path)  # 保存圖像至暫時路徑
        generate_pdf(report_topic, response_text, temp_image_path, path)  # 生成 PDF 檔案
        await message.channel.send("檔案已成功儲存!")  # 回覆檔案保存成功
        await message.channel.send(file=discord.File(f"{path}response.pdf"))  # 上傳 PDF 檔案
        responses['save_request'] = False  # 重置保存請求狀態

# 生成 PDF 的函數
def generate_pdf(direction, summary, applications, image_path, path):
    # 使用正則表達式分割内容，确保每個點都在新的一行
    summary_lines = re.split(r'(?=\d+\.)', summary.strip())  # 這會根據數字點（如1. 2.）分割前言文本
    applications_lines = re.split(r'(?=\d+\.)', applications.strip())  # 這會根據數字點（如1. 2.）分割實際應用案例文本
    # 設定行高
    line_height = 25
    # 計算文本總高度
    summary_height = len(summary_lines) * line_height
    applications_height = len(applications_lines) * line_height
    # 計算頁面總高度
    page_height = summary_height + applications_height + 1200

    # 創建 PDF 並設定頁面大小
    c = canvas.Canvas(f"{path}response.pdf", pagesize=(A4[0], page_height))
    # 設定使用的字體
    c.setFont("ChineseFont", 12)
    # 寫入 PDF 標題
    c.drawString(100, page_height - 50, "標題：")
    c.drawString(150, page_height - 50, direction)
    # 寫入 PDF 前言
    c.drawString(100, page_height - 80, "前言：")

    # 設定寫入前言文本的起始位置
    text_x = 100
    text_y = page_height - 80 - line_height
    # 遍歷每行前言文本並寫入 PDF
    for line in summary_lines:
        c.drawString(text_x, text_y, line)
        text_y -= line_height

    # 寫入 PDF 實際應用案例標題
    c.drawString(100, page_height - 80 - summary_height - 80, "實際應用案例：")

    # 設定寫入實際應用案例文本的起始位置
    text_x = 100
    text_y = page_height - 80 - summary_height - 80 - line_height
    # 遍歷每行實際應用案例文本並寫入 PDF
    for line in applications_lines:
        c.drawString(text_x, text_y, line)
        text_y -= line_height

    # 調整圖像大小
    image = Image.open(image_path)
    image_width, image_height = image.size
    max_image_width = A4[0] - 200
    max_image_height = page_height - 200 - summary_height - applications_height
    if image_width > max_image_width or image_height > max_image_height:
        ratio = min(max_image_width / image_width, max_image_height / image_height)
        image = image.resize((int(image_width * ratio), int(image_height * ratio)))
    # Draw image on PDF
    c.drawImage(image_path, 100, 100, width=image.size[0], height=image.size[1])

    # 保存 PDF 文件
    c.save()
    os.remove(image_path)

client.run("Your Discord Key!")