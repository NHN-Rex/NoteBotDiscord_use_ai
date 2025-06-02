from discord.ext import commands
import discord
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from io import BytesIO
from flask import Flask
from threading import Thread
import json, os, sys, re
import gdown
import pandas as pd
from thongke import generate_chart_pay_by_month, generate_chart_debt
import name


project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

#để model trên driver rồi tải về giải nén ra vào thư mục models
import gdown
import os
import zipfile

MODEL_ZIP_PATH = "models/final_model1.zip"
MODEL_DIR = "models/final_model1"
FILE_ID = "1g52cp41_de9yhUblXu3LM164cVzg22cB"
URL = f"https://drive.google.com/uc?id={FILE_ID}"

def download_model_zip():
    if not os.path.exists(MODEL_DIR):
        if not os.path.exists("models"):
            os.makedirs("models")
        print("Đang tải model zip bằng gdown...")
        gdown.download(URL, MODEL_ZIP_PATH, quiet=False)
        print("Tải xong, bắt đầu giải nén...")
        with zipfile.ZipFile(MODEL_ZIP_PATH, 'r') as zip_ref:
            zip_ref.extractall("models/")
        print("Giải nén hoàn thành.")
        os.remove(MODEL_ZIP_PATH)
    else:
        print("Model đã tồn tại, không cần tải lại.")

download_model_zip()
print("📦 Danh sách file trong models/:", os.listdir("models"))
print("📦 Danh sách file trong models/final_model1:")
print(os.listdir("models/final_model1"))

from slang_handle import handle_message, replace_slang_with_amount
from final_core import extract_entities

# Load slang mapping
try:
    with open("slang_mapping.json", "r", encoding="utf-8") as f:
        slang_amount_mapping = json.load(f)
except:
    slang_amount_mapping = {}



# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# sử dụng trên render
# Lấy nội dung JSON từ biến môi trường
credentials_info = os.getenv("GOOGLE_CREDENTIALS_JSON")
# Parse string JSON thành dict
credentials_dict = json.loads(credentials_info)
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client_gs = gspread.authorize(creds)


# sử dụng local
# creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
# client_gs = gspread.authorize(creds)


sheet = client_gs.open("chi_tieu_on_dinh").sheet1

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Web server keep-alive (nếu bạn chạy trên replit hoặc cần)
app = Flask('')

@app.route('/')
def home():
    return "Bot đang chạy ngon lành!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Hàm xử lý AI message
def process_user_message(message):
    processed_message = replace_slang_with_amount(message, slang_amount_mapping)
    result = extract_entities(processed_message)
    return result

# Bot events
@bot.event
async def on_ready():
    print(f"✅ Bot đã đăng nhập thành {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Nếu là command thì bỏ qua phần ghi chi tiêu, cho bot.process_commands xử lý
    if message.content.startswith('!'):
        await bot.process_commands(message)
        return
    
    response = handle_message(message.content)
    if response:
        await message.reply(response)

    text = message.content
    text = replace_slang_with_amount(text, slang_amount_mapping)

    try:
        data = process_user_message(text)
        print(type(data), data)
        if data['amount'] == 0:
            await message.reply("Không nhận diện được số tiền.")
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        username = {"harmonious_fox_17849": "Nghĩa",
            "doufang_8": "Phương",
            "ann_nguyen123": "Ngân"}
        
        # know_names = ["Ngân", "Phương", "Đạt", "Nhi", "Nghĩa"]
        if(data['recipients']=='cả nhóm' or data["recipients"]=="mn"):
            data['recipients'] = 'Mọi Người'

        if data['payer'].title() in name.know_names:
            payer = data["payer"].title()
        else:
            user = username.get(message.author.name, message.author.name)
            payer = user
        sheet.append_row([now, data['spending_category'], data['amount'], payer, data['recipients'].title(), ""])

        await message.reply(f"✅ Đã ghi chi tiêu: {data}.\nXem file google sheet [TẠI ĐÂY](https://docs.google.com/spreadsheets/d/1HtiGGXWZ6II9X_L3BxUh60e13isLuOhWL6NR1wcwvVk/edit?gid=0#gid=0)")

    except Exception as e:
        await message.reply(f"❌ Lỗi khi ghi dữ liệu: {e}")

# Bot command gửi biểu đồ
@bot.command()
async def thongkechi(ctx, time=None):
    data = sheet.get_all_values()
    chart_pay = generate_chart_pay_by_month(data, time)
    if not chart_pay:
        await ctx.reply(f"Không có dữ liệu chi tiêu trong tháng {time}.")
        return
    if time is None:
        await ctx.reply(f"📊 Không nhận được thời gian cụ thể nên thống kê toàn bộ dữ liệu chi tiêu: ", file=discord.File(chart_pay, 'chart.png'))
    else: await ctx.reply(f"📊 Thống kê chi tiêu tháng {time}:", file=discord.File(chart_pay, 'chart.png'))

@bot.command()
async def thongkeno(ctx):
    # user = ctx.author.name
    user = name.username.get(name, name)
    data = sheet.get_all_values()
    time = datetime.now().strftime("%d/%m/%Y")
    chart_debt = generate_chart_debt(user,data)
    if not chart_debt:
        await ctx.reply(f"{user} Không có dữ liệu.")
        return
    await ctx.reply(f"📊 Thống kê nợ của {user} đến tháng {time}:", file=discord.File(chart_debt, 'chart.png'))
# Chạy bot và web server
keep_alive()
bot.run(os.getenv('NoteBotDiscordToken'))
