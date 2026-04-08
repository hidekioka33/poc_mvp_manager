# CHANGELOG - poc_mvp_manager

本MVPへの全ての変更を記録する。**XS/S/M 区分を必ず記載する**こと。

記載フォーマット：
```
## [YYYY-MM-DD] REQ-YYYYMMDD-xx [XS|S|M] 変更タイトル
- **変更内容**：何を変えたか
- **影響範囲**：UI / DB / API / 外部連携 / 他MVP のうち該当するもの
- **テスト結果**：スモーク pass / 受入 pass 等
- **備考**：ロールバック手順のリンク、関連Issue等（任意）
```

---

## [2026-04-08] REQ-20260408-00 [M] MVP品質マニュアル適用（初版整備）
- **変更内容**：
  - `tests/smoke_test.py` を新規作成（10項目：ファイル構造・mvps.json パース・app.py 構文・親ディレクトリスキャン）
  - `docs/schema.md` を新規作成（mvps.json / memos.json の構造を正本化）
  - `CHANGELOG.md` を新規作成（本ファイル）
  - `README.md` に「ロールバック手順」セクションを追加
  - `.gitignore` を新規作成
  - `.env.example` を新規作成（外部APIキー不使用を明記）
- **影響範囲**：なし（ドキュメント・テスト整備のみ。アプリ本体に変更なし）
- **テスト結果**：スモークテスト 10/10 PASS
- **備考**：`CTO/Context/dev_process_manual.md` に従う。CTO-019（ロールアウト）の一環
