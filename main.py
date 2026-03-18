import discord
from discord.ext import commands
import pandas as pd
import datetime
import os
from flask import Flask
from threading import Thread
import jholiday  # 日本の祝日判定用

# --- 1. Renderのスリープを防止するためのダミーサーバー ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run_web_server():
    # Renderは通常8080ポートを使用します
    app.run(host='0.0.0.0', port=8080)

# --- 2. 判定・データ取得ロジック ---

def get_timetable_file():
    """今日が平日か休日(土日祝)かを判定して、読み込むべきCSV名を返す"""
    # 日本時間(JST)を取得
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    
    # 土曜日(5)、日曜日(6)、または祝日かチェック
    if now.weekday() >= 5 or jholiday.is_holiday(now.date()):
        return 'timetable_holiday.csv'
    else:
        return 'timetable_weekday.csv'

def get_next_trains(df, direction_filter, limit=2):
    """指定された方面の次の列車を抽出する"""
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))
    current_time = now.strftime("%H:%M")
    
    # 方面でフィルタリング
    if direction_filter == "広島":
        # 広島行きと、特殊な「呉行き」の両方を対象にする
        target_df = df[df['direction'].isin(["広島", "呉"])]
    else:
        # 広方面
        target_df = df[df['direction'] == "広"]
        
    # 現在時刻以降のものを取得して昇順にソートし、指定件数(limit)だけ返す
    return target_df[target_df['time'] >= current_time].sort_values('time').head(limit)

# --- 3. Discord Bot の本体 ---

intents = discord.Intents.default()
intents.message_content = True  # コマンドを読み取るために必要
bot = commands.Bot(command_prefix='/', intents=intents)

@bot.command(name="aga")
async def aga(ctx):
    try:
        # 適切なCSVを選択して読み込む
        file_name = get_timetable_file()
        df = pd.read_csv(file_name)
        
        # タイトルに今日が平日か休日かを表示
        day_type = "【休日ダイヤ】" if "holiday" in file_name else "【平日ダイヤ】"
        embed = discord.Embed(title=f"安芸阿賀駅 発車予定 {day_type}", color=discord.Color.blue())

        # --- 広島方面の処理 ---
        h_trains = get_next_trains(df, "広島")
        h_text = ""
        for _, row in h_trains.iterrows():
            # 快速(通勤ライナー、安芸路ライナー、シティライナー等)を太字にする
            display_type = f"**[{row['type']}]**" if "快速" in str(row['type']) else row['type']
            # 呉行きの場合は注釈をいれる
            dest = "（呉止まり）" if row['direction'] == "呉" else ""
            h_text += f"⏰ {row['time']} | {display_type} {dest}\n"
        
        embed.add_field(name="🟥 広島方面", value=h_text or "本日の運行は終了しました", inline=False)

        # --- 広方面の処理 ---
        hi_trains = get_next_trains(df, "広")
        hi_text = ""
        for _, row in hi_trains.iterrows():
            # 広方面は一律「普通（広行）」として表示
            hi_text += f"⏰ {row['time']} | 普通（広行）\n"
        
        embed.add_field(name="🟦 広方面", value=hi_text or "本日の運行は終了しました", inline=False)

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"エラーが発生しました: コードまたはCSVを確認してください。\n`{e}`")

# --- 4. 起動処理 ---

if __name__ == "__main__":
    # Webサーバーを別スレッドで開始
    t = Thread(target=run_web_server)
    t.start()
    
    # Botの起動 (トークンはRenderの環境変数から取得することを推奨)
    # 直接書く場合は "TOKEN" を書き換えてください
    token = os.getenv("DISCORD_TOKEN")
    bot.run(token)