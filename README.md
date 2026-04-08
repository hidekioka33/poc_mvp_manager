# poc_mvp_manager

全 MVP を一覧するダッシュボード。親ディレクトリの `poc_*` ディレクトリを自動検出し、各 MVP の説明・技術スタック・起動URL・ポート状態を一覧する Streamlit アプリ。

## 概要

- **ターゲット**：CTO／オーナー（MVP ステータスを一目で把握したい）
- **主要機能**：MVP 自動検出、ポート応答チェック、`mvps.json` による上書き、メモ機能、起動リンク
- **技術スタック**：Python 3.11 / Streamlit のみ（外部APIなし）

## ファイル構成

```
poc_mvp_manager/
├── app.py            # Streamlit ダッシュボード本体
├── mvps.json         # 上書き設定（任意）
├── memos.json        # ユーザーメモ（自動生成・gitignore 済）
├── requirements.txt
├── launch.bat        # Windows 起動バッチ（ポート 8502）
├── .env.example
├── .gitignore
├── docs/
│   └── schema.md
├── tests/
│   └── smoke_test.py
└── CHANGELOG.md
```

## セットアップ

```bash
# 1. 依存関係インストール
pip install -r requirements.txt

# 2. スモークテスト
python tests/smoke_test.py

# 3. 起動（Windows）
launch.bat
# または
python -m streamlit run app.py --server.port 8502
```

起動後、http://localhost:8502 で確認。

## 必須の環境変数

なし（外部APIを使用しない）

## 開発ルール

本MVPは `CTO/Context/dev_process_manual.md` に従う。変更時は：
1. REQ-ID を発番し、CHANGELOG に追記
2. XS/S/M 区分を判定（`_discover_mvps` の修正は S、mvps.json の項目追加は XS）
3. `python tests/smoke_test.py` を pass
4. データ構造変更時は `docs/schema.md` を更新

## 稼働ステータス機能（TODO）

本ダッシュボードには将来的に各 MVP の稼働ステータス欄を追加する（CTO-019 の後続タスクとして、`dev_process_manual.md` に準拠した `smoke_test.py` の結果を可視化）。

## ロールバック手順

### 1. 即時対応（5分以内）
1. **Git で直前コミットに戻す**：
   ```bash
   git log --oneline -10
   git revert <problem-commit>
   git push
   ```
2. ローカルで `launch.bat` を再実行

### 2. mvps.json 破損の場合
1. `mvps.json` を Git で直前版に戻す：
   ```bash
   git checkout HEAD -- mvps.json
   ```
2. ダッシュボードを再起動
3. `_discover_mvps()` は `mvps.json` が無くても動作するため、最悪空ファイルにしてもよい

### 3. memos.json 破損の場合
1. `memos.json` は `.gitignore` 済なので手動バックアップがなければ復旧不可
2. 空の `{}` で初期化して続行
3. 重要なメモは今後 Git 管理対象にするか、定期バックアップを検討

### 4. app.py の自動検出ロジックが誤動作する場合
1. 該当 MVP を `mvps.json` に手動で登録して override
2. 原因究明 → 修正 → スモークテスト pass → 再デプロイ

### 5. 完全復旧できない場合
1. オーナーに BLUF 形式で即時報告
2. 代替手段として各 MVP の `launch.bat` を直接実行
3. 復旧プランをオーナーと合意のうえ実行

### 検証
復旧後は必ず以下を実行：
```bash
python tests/smoke_test.py
```
全項目 PASS を確認してから、ダッシュボードで全 MVP が一覧表示されることを確認する。
