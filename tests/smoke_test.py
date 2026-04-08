"""
poc_mvp_manager スモークテスト

目的：
  MVPダッシュボードの最低限の健全性を確認する。
  「ファイル構造」「mvps.json パース」「app.py 構文チェック」の3観点を自動チェック。
  Streamlit アプリ本体は起動しないため、_discover_mvps は ast 解析で存在確認のみ行う。

実行方法：
  python tests/smoke_test.py

成功基準：
  すべての項目を PASS し、終了コード 0 で終了すること。

dev_process_manual.md 準拠：(4)テストフェーズの必須成果物。
"""

import io
import sys
import ast
import json
from pathlib import Path

# Windows cp932 対策：標準出力を UTF-8 に切り替え
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def check(label: str, condition: bool, details: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    suffix = f" - {details}" if details else ""
    print(f"[{status}] {label}{suffix}")
    return condition


def main() -> None:
    print("=" * 60)
    print("poc_mvp_manager スモークテスト開始")
    print("=" * 60)

    results: list[bool] = []

    # --- 1. ファイル構造チェック ---
    for path, label in [
        ("app.py", "Streamlit UI (app.py)"),
        ("mvps.json", "MVP上書き設定 (mvps.json)"),
        ("requirements.txt", "依存関係定義"),
        (".env.example", ".env.example"),
        ("launch.bat", "起動バッチ"),
    ]:
        results.append(check(label, (ROOT / path).exists(), str(ROOT / path)))

    # --- 2. mvps.json がパースできて、必要なキーを持つ ---
    mvps_ok = False
    mvps_detail = ""
    try:
        with open(ROOT / "mvps.json", encoding="utf-8") as f:
            mvps = json.load(f)
        # 各エントリが id を持っているか（_comment 行は除外）
        valid_entries = [e for e in mvps if "id" in e]
        mvps_ok = len(valid_entries) >= 1 and all("name" in e or "summary" in e for e in valid_entries)
        mvps_detail = f"{len(valid_entries)} 件のMVPエントリ"
    except Exception as e:
        mvps_detail = str(e)
    results.append(check("mvps.json パース", mvps_ok, mvps_detail))

    # --- 3. app.py の AST 解析（構文エラーなし・関数定義確認） ---
    ast_ok = False
    ast_detail = ""
    try:
        source = (ROOT / "app.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        # 主要関数が存在するか
        func_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
        expected = {"_discover_mvps", "_docstring_summary", "_tech_stack"}
        ast_ok = expected.issubset(func_names)
        missing = expected - func_names
        ast_detail = f"関数数={len(func_names)}" if not missing else f"不足: {missing}"
    except SyntaxError as e:
        ast_detail = f"SyntaxError: {e}"
    except Exception as e:
        ast_detail = str(e)
    results.append(check("app.py 構文＋主要関数", ast_ok, ast_detail))

    # --- 4. 親ディレクトリが存在し、MVP候補ディレクトリが見える ---
    parent_ok = False
    parent_detail = ""
    try:
        parent = ROOT.parent
        mvp_dirs = [d for d in parent.iterdir() if d.is_dir() and (d.name.startswith("poc_") or d.name in {"npo-joseikin-ai", "daigaku-juken-ai", "sns-monitor-ai", "x-sns-analyzer"})]
        parent_ok = len(mvp_dirs) >= 3  # 最低3つは見つかるはず
        parent_detail = f"{len(mvp_dirs)} 件のMVPディレクトリ検出"
    except Exception as e:
        parent_detail = str(e)
    results.append(check("親ディレクトリのMVP検出", parent_ok, parent_detail))

    # --- 5. requirements.txt に streamlit が含まれている ---
    req_ok = False
    try:
        content = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        req_ok = "streamlit" in content
    except Exception:
        pass
    results.append(check("requirements.txt に streamlit", req_ok))

    # --- 6. .gitignore に .env が含まれている ---
    gitignore_ok = False
    gitignore_path = ROOT / ".gitignore"
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        gitignore_ok = ".env" in content
    results.append(check(".gitignore で .env を除外", gitignore_ok))

    # --- サマリー ---
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"結果：{passed} / {total} PASS")
    if passed == total:
        print("スモークテスト完了：すべて PASS")
        sys.exit(0)
    else:
        print("スモークテスト失敗：上記 FAIL を確認してください")
        sys.exit(1)


if __name__ == "__main__":
    main()
