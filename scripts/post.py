"""Threads 自動投稿スクリプト

posts.txt の上から順に、まだ投稿していないものを1本だけ Threads に投稿する。
投稿済みの記録は state/posted.tsv に残す（同じ時間帯に2回投稿しないためのチェックにも使う）。

環境変数:
  THREADS_TOKEN  … Threads の鍵（長期アクセストークン）
  DRY_RUN=1      … 実際には投稿せず、次に出る投稿を表示するだけ
  FORCE=1        … 同じ時間帯にすでに投稿していても投稿する（手動実行用）
"""
import hashlib
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_FILE = os.path.join(ROOT, "posts.txt")
STATE_FILE = os.path.join(ROOT, "state", "posted.tsv")
API = "https://graph.threads.net/v1.0"
JST = timezone(timedelta(hours=9))
MAX_LEN = 500
LOW_STOCK = 9  # 残りがこれ以下になったら知らせる


def load_posts():
    with open(POSTS_FILE, encoding="utf-8") as f:
        text = f.read()
    posts = []
    current = None
    for line in text.splitlines():
        if re.match(r"^【\d+】", line.strip()):
            if current is not None:
                posts.append("\n".join(current).strip())
            current = []
        elif current is not None:
            current.append(line)
    if current is not None:
        posts.append("\n".join(current).strip())
    return [p for p in posts if p]


def post_id(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def load_state():
    rows = []
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 3:
                    rows.append(parts)
    return rows


def slot_of(now):
    h = now.hour
    if 5 <= h < 10:
        return "朝"
    if 10 <= h < 16:
        return "昼"
    if 16 <= h < 24:
        return "夜"
    return "深夜"


def summary(msg):
    print(msg)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")


def publish(token, text):
    r = requests.post(
        f"{API}/me/threads",
        data={"media_type": "TEXT", "text": text, "access_token": token},
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"下書きの作成に失敗: {r.status_code} {r.text}")
    creation_id = r.json()["id"]
    time.sleep(5)  # Threads側の準備待ち
    for attempt in range(3):
        r = requests.post(
            f"{API}/me/threads_publish",
            data={"creation_id": creation_id, "access_token": token},
            timeout=60,
        )
        if r.status_code == 200:
            return r.json()["id"]
        time.sleep(10)
    raise RuntimeError(f"公開に失敗: {r.status_code} {r.text}")


def main():
    dry = os.environ.get("DRY_RUN") == "1"
    force = os.environ.get("FORCE") == "1"
    now = datetime.now(JST)
    today = now.strftime("%Y-%m-%d")
    slot = slot_of(now)

    posts = load_posts()
    for i, p in enumerate(posts, 1):
        if len(p) > MAX_LEN:
            summary(f"❌ {i}番目の投稿が{len(p)}文字で、上限{MAX_LEN}文字を超えています。")
            sys.exit(1)

    state = load_state()
    done = {row[0] for row in state}
    if not force and not dry and any(r[1] == today and r[2] == slot for r in state):
        summary(f"⏭ 今日の{slot}の投稿はもう済んでいるので、今回はお休みします。")
        return

    remaining = [p for p in posts if post_id(p) not in done]
    if not remaining:
        summary("⚠️ 投稿のストックがなくなりました。posts.txt に投稿を追加してください。")
        sys.exit(1)

    text = remaining[0]
    number = posts.index(text) + 1
    if dry:
        summary(f"🧪 お試しモード（投稿はしません）\n次に出るのは {number}番:\n\n{text}\n\n残り {len(remaining)}本")
        return

    token = os.environ.get("THREADS_TOKEN")
    if not token:
        summary("❌ THREADS_TOKEN（Threadsの鍵）が登録されていません。")
        sys.exit(1)

    media_id = publish(token, text)
    with open(STATE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{post_id(text)}\t{today}\t{slot}\t{number}\t{media_id}\n")

    left = len(remaining) - 1
    summary(f"✅ {today} {slot}：{number}番を投稿しました。残り {left}本")
    if left <= LOW_STOCK:
        summary(f"⚠️ ストックが残り{left}本です。そろそろ次の分を作りましょう。")


if __name__ == "__main__":
    main()
