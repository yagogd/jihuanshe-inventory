"""Interactive screen reader: dump current window and print readable structure.

Usage: python scripts/screen.py
"""
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ADB = os.environ.get("JIHUANSHE_ADB", "adb")


def dump_xml() -> str | None:
    proc = subprocess.run(
        [ADB, "shell", "uiautomator", "dump", "/sdcard/window.xml"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )
    if "dumped" not in (proc.stdout or "") + (proc.stderr or ""):
        print("  [no se pudo hacer dump]", file=sys.stderr)
        return None
    cat = subprocess.run(
        [ADB, "shell", "cat", "/sdcard/window.xml"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )
    return cat.stdout


def main() -> None:
    xml = dump_xml()
    if not xml:
        return
    root = ET.fromstring(xml)
    print("=== PANTALLA ACTUAL ===")
    for node in root.iter("node"):
        text = node.attrib.get("text", "").strip()
        rid = node.attrib.get("resource-id", "")
        desc = node.attrib.get("content-desc", "").strip()
        cls = node.attrib.get("class", "").split(".")[-1]
        if rid:
            rid = rid.replace("com.jihuanshe:id/", "")
        if text or rid or desc:
            print(f"[{cls:12}] rid={rid:<28} text={text!r} desc={desc!r}")


if __name__ == "__main__":
    main()
