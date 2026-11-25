"""週1回の画像カード投稿（Threads）

1. make    … この1週間の自分の投稿から、いちばん反応が良かったものを選び、文字入りカード画像を作る
2. publish … 作った画像をThreadsに投稿する（画像はGitHubに保存したものを公開URLで渡す）

反応の数（いいね・返信・再投稿・表示数）が取れないときは、いちばん新しい投稿を使う。
環境変数: THREADS_TOKEN, DRY_RUN=1, IMAGE_BASE_URL（画像の置き場所。未指定ならGitHubの公開URL）
"""
import glob
import json
import os
import re
import sys
from datetime import timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import ROOT, now_jst, summary, threads_get, threads_publish  # noqa: E402

PENDING = os.path.join(ROOT, "state", "image_pending.json")
DONE = os.path.join(ROOT, "state", "image_posted.tsv")
IMG_DIR = os.path.join(ROOT, "images")

W, H = 1080, 1350
NAVY_TOP, NAVY_BOTTOM = (12, 20, 48), (30, 45, 94)
GOLD = (214, 178, 102)
WHITE = (248, 246, 240)

CAPTIONS = [
    "今週いちばん反応をもらった言葉を、画像にしました。\nしんどい日に見返せるように、保存しておいてもらえたら嬉しいです。",
    "今週たくさん反応をもらった投稿を、1枚にまとめました。\n誰かの背中を押せたら嬉しいです。",
    "今週の言葉。\n必要な人に届きますように。",
]


def font(size, weight="Bold"):
    cands = glob.glob(f"/usr/share/fonts/**/NotoSansCJK-{weight}.ttc", recursive=True) + \
        glob.glob("/usr/share/fonts/**/NotoSansCJK*.ttc", recursive=True)
    from PIL import ImageFont
    return ImageFont.truetype(cands[0], size, index=0)  # index 0 = 日本語


NO_START = set("、。，．・：；？！ー」』）】〉》ぁぃぅぇぉっゃゅょァィゥェォッャュョ…")


def wrap(draw, text, fnt, max_w):
    lines = []
    for para in text.split("\n"):
        if not para.strip():
            lines.append("")
            continue
        cur = ""
        for ch in para:
            if draw.textlength(cur + ch, font=fnt) <= max_w or not cur:
                cur += ch
            elif ch in NO_START:  # 句読点などを行頭に来させない
                cur += ch
            else:
                lines.append(cur)
                cur = ch
        lines.append(cur)
    while lines and not lines[-1]:
        lines.pop()
    return lines


def card_text(text):
    body = "\n".join(l for l in text.strip().split("\n") if not l.strip().startswith("#"))
    body = re.sub(r"https?://\S+", "", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    return body


def make_card(text, path):
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):  # 縦グラデーション
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(NAVY_TOP, NAVY_BOTTOM)))
    d.rectangle([40, 40, W - 40, H - 40], outline=GOLD, width=3)
    d.rectangle([54, 54, W - 54, H - 54], outline=(120, 100, 60), width=1)

    head = font(34, "Medium")
    label = "LEAPS KINGDOM."
    d.text(((W - d.textlength(label, font=head)) / 2, 110), label, font=head, fill=GOLD)
    d.line([(W / 2 - 60, 170), (W / 2 + 60, 170)], fill=GOLD, width=2)

    body = card_text(text)
    top, bottom, max_w = 230, H - 230, W - 220
    chosen = None
    for size in range(64, 33, -2):
        fnt = font(size)
        lines = wrap(d, body, fnt, max_w)
        lh = int(size * 1.6)
        if lh * len(lines) > bottom - top:
            continue
        if chosen is None:
            chosen = (fnt, lines, lh)
        if not any(0 < len(l) <= 2 for l in lines):  # 「け。」だけの行など、ぽつんと残る行を避ける
            chosen = (fnt, lines, lh)
            break
    fnt, lines, lh = chosen or (fnt, lines, lh)
    y = top + (bottom - top - lh * len(lines)) / 2
    for line in lines:
        d.text(((W - d.textlength(line, font=fnt)) / 2, y), line, font=fnt, fill=WHITE)
        y += lh

    foot = font(30, "Medium")
    sig = "あらいたかひで｜LEAPS KINGDOM.運営"
    d.line([(W / 2 - 60, H - 175), (W / 2 + 60, H - 175)], fill=GOLD, width=2)
    d.text(((W - d.textlength(sig, font=foot)) / 2, H - 150), sig, font=foot, fill=GOLD)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "PNG", optimize=True)


def metric_value(item):
    if "total_value" in item:
        return item["total_value"].get("value", 0)
    vals = item.get("values") or [{}]
    return vals[0].get("value", 0)


def pick_post(token):
    done = set()
    if os.path.exists(DONE):
        with open(DONE, encoding="utf-8") as f:
            done = {line.split("\t")[1] for line in f if "\t" in line}
    since = now_jst() - timedelta(days=8)
    posts = threads_get("me/threads", token, fields="id,text,timestamp,media_type", limit=40).get("data", [])
    cands = []
    for p in posts:
        if p.get("media_type") != "TEXT_POST" or not p.get("text") or p["id"] in done:
            continue
        if p["timestamp"][:10] < since.strftime("%Y-%m-%d"):
            continue
        if len(card_text(p["text"])) < 15:
            continue
        cands.append(p)
    if not cands:
        return None, "対象の投稿なし"
    scored, insights_ok = [], True
    for p in cands:
        try:
            data = threads_get(f"{p['id']}/insights", token, metric="views,likes,replies,reposts").get("data", [])
            m = {i["name"]: metric_value(i) for i in data}
            score = m.get("likes", 0) * 3 + m.get("replies", 0) * 4 + m.get("reposts", 0) * 5 + m.get("views", 0) / 100
            scored.append((score, p, m))
        except RuntimeError:
            insights_ok = False
            break
    if not insights_ok or not scored:
        return cands[0], "反応の数が取れなかったので、いちばん新しい投稿を使用"
    scored.sort(key=lambda s: s[0], reverse=True)
    score, p, m = scored[0]
    return p, f"いいね{m.get('likes',0)}・返信{m.get('replies',0)}・再投稿{m.get('reposts',0)}・表示{m.get('views',0)}"


def cmd_make():
    token = os.environ.get("THREADS_TOKEN")
    if not token:
        summary("⏸ Threadsの鍵がないので、画像投稿はお休みします。")
        return
    p, why = pick_post(token)
    if not p:
        summary("💤 この1週間に画像にできる投稿がありませんでした。")
        return
    stamp = now_jst().strftime("%Y-%m-%d")
    rel = f"images/{stamp}.png"
    make_card(p["text"], os.path.join(ROOT, rel))
    week = int(now_jst().strftime("%U"))
    with open(PENDING, "w", encoding="utf-8") as f:
        json.dump({"path": rel, "source_id": p["id"], "caption": CAPTIONS[week % len(CAPTIONS)]}, f, ensure_ascii=False)
    summary(f"🖼 画像を作りました：{rel}\n選んだ理由：{why}\n\n元の投稿：\n{p['text']}")


def repo_is_private(repo):
    import requests
    token = os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        return False
    r = requests.get(f"https://api.github.com/repos/{repo}",
                     headers={"Authorization": f"Bearer {token}"}, timeout=30)
    return r.status_code == 200 and r.json().get("private", False)


def cmd_publish():
    if not os.path.exists(PENDING):
        return
    with open(PENDING, encoding="utf-8") as f:
        job = json.load(f)
    base = os.environ.get("IMAGE_BASE_URL")
    if not base:
        repo = os.environ.get("GITHUB_REPOSITORY")
        if repo_is_private(repo):
            summary("⏸ 画像は作りましたが、保管場所が「非公開」のため、Threadsが画像を読み込めません。\n"
                    "保管場所を公開にするか、画像の置き場所（IMAGE_BASE_URL）を設定すると投稿されます。")
            os.remove(PENDING)
            return
        base = f"https://raw.githubusercontent.com/{repo}/main"
    url = f"{base.rstrip('/')}/{job['path']}"
    if os.environ.get("DRY_RUN") == "1":
        summary(f"🧪 お試しモード：画像は作りましたが、Threadsには投稿しません。\n画像のURL：{url}")
        os.remove(PENDING)
        return
    media_id = threads_publish(os.environ["THREADS_TOKEN"], job["caption"], image_url=url)
    with open(DONE, "a", encoding="utf-8") as f:
        f.write(f"{now_jst().strftime('%Y-%m-%d')}\t{job['source_id']}\t{job['path']}\t{media_id}\n")
    os.remove(PENDING)
    summary(f"✅ 画像付き投稿をThreadsに出しました（{job['path']}）")


if __name__ == "__main__":
    {"make": cmd_make, "publish": cmd_publish}[sys.argv[1]]()
