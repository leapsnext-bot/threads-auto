"""定時投稿スクリプト（Threads・X 共通）

投稿リストの上から順に、まだ投稿していないものを1本だけ投稿する。
投稿済みの記録は state/ のファイルに残す（同じ時間帯に2回投稿しないためのチェックにも使う）。

環境変数:
  PLATFORM       … threads（初期値）または x
  POSTS_FILE     … 投稿リスト（初期値 posts.txt）
  STATE_FILE     … 投稿記録（初期値 state/posted.tsv）
  THREADS_TOKEN  … Threadsの鍵
  X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_SECRET … Xの鍵
  DRY_RUN=1      … 実際には投稿せず、次に出る投稿を表示するだけ
  FORCE=1        … 同じ時間帯にすでに投稿していても投稿する（手動実行用）
"""
import hashlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, now_jst, summary, threads_publish, x_length, x_publish  # noqa: E402

PLATFORM = os.environ.get("PLATFORM", "threads")
POSTS_FILE = os.path.join(ROOT, os.environ.get("POSTS_FILE", "posts.txt"))
STATE_FILE = os.path.join(ROOT, os.environ.get("STATE_FILE", "state/posted.tsv"))
LOW_STOCK = 9  # 残りがこれ以下になったら知らせる
NAME = {"threads": "Threads", "x": "X"}[PLATFORM]


def load_posts():
    with open(POSTS_FILE, encoding="utf-8") as f:
        text = f.read()
    posts, current = [], None
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


def too_long(text):
    if PLATFORM == "x":
        return x_length(text) > 280, f"Xの数え方で{x_length(text)}（上限280、日本語は1文字＝2）"
    return len(text) > 500, f"{len(text)}文字（上限500）"


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


def keys_ready():
    if PLATFORM == "x":
        return all(os.environ.get(k) for k in ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET"))
    return bool(os.environ.get("THREADS_TOKEN"))


def main():
    dry = os.environ.get("DRY_RUN") == "1"
    force = os.environ.get("FORCE") == "1"
    now = now_jst()
    today = now.strftime("%Y-%m-%d")
    slot = slot_of(now)

    posts = load_posts()
    for i, p in enumerate(posts, 1):
        bad, detail = too_long(p)
        if bad:
            summary(f"❌ {i}番目の投稿が長すぎます：{detail}")
            sys.exit(1)

    state = load_state()
    done = {row[0] for row in state}
    if not force and not dry and any(r[1] == today and r[2] == slot for r in state):
        summary(f"⏭ 今日の{slot}の{NAME}投稿はもう済んでいるので、今回はお休みします。")
        return

    remaining = [p for p in posts if post_id(p) not in done]
    if not remaining:
        summary(f"⚠️ {NAME}の投稿ストックがなくなりました。投稿リストに追加してください。")
        sys.exit(1)

    text = remaining[0]
    number = posts.index(text) + 1
    if dry:
        summary(f"🧪 お試しモード（{NAME}には投稿しません）\n次に出るのは {number}番:\n\n{text}\n\n残り {len(remaining)}本")
        return

    if not keys_ready():
        if force:
            summary(f"❌ {NAME}の鍵がGitHubに登録されていません。")
            sys.exit(1)
        summary(f"⏸ {NAME}の鍵がまだ登録されていないので、投稿はお休みしています。")
        return

    media_id = threads_publish(os.environ["THREADS_TOKEN"], text) if PLATFORM == "threads" else x_publish(text)
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{post_id(text)}\t{today}\t{slot}\t{number}\t{media_id}\n")

    left = len(remaining) - 1
    summary(f"✅ {today} {slot}：{NAME}に{number}番を投稿しました。残り {left}本")
    if left <= LOW_STOCK:
        summary(f"⚠️ {NAME}のストックが残り{left}本です。そろそろ次の分を作りましょう。")


if __name__ == "__main__":
    main()
