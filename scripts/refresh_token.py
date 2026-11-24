"""Threads の鍵（長期アクセストークン）を更新して、新しい鍵を標準出力に出す。

鍵は60日で切れるので、毎週これを動かして延長する。
1. まず「更新」を試す（長期の鍵の場合）
2. だめなら、THREADS_APP_SECRET があれば「短期の鍵→長期の鍵への交換」を試す
"""
import os
import sys

import requests

API = "https://graph.threads.net"


def main():
    token = os.environ.get("THREADS_TOKEN", "")
    secret = os.environ.get("THREADS_APP_SECRET", "")
    if not token:
        print("THREADS_TOKEN が登録されていません", file=sys.stderr)
        sys.exit(1)

    r = requests.get(
        f"{API}/refresh_access_token",
        params={"grant_type": "th_refresh_token", "access_token": token},
        timeout=60,
    )
    if r.status_code == 200 and "access_token" in r.json():
        print(r.json()["access_token"])
        return
    refresh_error = r.text

    if secret:
        r = requests.get(
            f"{API}/access_token",
            params={
                "grant_type": "th_exchange_token",
                "client_secret": secret,
                "access_token": token,
            },
            timeout=60,
        )
        if r.status_code == 200 and "access_token" in r.json():
            print(r.json()["access_token"])
            return
        print(f"交換にも失敗: {r.text}", file=sys.stderr)

    print(f"鍵の更新に失敗: {refresh_error}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
