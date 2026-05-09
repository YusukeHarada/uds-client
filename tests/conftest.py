"""
テスト共通設定。
GUIテストをヘッドレスで実行するためoffscreenを設定する。
main_window.py本体には一切環境変数を書かない。
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
