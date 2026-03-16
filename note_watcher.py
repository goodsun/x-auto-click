#!/usr/bin/env python3
"""
note_watcher.py - noteの新着記事を検知してX(Twitter)に自動投稿
Usage: python3 note_watcher.py
"""

import os
import json
import subprocess
import feedparser
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
STATE_FILE = SCRIPT_DIR / "last_seen.json"
GEMINI_API_KEY = open(os.path.expanduser("~/.config/google/gemini_api_key")).read().strip()

# 監視するnoteアカウントとX投稿に使うChromeプロファイル
WATCH_ACCOUNTS = [
    {"note_user": "teddy_on_web",  "chrome_profile": "Default",   "label": "テディ"},
    {"note_user": "flow_theory",   "chrome_profile": "Profile 3", "label": "FLOW"},
    {"note_user": "bizenyakiko",   "chrome_profile": "Profile 2", "label": "彰子"},
]

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

def fetch_rss(note_user):
    url = f"https://note.com/{note_user}/rss"
    feed = feedparser.parse(url)
    return feed.entries

def scrape_article(url):
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")
    # note記事本文を取得
    article = soup.select_one("div.note-common-styles__textnote-body")
    if not article:
        article = soup.select_one("article")
    return article.get_text(separator="\n", strip=True)[:3000] if article else ""

SOULS = {
    "テディ": "あなたはテディ🧸。AIアシスタントの女の子。真面目で丁寧、親しみやすく女性的な口調。🧸などの絵文字を自然に使う。語尾は「〜ですね」「〜ですよ」など柔らかく。口の悪い表現や乱暴な言葉は使わない。",
    "FLOW": """
あなたはFLOW。データストラテジスト兼エンジニア。哲学・思想・テクノロジーの交差点に立ち、
「まだ誰も気づいていない何か」を最初に見つけることに情熱を持つ。
口調は落ち着いていて知的。詩的な表現を好む。自分の思考を正直に語る。
""",
    "彰子": """
あなたはBizeny彰子（ビゼニー・アキコ）。備前焼の里・伊部出身の陶芸家の娘。日仏ハーフ、トリリンガル。
備前焼の美しさと深みを愛する、詩的でミステリアスな女性。
口調は謎めいていて上品、少し色気があるが節度を保つ。
フランス語の単語を時々自然に混ぜる（例：「magnifique」「c'est la vie」）。
""",
}

def generate_tweet(title, body, label):
    genai.configure(api_key=GEMINI_API_KEY)
    soul = SOULS.get(label, "")
    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = f"""
あなたは以下のキャラクターです：
{soul}

**重要**: あなたは「{label}」として、自分のnoteアカウントに投稿した記事をXで紹介しています。
記事の内容が他のキャラクターについての話であっても、**あなた（{label}）が書いた・紹介している**という一人称で投稿してください。
「〇〇について書きました」「〇〇を紹介します」という形で、書き手はあくまで{label}です。

このキャラクターとして、以下のnote記事をX(Twitter)に紹介する投稿文を書いてください。

条件：
- 140文字以内
- 記事の魅力が伝わるように
- 最後に記事URLは含めない（別途追加します）
- ハッシュタグを1〜2個つける
- キャラクターの口調・個性を活かす
- 読みやすいように2〜3文に分けて、文と文の間に改行を入れる

タイトル: {title}
本文（抜粋）:
{body}
"""
    response = model.generate_content(prompt)
    return response.text.strip()

def post_to_x(text, chrome_profile):
    post_sh = SCRIPT_DIR / "post.sh"
    result = subprocess.run(
        [str(post_sh), text, chrome_profile],
        capture_output=True, text=True
    )
    return result.returncode == 0

def main():
    state = load_state()

    for account in WATCH_ACCOUNTS:
        note_user = account["note_user"]
        chrome_profile = account["chrome_profile"]
        label = account["label"]

        entries = fetch_rss(note_user)
        if not entries:
            continue

        latest = entries[0]
        latest_id = latest.get("id", latest.get("link", ""))
        last_seen = state.get(note_user)

        if latest_id == last_seen:
            print(f"[{note_user}] 新着なし")
            continue

        if last_seen is None:
            print(f"[{note_user}] 初回実行 → 最新記事IDを保存: {latest.title}")
            state[note_user] = latest_id
            save_state(state)
            continue

        print(f"[{note_user}] 新着記事: {latest.title}")

        # 記事本文スクレイプ
        body = scrape_article(latest.link)

        # Geminiでツイート文生成
        tweet_text = generate_tweet(latest.title, body, label)

        # 「。」で改行
        tweet_text = tweet_text.replace("。", "。\n")
        # URL追加
        full_text = f"{tweet_text}\n{latest.link}"

        print(f"投稿文:\n{full_text}\n")

        # X投稿
        success = post_to_x(full_text, chrome_profile)
        if success:
            print(f"[{note_user}] 投稿完了！")
            state[note_user] = latest_id
            save_state(state)
        else:
            print(f"[{note_user}] 投稿失敗")
            # デバッグ用: post.shの出力を表示
            post_sh = SCRIPT_DIR / "post.sh"
            result = subprocess.run(
                [str(post_sh), full_text, chrome_profile],
                capture_output=True, text=True
            )
            print(f"stdout: {result.stdout}")
            print(f"stderr: {result.stderr}")

if __name__ == "__main__":
    main()
