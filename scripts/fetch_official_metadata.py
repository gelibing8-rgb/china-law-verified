#!/usr/bin/env python3
"""从国家法律法规数据库核验 laws/ 的官方现行版本（flk.npc.gov.cn）。

背景
----
正文（docx/ofd/pdf）经 flfgDetails 暴露的 OSS 路径分发，但官方对文档
显式设置 permission.download = 0，且对象存储端点为内网主机
（flkoss.obs-bj2-internal.cucloud.cn）。因此正文不可自动补齐，
本脚本不去取，也不尝试绕过。

但**元数据是公开可得的**：flfgDetails 以 GET 返回官方版本沿革
(lsyg)、公布日期(gbrq)、施行日期(sxrq) 与时效性(sxx)。
本脚本据此把「是否仍为官方现行版本」从静态记录变成可每日复验的事实。

合规
----
- 仅访问 sources.yaml 白名单内的 flk.npc.gov.cn；
- 仅调用该站公开页面自身调用的 flfgDetails（GET，无鉴权、无验证码）；
- 不触碰 captchaImage、download/* 等需要授权或被禁用的接口；
- 逐条串行请求并限速，不并发、不轮询。
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "metadata" / "index.jsonl"
RAW_DIR = ROOT / "metadata" / "official-snapshots"
OUT = ROOT / "metadata" / "official-freshness.json"

ALLOWED_HOST = "flk.npc.gov.cn"
DETAILS = "/law-search/search/flfgDetails"

# 官方时效性代码。sxx=3 表示现行有效。
SXX_MEANING = {1: "尚未生效", 2: "已被修改", 3: "现行有效", 4: "已废止", 5: "已失效"}
CURRENT_SXX = 3

UA = "Mozilla/5.0 (Macintosh) china-law-verified/5.0.5 official-metadata-check"


def fetch(bbbs: str, timeout: int = 20) -> dict:
    url = f"https://{ALLOWED_HOST}{DETAILS}?bbbs={urllib.parse.quote(bbbs)}"
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Referer": f"https://{ALLOWED_HOST}/detail.html"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw.decode("utf-8"))


def main() -> int:
    if not INDEX.exists():
        print(f"[FAIL] 缺少 {INDEX}")
        return 2

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    records = [json.loads(l) for l in INDEX.read_text(encoding="utf-8").splitlines() if l.strip()]

    report = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": f"https://{ALLOWED_HOST}{DETAILS}",
        "body_text_note": (
            "正文不可自动获取：官方文档 permission.download=0，"
            "对象存储为内网端点。本脚本仅核验元数据。"
        ),
        "items": [],
        "drift": [],
    }

    for rec in records:
        path = rec.get("path")
        bbbs = rec.get("bbbs")
        if not path or not bbbs:
            report["items"].append({"path": path, "status": "SKIPPED_NO_BBBS"})
            continue

        try:
            payload = fetch(bbbs)
        except Exception as exc:  # noqa: BLE001 - 记录失败而不是中断整体核验
            report["items"].append({"path": path, "bbbs": bbbs, "status": "FETCH_FAILED",
                                    "error": str(exc)})
            print(f"  [FAIL] {path}: 抓取失败 {exc}")
            time.sleep(2)
            continue

        data = payload.get("data") or {}
        # 保存原始响应快照及其 sha256，使核验结论可复现。
        raw_path = RAW_DIR / f"{Path(path).stem}.flfgDetails.json"
        raw_bytes = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")).encode("utf-8")
        raw_path.write_bytes(raw_bytes)

        sxx = data.get("sxx")
        official = {
            "title": data.get("title"),
            "gbrq": data.get("gbrq"),
            "sxrq": data.get("sxrq"),
            "sxx": sxx,
            "sxx_meaning": SXX_MEANING.get(sxx),
            "version_count": len(data.get("lsyg") or []),
            "issuing_authority": data.get("zdjgName"),
        }
        item = {
            "path": path,
            "bbbs": bbbs,
            "status": "OK",
            "official": official,
            "snapshot": str(raw_path.relative_to(ROOT)),
            "snapshot_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "stored": {
                "title": rec.get("title"),
                "current_version_date": rec.get("current_version_date"),
                "current_version_effective_date": rec.get("current_version_effective_date"),
            },
        }

        mismatches = []
        if official["title"] != rec.get("title"):
            mismatches.append(f"title: 官方={official['title']!r} 本地={rec.get('title')!r}")
        if official["gbrq"] and rec.get("current_version_date") and \
                official["gbrq"] != rec.get("current_version_date"):
            mismatches.append(
                f"current_version_date: 官方={official['gbrq']} 本地={rec.get('current_version_date')}")
        if official["sxrq"] and rec.get("current_version_effective_date") and \
                official["sxrq"] != rec.get("current_version_effective_date"):
            mismatches.append(
                f"current_version_effective_date: 官方={official['sxrq']} "
                f"本地={rec.get('current_version_effective_date')}")
        if sxx != CURRENT_SXX:
            mismatches.append(f"时效性: sxx={sxx} ({SXX_MEANING.get(sxx)})，非现行有效")

        item["mismatches"] = mismatches
        item["verdict"] = "CURRENT_MATCH" if not mismatches else "DRIFT"
        if mismatches:
            report["drift"].append({"path": path, "mismatches": mismatches})

        report["items"].append(item)
        mark = "OK " if not mismatches else "DRIFT"
        print(f"  [{mark}] {path}: 官方 {official['title']} "
              f"gbrq={official['gbrq']} sxrq={official['sxrq']} "
              f"sxx={sxx}({official['sxx_meaning']}) 版本数={official['version_count']}")
        for m in mismatches:
            print(f"         - {m}")
        time.sleep(2)

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + chr(10),
                   encoding="utf-8")

    n = len(report["items"])
    print(f"核验 {n} 部法律；漂移 {len(report['drift'])} 部 -> {OUT.relative_to(ROOT)}")
    if report["drift"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
