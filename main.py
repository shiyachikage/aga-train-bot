import discord
from discord.ext import commands
import pandas as pd
import datetime
import os
from flask import Flask
from threading import Thread
import holidays  # jholidayからholidaysに変更

# --- 1. Renderのスリープを防止するためのダミーサーバー ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_web_server():
    app.run(host='0.0.0.0', port=8080)

# --- 2. 判定・データ取得ロジック ---

def get_timetable_file():
    """今日が平日か休日(土日祝)かを判定して、読み込むべきCSV名を返す"""
    # 日本時間(JST)を取得
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    
    # 日本の祝日データを取得
    jp_holidays = holidays.Japan()
    
    # 土曜日(5)、日曜日(6)、または祝日かチェック
    if now.weekday() >= 5 or (now.date() in jp_holidays):
        return 'timetable_holiday.csv'
    else:
        return 'timetable_weekday.csv'

def get_next_trains(df, direction_filter, limit=2):
    """指定された方面の次の列車を抽出する"""
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    current_time = now.strftime("%H:%M")
    
    if direction_filter == "広島":
        target_df = df[df['direction'].isin(["広島", "呉"])]
    else:
        target_df = df[df['direction'] == "広"]
        
    return target_df[target_df['time'] >= current_time].sort_values('time').head(limit)

# --- 3. Discord Bot の本体 ---

intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.command(name="aga")
async def aga(ctx):
    try:
        file_name = get_timetable_file()
        df = pd.read_csv(file_name)
        
        day_type = "【休日ダイヤ】" if "holiday" in file_name else "【平日ダイヤ】"
        embed = discord.Embed(title=f"安芸阿賀駅 発車予定 {day_type}", color=discord.Color.blue())

        # 広島方面
        h_trains = get_next_trains(df, "広島")
        h_text = ""
        for _, row in h_trains.iterrows():
            display_type = f"**[{row['type']}]**" if "快速" in str(row['type']) else row['type']
            dest = "（呉止まり）" if row['direction'] == "呉" else ""
            h_text += f"⏰ {row['time']} | {display_type} {dest}\n"
        
        embed.add_field(name="🟥 広島方面", value=h_text or "本日の運行は終了しました", inline=False)

        # 広方面
        hi_trains = get_next_trains(df, "広")
        hi_text = ""
        for _, row in hi_trains.iterrows():
            hi_text += f"⏰ {row['time']} | 普通（広行）\n"
        
        embed.add_field(name="🟦 広方面", value=hi_text or "本日の運行は終了しました", inline=False)

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"エラーが発生しました: `{e}`")

# --- 4. 起動処理 ---

if __name__ == "__main__":
    t = Thread(target=run_web_server)
    t.start()
    
    token = os.getenv("DISCORD_TOKEN")
    bot.run(token)
