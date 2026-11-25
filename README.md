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
