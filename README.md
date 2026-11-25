# Threads 自動投稿（leaps.takahide）

`posts.txt` の投稿を上から順に、毎日 **7時・12時・21時ごろ** に1本ずつ Threads に自動で投稿します。
GitHubのサーバーで動くので、スマホやPCを閉じていても動きます。費用は0円です。

- 投稿の時刻は、GitHubの混み具合で数分〜十数分ずれることがあります
- 投稿したものは `state/posted.tsv` に記録されるので、同じものが2回出ることはありません
- ストックが残り9本以下になると、実行結果の画面でお知らせが出ます
- Threadsの鍵（60日で切れる）は、毎週月曜に自動で更新されます

---

## はじめの設定（1回だけ・30分くらい）

### ステップ1：GitHubに空の保管場所を作る
1. https://github.com/new を開く（leapsnext-bot でログイン）
2. 名前（Repository name）に `threads-auto` と入れる
3. **Private（非公開）** を選ぶ
4. 「Create repository」を押す
5. できたら Claude に「作った」と伝える → 中身は Claude が入れます

### ステップ2：Metaで「Threads用のアプリ」を作る
1. https://developers.facebook.com/apps を開いてログイン
2. 「アプリを作成」→ 使い方（ユースケース）で **「Threads APIにアクセス」** を選ぶ
3. アプリ名は何でもOK（例：`kingdom-threads`）→ 作成
4. 左メニュー「ユースケース」→「Threads APIにアクセス」→「カスタマイズ」
5. 権限の一覧で **threads_content_publish** を「追加」する（threads_basic は最初から入っています）

### ステップ3：自分のThreadsをテスターに登録して承認する
1. 左メニュー「アプリの役割」→「役割」→「メンバーを追加」→ **Threadsテスター** を選び、`leaps` と打って **写真付きの候補を選ぶ**（文字だけで確定すると「Invalid id」エラー）
2. Threadsアプリで「設定」→「その他の設定」→「ウェブサイトのアクセス許可」→「Invites」タブ → **承認**

### ステップ4：鍵を2つコピーする（PCで行うこと）
※ iPhoneのSafariでは「アクセストークンを生成」が動かないことがあります。PCのブラウザでやるのが確実です。
1. 「ユースケース」→「カスタマイズ」→「設定」の一番下「ユーザートークン生成ツール」で、`leaps.takahide` の **「アクセストークンを生成」** → 出てきた鍵（`TH`で始まる）をコピー
   → これが **THREADS_TOKEN**（最初から60日有効の鍵です）
2. 同じ画面の上「Threadsのapp secret」の **「表示」**（「リセット」は押さない）→ 枠の中をクリックして ⌘A → ⌘C
   → これが **THREADS_APP_SECRET**

※ 鍵は他人に見せないでください。チャットにも貼らず、次のステップでGitHubに直接入れます。

### ステップ5：GitHub用の鍵を作る（鍵の自動更新に使う）
1. https://github.com/settings/personal-access-tokens/new を開く
2. 名前：`threads-auto`、期限（Expiration）：できるだけ長く（1年など）
3. 「Repository access」→「Only select repositories」→ `threads-auto` を選ぶ
4. 「Permissions」→「Repository permissions」→ **Secrets** を「Read and write」にする
5. 「Generate token」→ 出てきた文字をコピー → これが **GH_PAT**

### ステップ6：3つの鍵をGitHubに登録する
1. `threads-auto` のページ →「Settings」→「Secrets and variables」→「Actions」
2. 「New repository secret」で、次の3つを1つずつ登録
   - 名前 `THREADS_TOKEN`（打ち間違い注意。コピーして貼るのが確実） ／ 値：ステップ4-1の鍵
   - 名前 `THREADS_APP_SECRET` ／ 値：ステップ4-2の鍵
   - 名前 `GH_PAT` ／ 値：ステップ5の鍵

### ステップ7：試運転
1. 「Actions」→ 左の **「Threads自動投稿」** →「Run workflow」
2. 「お試し」のまま実行 → 結果画面に「次に出る投稿」が表示されればOK
3. もう一度「Run workflow」→ **「今すぐ投稿」** を選んで実行 → Threadsに1本出ていれば完成 🎉

あとは何もしなくても、毎日3本ずつ投稿されます。

---

## ふだんの使い方

- **投稿を直す・足す**：`posts.txt` を開いて鉛筆マークで編集。`【番号】` の行の下に本文を書くだけ
- **次の1か月分を作る**：Claudeに「次の90本作って」と頼む → 中身を確認して入れ替え
- **一時停止したい**：「Actions」→「Threads自動投稿」→ 右上の「…」→「Disable workflow」

## うまく動かないとき
「Actions」で赤い ❌ が付いた実行を開くと、日本語で理由が出ます。その画面をClaudeに見せてください。

---

# 追加の自動化（コメント返信・画像カード・X）

## 全体の時間割
| 時間（日本時間） | 内容 |
|---|---|
| 毎日 7:07 / 12:07 / 21:07ごろ | Threadsに1本投稿（posts.txt） |
| 毎日 7:37 / 12:37 / 20:37ごろ | Xに1本投稿（x_posts.txt） |
| 毎時23分ごろ | Threadsのコメントに自動返信 |
| 3時間ごと（0:53・3:53 …ごろ） | Xのリプライを集めて、返信の下書きをメールで通知 |
| 毎週日曜 20:23ごろ | 1週間でいちばん反応が良かった投稿を画像カードにしてThreadsへ |
| 毎週月曜 3:23ごろ | Threadsの鍵を自動で延長 |

## コメント自動返信
- AI（Claude）がコメントを読んで、🟢お礼／🟡笑縁LIVEに軽く誘う／🔵予約リンク付きで案内／🔴返信しない、に振り分けます
- 🔴（批判・お金の話・判断が難しいもの）は返信せず、GitHubの「Issues」に一覧が作られ、カリスマにメールが届きます
- スタート時より前のコメントには返信しません
- 返信のルールを変えたいときは `scripts/reply.py` の上のほうの文章を書き換えます（Claudeに頼めばOK）

**必要な鍵：ANTHROPIC_API_KEY**
1. https://console.anthropic.com にログイン（アカウントがなければ作成）
2. 「Billing（請求）」でクレジットを購入（5ドルから。返信だけなら数か月もちます）
3. 「API Keys」→「Create Key」→ 名前 `threads-reply` → 出てきた鍵（`sk-ant-`で始まる）をコピー
4. GitHubのシークレットに登録：名前 `ANTHROPIC_API_KEY`
5. 「Actions」→「Threadsコメント自動返信」→「お試し」で実行 → ✅ならOK

## 画像カード投稿
- 画像は `images/` に保存され、その公開URLをThreadsに渡します
- **保管場所（このリポジトリ）が非公開のままだと、Threadsが画像を読めないので投稿はお休みになります**
- 公開にする方法：「Settings」→「General」→一番下「Danger Zone」→「Change repository visibility」→「Public」
  - 鍵（シークレット）は公開されません。見えるのはプログラムと投稿文と画像だけです
- 試すとき：「Actions」→「週1回の画像カード投稿」→「お試し」（画像を作るだけ）

## X自動投稿（@takahide_ai）
- 投稿は `x_posts.txt`（90本）。1本あたり約0.015ドル（リンクなしの場合）
- 鍵が登録されるまでは、自動でお休みします

**必要な鍵（4つ）**
1. @takahide_ai でログインした状態で https://console.x.com（X Developer Console）を開く
2. アプリを作成 →「User authentication settings（ユーザー認証設定）」で権限を **Read and write（読み取りと書き込み）** にする
3. 「Keys and tokens」で次の4つを発行してコピー（Access Tokenは、権限をRead and writeにした**後で**発行する）
4. クレジットを購入し、使いすぎ防止の上限（Spending limit）を設定（例：月5ドル）
5. GitHubのシークレットに登録

| 名前 | 中身 |
|---|---|
| `X_API_KEY` | API Key（Consumer Key） |
| `X_API_SECRET` | API Key Secret（Consumer Secret） |
| `X_ACCESS_TOKEN` | Access Token |
| `X_ACCESS_SECRET` | Access Token Secret |

6. 「Actions」→「X自動投稿」→「お試し」→ ✅なら「今すぐ投稿」で1本出して確認

## Xリプライの下書き通知
- Xのルールでは、自動で返信するには相手の同意が必要です。そのため、Xは**AIが下書きを作り、送るのはカリスマ**という形にしています
- 3時間ごとに @takahide_ai へのリプライを集めて、GitHubの「Issues」に下書きをまとめます（→メールが届きます）
- メールの「この下書きで返信画面を開く」を押すと、下書き入りのXの返信画面が開くので、確認して送るだけです
- 費用の目安：リプライ1件を読むごとに約0.005ドル＋AI代（ごくわずか）
