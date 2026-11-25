"""各スクリプトで共通に使う部品（Threads・X・GitHub・Claude への接続）"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.parse
from datetime import datetime, timedelta, timezone

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JST = timezone(timedelta(hours=9))
THREADS_API = "https://graph.threads.net/v1.0"


def now_jst():
    return datetime.now(JST)


def summary(msg):
    """実行結果の画面（GitHubの Summary）とログの両方に出す"""
    print(msg)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(msg + "\n\n")


# ---------------- Threads ----------------

def threads_get(path, token, **params):
    params["access_token"] = token
    r = requests.get(f"{THREADS_API}/{path}", params=params, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Threadsからの読み込みに失敗: {r.status_code} {r.text}")
    return r.json()


def threads_publish(token, text, reply_to_id=None, image_url=None):
    """Threadsに投稿する（返信・画像にも対応）。投稿IDを返す"""
    data = {"text": text, "access_token": token}
    if image_url:
        data.update(media_type="IMAGE", image_url=image_url)
    else:
        data["media_type"] = "TEXT"
    if reply_to_id:
        data["reply_to_id"] = reply_to_id
    r = requests.post(f"{THREADS_API}/me/threads", data=data, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"下書きの作成に失敗: {r.status_code} {r.text}")
    creation_id = r.json()["id"]
    time.sleep(30 if image_url else 5)  # 画像はThreads側の読み込みに時間がかかる
    last = None
    for _ in range(5):
        r = requests.post(
            f"{THREADS_API}/me/threads_publish",
            data={"creation_id": creation_id, "access_token": token},
            timeout=60,
        )
        if r.status_code == 200:
            return r.json()["id"]
        last = r
        time.sleep(15)
    raise RuntimeError(f"公開に失敗: {last.status_code} {last.text}")


# ---------------- X（旧Twitter） ----------------

def _pct(s):
    return urllib.parse.quote(str(s), safe="~-._")


def x_request(method, url, params=None, json_body=None):
    """X API を OAuth 1.0a（自分のアカウント）で呼び出す"""
    params = params or {}
    oauth = {
        "oauth_consumer_key": os.environ["X_API_KEY"],
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": os.environ["X_ACCESS_TOKEN"],
        "oauth_version": "1.0",
    }
    allp = {**oauth, **{k: str(v) for k, v in params.items()}}
    param_str = "&".join(f"{_pct(k)}={_pct(v)}" for k, v in sorted(allp.items()))
    base = "&".join([method, _pct(url), _pct(param_str)])
    key = f"{_pct(os.environ['X_API_SECRET'])}&{_pct(os.environ['X_ACCESS_SECRET'])}"
    oauth["oauth_signature"] = base64.b64encode(
        hmac.new(key.encode(), base.encode(), hashlib.sha1).digest()).decode()
    header = "OAuth " + ", ".join(f'{_pct(k)}="{_pct(v)}"' for k, v in sorted(oauth.items()))
    headers = {"Authorization": header}
    if json_body is not None:
        headers["Content-Type"] = "application/json"
    r = requests.request(method, url, params=params or None, headers=headers,
                         data=json.dumps(json_body) if json_body is not None else None, timeout=60)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"X APIでエラー: {r.status_code} {r.text}")
    return r.json()


def x_publish(text):
    """Xに投稿する。投稿IDを返す"""
    return x_request("POST", "https://api.x.com/2/tweets", json_body={"text": text})["data"]["id"]


def x_length(text):
    """Xの文字数の数え方（日本語などは1文字＝2、URLは23）で数える"""
    import re
    total = 0
    for part in re.split(r"(https?://\S+)", text):
        if re.match(r"https?://", part):
            total += 23
            continue
        for ch in part:
            cp = ord(ch)
            if cp <= 0x10FF or 0x2000 <= cp <= 0x200D or 0x2010 <= cp <= 0x201F or 0x2032 <= cp <= 0x2037:
                total += 1
            else:
                total += 2
    return total


# ---------------- Claude（返信文づくり） ----------------

def ask_claude(system, user, max_tokens=500):
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": os.environ["ANTHROPIC_API_KEY"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": os.environ.get("CLAUDE_MODEL", "claude-haiku-5-5"),
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        },
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Claudeへの問い合わせに失敗: {r.status_code} {r.text}")
    return "".join(b.get("text", "") for b in r.json()["content"])


# ---------------- GitHub（カリスマへの通知） ----------------

def notify_owner(title, body):
    """GitHubの「Issue」を作る → カリスマにメールで通知が届く"""
    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        print("（通知先がないので、ログにだけ出します）\n" + title + "\n" + body)
        return
    r = requests.post(
        f"https://api.github.com/repos/{repo}/issues",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        json={"title": title, "body": body},
        timeout=60,
    )
    if r.status_code not in (200, 201):
        print(f"通知の作成に失敗: {r.status_code} {r.text}")
