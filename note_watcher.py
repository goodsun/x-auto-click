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

def generate_tweet(title, body, label):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = f"""
以下のnote記事を読んで、{label}としてX(Twitter)に投稿する文章を作ってください。

条件：
- 140文字以内
- 記事の魅力が伝わるように
- 最後に記事URLは含めない（別途追加します）
- ハッシュタグを1〜2個つける
- {label}らしい口調で（テディなら🧸をつかって親しみやすく、彰子なら備前焼・アートよりの雰囲気で）

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
