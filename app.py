"""
MVP管理ダッシュボード
起動方法: python -m streamlit run app.py --server.port 8502
"""
import ast
import json
import os
import re
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

# ─── パス定義 ────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
PARENT_DIR = BASE_DIR.parent
OVERRIDES_FILE = BASE_DIR / "mvps.json"   # 任意の手動上書きファイル
MEMOS_FILE = BASE_DIR / "memos.json"

# ─── 環境判定 ─────────────────────────────────────────────────
# IS_CLOUD=true 環境変数 または ローカルにpoc_*フォルダが存在しない場合はCloud扱い
def _detect_cloud() -> bool:
    if os.environ.get("IS_CLOUD", "").lower() == "true":
        return True
    try:
        return not any(
            d.is_dir() and d.name.startswith("poc_") and d != BASE_DIR
            for d in PARENT_DIR.iterdir()
        )
    except Exception:
        return True

IS_CLOUD = _detect_cloud()

# ─── 自動検出ロジック ─────────────────────────────────────────

def _docstring_summary(filepath: Path) -> str:
    """モジュールdocstringの先頭から意味のある行を抽出する"""
    if not filepath.exists():
        return ""
    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source)
        doc = ast.get_docstring(tree)
        if doc:
            lines = [ln.strip() for ln in doc.splitlines() if ln.strip()]
            filtered = []
            for ln in lines:
                if re.match(r"(使用方法|起動方法|Usage|起動|How to|python )", ln):
                    break
                filtered.append(ln)
            return " / ".join(filtered[:2]) if filtered else ""
    except Exception:
        pass
    return ""

def _tech_stack(d: Path) -> str:
    """requirements.txt からパッケージ名を列挙する"""
    req = d / "requirements.txt"
    if not req.exists():
        return "—"
    pkgs = []
    for line in req.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        pkg = re.split(r"[>=<!~\[ ]", line)[0].strip()
        if pkg:
            pkgs.append(pkg)
    return " / ".join(pkgs) if pkgs else "—"

def _url_from_launch(d: Path, has_ui: bool) -> str | None:
    """launch.bat の --server.port からURLを組み立てる"""
    bat = d / "launch.bat"
    if bat.exists():
        content = bat.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"--server\.port\s+(\d+)", content)
        if m:
            return f"http://localhost:{m.group(1)}"
    return "http://localhost:8501" if has_ui else None

def _discover_mvps() -> list[dict]:
    """poc_* ディレクトリを自動スキャンしてMVP情報を生成する"""
    overrides: dict[str, dict] = {}
    if OVERRIDES_FILE.exists():
        for entry in json.loads(OVERRIDES_FILE.read_text(encoding="utf-8")):
            overrides[entry["id"]] = entry

    # mvps.json に登録された非poc_フォルダも対象に加える
    extra_ids = {eid for eid in overrides if not eid.startswith("poc_")}

    target_dirs = sorted(
        d for d in PARENT_DIR.iterdir()
        if d.is_dir() and d != BASE_DIR and (d.name.startswith("poc_") or d.name in extra_ids)
    )

    mvps = []
    for d in target_dirs:
        mvp_id = d.name

        # ── 自動検出 ──────────────────────────────────────────
        has_ui = (d / "app.py").exists()
        url = _url_from_launch(d, has_ui)

        # 概要: app.py > main.py の順で試みる
        summary = ""
        for fname in ("app.py", "main.py"):
            summary = _docstring_summary(d / fname)
            if summary:
                break
        if not summary:
            summary = "（概要未設定）"

        # 名称: poc_ を除いてタイトルケース
        name = mvp_id.removeprefix("poc_").replace("_", " ").title()

        # 技術スタック
        tech_stack = _tech_stack(d)

        # 日付: ファイルシステムのタイムスタンプ
        stat = d.stat()
        created_at = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d")
        py_mtimes = [f.stat().st_mtime for f in d.rglob("*.py") if f.is_file()]
        mtime = max(py_mtimes) if py_mtimes else stat.st_mtime
        updated_at = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")

        # ── mvps.json による上書き（任意） ───────────────────
        ov = overrides.get(mvp_id, {})

        # urls: {"Local": "http://...", "Streamlit Cloud": "https://..."} 形式
        # mvps.json に urls があればそれを優先。なければ url から {"Local": url} を生成。
        ov_url  = ov.get("url", url)
        ov_urls = ov.get("urls")
        if ov_urls:
            resolved_urls = ov_urls
        elif ov_url:
            resolved_urls = {"Local": ov_url}
        else:
            resolved_urls = {}

        mvp = {
            "id": mvp_id,
            "name": ov.get("name", name),
            "summary": ov.get("summary", summary),
            "tech_stack": ov.get("tech_stack", tech_stack),
            "has_ui": ov.get("has_ui", has_ui),
            "urls": resolved_urls,
            "dir": d,           # 起動処理で使用
            "created_at": ov.get("created_at", created_at),
            "updated_at": ov.get("updated_at", updated_at),
        }
        mvps.append(mvp)

    return mvps

def _discover_mvps_cloud() -> list[dict]:
    """Cloud環境用: mvps.jsonのみからMVP情報を生成する"""
    if not OVERRIDES_FILE.exists():
        return []
    entries = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
    mvps = []
    for entry in entries:
        if "id" not in entry:
            continue
        mvp_id = entry["id"]
        urls = entry.get("urls", {})
        if not urls and entry.get("url"):
            urls = {"Local": entry["url"]}
        mvps.append({
            "id": mvp_id,
            "name": entry.get("name", mvp_id.replace("_", " ").title()),
            "summary": entry.get("summary", "（概要未設定）"),
            "tech_stack": entry.get("tech_stack", "—"),
            "has_ui": entry.get("has_ui", bool(urls)),
            "urls": urls,
            "dir": None,
            "created_at": entry.get("created_at", "—"),
            "updated_at": entry.get("updated_at", "—"),
        })
    return mvps

# ─── 起動支援ユーティリティ ───────────────────────────────────

def _port_from_url(url: str) -> int | None:
    """URLからポート番号を取得する"""
    m = re.search(r":(\d+)/?$", url)
    return int(m.group(1)) if m else None

def _is_port_open(port: int) -> bool:
    """ローカルポートが使用中（＝プロセス起動済み）かチェックする"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("localhost", port)) == 0

def _launch_mvp(mvp_dir: Path, port: int) -> None:
    """MVPをバックグラウンドで起動する（新しいコンソールウィンドウで表示）"""
    app_py = mvp_dir / "app.py"
    if not app_py.exists():
        return
    subprocess.Popen(
        [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-Command",
            f"python -m streamlit run '{app_py}' --server.port {port}",
        ],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )

# ─── メモ読み書き ────────────────────────────────────────────
def load_memos() -> dict:
    if not MEMOS_FILE.exists():
        return {}
    return json.loads(MEMOS_FILE.read_text(encoding="utf-8"))

def save_memos(memos: dict) -> None:
    MEMOS_FILE.write_text(
        json.dumps(memos, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

# ─── ページ設定 ────────────────────────────────────────────────
st.set_page_config(
    page_title="MVP管理ダッシュボード",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── カスタムCSS ──────────────────────────────────────────────
st.markdown("""
<style>
.mvp-open-btn {
    display: inline-block;
    padding: 8px 20px;
    background-color: #1a3c8f;
    color: white !important;
    border-radius: 6px;
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    margin-top: 8px;
    margin-right: 8px;
    transition: background-color 0.2s;
}
.mvp-open-btn:hover {
    background-color: #142f70;
    color: white !important;
    text-decoration: none;
}
.mvp-open-btn-cloud {
    display: inline-block;
    padding: 8px 20px;
    background-color: #059669;
    color: white !important;
    border-radius: 6px;
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    margin-top: 8px;
    margin-right: 8px;
    transition: background-color 0.2s;
}
.mvp-open-btn-cloud:hover {
    background-color: #047857;
    color: white !important;
    text-decoration: none;
}
.mvp-open-btn-other {
    display: inline-block;
    padding: 8px 20px;
    background-color: #6b7280;
    color: white !important;
    border-radius: 6px;
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    margin-top: 8px;
    margin-right: 8px;
    transition: background-color 0.2s;
}
.mvp-open-btn-other:hover {
    background-color: #4b5563;
    color: white !important;
    text-decoration: none;
}
.mvp-cli-badge {
    display: inline-block;
    padding: 8px 20px;
    background-color: #e0e0e0;
    color: #888;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 500;
    margin-top: 8px;
    cursor: not-allowed;
}
.memo-updated {
    font-size: 11px;
    color: #999;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

# ─── セッション初期化 ─────────────────────────────────────────
if "memos" not in st.session_state:
    st.session_state.memos = load_memos()

# ─── ヘッダー ─────────────────────────────────────────────────
st.title("🗂️ MVP管理ダッシュボード")
st.caption("poc_* ディレクトリを自動検出して一覧表示します。新MVPを作成するだけで自動的に反映されます。")
st.divider()

# ─── MVP一覧（毎回スキャン） ──────────────────────────────────
mvps = _discover_mvps_cloud() if IS_CLOUD else _discover_mvps()
memos = st.session_state.memos

if not mvps:
    st.info("poc_* ディレクトリが見つかりません。MVPを構築すると自動的にここに表示されます。")
else:
    st.markdown(f"**{len(mvps)} 件のMVP**")
    st.write("")

    for mvp in mvps:
        mvp_id = mvp["id"]
        memo_data = memos.get(mvp_id, {"text": "", "updated_at": None})

        with st.container(border=True):
            col_info, col_memo = st.columns([3, 2])

            # ── 左カラム: MVP情報 ──────────────────────────────
            with col_info:
                st.subheader(mvp["name"])
                st.caption(
                    f"作成日: **{mvp['created_at']}**　　"
                    f"更新日: **{mvp['updated_at']}**　　"
                    f"`{mvp_id}`"
                )

                st.write("")
                st.markdown("**概要**")
                st.write(mvp["summary"])

                st.markdown("**システム構成**")
                st.code(mvp["tech_stack"], language=None)

                urls = mvp.get("urls", {})
                if mvp.get("has_ui") and urls:

                    def _btn_class(env_name: str) -> str:
                        lower = env_name.lower()
                        if "local" in lower:
                            return "mvp-open-btn"
                        if "cloud" in lower or "streamlit" in lower or "外部" in lower:
                            return "mvp-open-btn-cloud"
                        return "mvp-open-btn-other"

                    def _btn_icon(env_name: str) -> str:
                        lower = env_name.lower()
                        if "local" in lower:
                            return "🖥️"
                        if "cloud" in lower or "streamlit" in lower or "外部" in lower:
                            return "🌐"
                        return "🚀"

                    # ── 非Localボタンは従来どおりHTMLリンク ────
                    non_local_html = "".join(
                        f'<a class="{_btn_class(env)}" href="{env_url}" '
                        f'target="_blank" rel="noopener noreferrer">'
                        f'{_btn_icon(env)} {env}</a>'
                        for env, env_url in urls.items()
                        if "local" not in env.lower()
                    )
                    if non_local_html:
                        st.markdown(non_local_html, unsafe_allow_html=True)

                    # ── LocalボタンはポートON/OFFで動作を切替（ローカル環境のみ） ──
                    if not IS_CLOUD:
                        local_url = next(
                            (u for e, u in urls.items() if "local" in e.lower()), None
                        )
                        if local_url:
                            port = _port_from_url(local_url)
                            launch_key = f"launching_{mvp_id}"

                            if port and _is_port_open(port):
                                # 起動済み → 開くリンク
                                st.markdown(
                                    f'<a class="mvp-open-btn" href="{local_url}" '
                                    f'target="_blank" rel="noopener noreferrer">'
                                    f'🖥️ Local</a>',
                                    unsafe_allow_html=True,
                                )
                                if launch_key in st.session_state:
                                    del st.session_state[launch_key]

                            elif st.session_state.get(launch_key):
                                # 起動中ポーリング（2秒ごとに再チェック）
                                st.info("⏳ 起動中... しばらくお待ちください")
                                time.sleep(2)
                                st.rerun()

                            else:
                                # 未起動 → 起動ボタン
                                if st.button(
                                    "▶ 起動して開く",
                                    key=f"launch_{mvp_id}",
                                    help=f"ポート {port} でStreamlitを起動します",
                                ):
                                    _launch_mvp(mvp["dir"], port)
                                    st.session_state[launch_key] = True
                                    st.rerun()

                    elif not non_local_html:
                        # Cloud環境かつ外部URLなし → バッジ表示
                        st.markdown(
                            '<span class="mvp-cli-badge">🔒 外部公開なし（ローカル専用）</span>',
                            unsafe_allow_html=True,
                        )

                else:
                    st.markdown(
                        '<span class="mvp-cli-badge">🖥️ CLI専用（ブラウザUIなし）</span>',
                        unsafe_allow_html=True,
                    )

            # ── 右カラム: メモ ────────────────────────────────
            with col_memo:
                st.markdown("**メモ**（50文字以内）")
                new_text = st.text_area(
                    label="メモ入力",
                    value=memo_data.get("text", ""),
                    max_chars=50,
                    height=120,
                    key=f"memo_{mvp_id}",
                    label_visibility="collapsed",
                    placeholder="自由にメモを記入できます...",
                )

                col_btn, col_len = st.columns([1, 1])
                with col_btn:
                    if st.button("保存", key=f"save_{mvp_id}", type="primary"):
                        memos[mvp_id] = {
                            "text": new_text,
                            "updated_at": datetime.now().isoformat(timespec="seconds"),
                        }
                        st.session_state.memos = memos
                        save_memos(memos)
                        st.success("保存しました", icon="✅")

                with col_len:
                    char_count = len(new_text)
                    color = "#e74c3c" if char_count >= 45 else "#999"
                    st.markdown(
                        f'<div style="text-align:right; color:{color}; '
                        f'font-size:12px; padding-top:8px;">'
                        f'{char_count} / 50</div>',
                        unsafe_allow_html=True,
                    )

                if memo_data.get("updated_at"):
                    st.markdown(
                        f'<div class="memo-updated">最終保存: {memo_data["updated_at"]}</div>',
                        unsafe_allow_html=True,
                    )

        st.write("")

# ─── フッター ─────────────────────────────────────────────────
st.divider()
st.caption(
    "名称・概要を手動で上書きしたい場合は `mvps.json` にエントリを追記してください（任意）。"
)
