# poc_mvp_manager データスキーマ（正本）

**最終更新：2026-04-08　　関連REQ-ID：REQ-20260408-00（初版・品質マニュアル適用）**

## BLUF
- **DB種別**：なし（JSON ファイル2点のみ）
- **データソース**：`mvps.json`（上書き設定）／ `memos.json`（ユーザーメモ）
- **マイグレーション管理**：なし（JSON 追記型）

---

## データファイル一覧

### `mvps.json`（バージョン管理対象）
**目的**：自動検出結果を上書きしたい MVP のメタデータを記載。エントリが無くても `poc_*` ディレクトリは自動検出される

```json
[
  {
    "_comment": "このファイルはオプションです。自動検出結果を上書きしたいMVPのみ記載してください。",
    "id": "poc_monthly_report",
    "name": "月次レポート自動生成（CLI）",
    "summary": "..."
  },
  {
    "id": "poc_platform_a",
    "name": "AI経営コックピット",
    "summary": "...",
    "urls": {
      "Local": "http://localhost:8501",
      "Streamlit Cloud": "https://..."
    }
  }
]
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| id | str | ◯ | MVP ディレクトリ名 |
| name | str | - | 表示名 |
| summary | str | - | 一行説明 |
| urls | dict[str, str] | - | 起動先URL（ラベル→URL） |

---

### `memos.json`（バージョン管理対象外・`.gitignore` 済）
**目的**：ダッシュボード上でユーザーが書き込むメモの永続化

```json
{
  "poc_platform_a": "TODO: LPリンクを差し替える",
  "npo-joseikin-ai": "オーナー承認待ち"
}
```

---

## 自動検出ロジック（参考）

`app.py` の `_discover_mvps()` が以下のルールで MVP をスキャン：

1. 親ディレクトリ（`../`）配下を列挙
2. `poc_*` で始まるディレクトリを対象に追加
3. `mvps.json` に記載されている非 `poc_*` のディレクトリも追加
4. 各ディレクトリから以下を抽出：
   - `app.py` / `main.py` の docstring（`_docstring_summary`）
   - `requirements.txt` のパッケージ名（`_tech_stack`）
   - `launch.bat` の `--server.port` → URL（`_url_from_launch`）

---

## マイグレーション履歴

### [2026-04-08] REQ-20260408-00 初版ドキュメント化
- 差分（before/after）：`mvps.json` / `memos.json` 構造を初回スナップショット
- マイグレーションスクリプト：なし
- ロールバック手順：本ファイル削除のみ（実データに影響なし）

---

## 備考
- `mvps.json` へのエントリ追加・URL更新は XS（単なる設定変更）
- 自動検出ロジックの変更（`_discover_mvps` の修正）は S または M
- 新しい MVP メタデータ項目を追加する場合は `app.py` と合わせて更新し CHANGELOG に記録
