#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
温州招标监控（知了标讯 API 版）

当前实现：
1. 通过 v2 按产品关键词（含高级字段）做主检索
2. 通过 v2 单个标讯（含高级字段）做精修补全
3. 通过 v1 标讯正文兜底补地址
4. 输出为用户指定的简洁格式
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta
from html import unescape
from typing import Any, Dict, List, Tuple

import requests

SANDBOX_URL = "https://user-open-website.zhiliaobiaoxun.com/sandbox/test_v2"
APP_ID = os.environ.get("ZLBX_APP_ID", "202603081480343542189522944")
APP_SECRET = os.environ.get("ZLBX_APP_SECRET", "dbb6bb44741c4066a4025e284145fce0")
ZLBX_TOKEN = os.environ.get("ZLBX_TOKEN", "")

DISPLAY_KEYWORDS = ["活动", "图文", "公众号", "视频制作", "宣传片"]
SEARCH_TERMS = ["活动", "图文", "公众号", "视频制作", "宣传片", "宣传", "拍摄", "新媒体", "运营", "策划", "美陈"]
PROVINCE = "浙江"
CITY = "温州"
DEFAULT_DAYS = int(os.environ.get("ZLBX_DAYS", "7"))
DEFAULT_LIMIT = int(os.environ.get("ZLBX_LIMIT", "30"))
DEFAULT_DETAIL_LIMIT = int(os.environ.get("ZLBX_DETAIL_LIMIT", "8"))

NEGATIVE_HINTS = [
    "摄像头", "监控设备", "安防", "LED", "广播系统", "电视机", "电脑", "网络设备",
    "球场建设", "疗休养", "疗养项目", "职工疗养", "勘察设计", "工程设计", "施工", "排涝工程",
    "绿道", "道路", "围墙", "开关柜", "断路器", "耗材", "空港大道", "基础配套设施", "设备采购",
    "建筑运营", "园艺植物", "生态绿道", "物业", "园林", "硬件"
]
STRONG_HINTS = [
    "宣传片", "视频制作", "公众号", "新媒体", "图文", "拍摄", "会务", "会议策划", "美陈制作", "宣传部"
]
MEDIUM_HINTS = [
    "宣传", "视频", "活动策划", "策划", "运营服务", "战略合作", "美陈", "文化活动", "会展"
]
WEAK_HINTS = [
    "活动", "运营", "合作", "服务", "设计"
]

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0",
})


class ZLBXError(Exception):
    pass


def require_token() -> str:
    if not ZLBX_TOKEN:
        raise ZLBXError("缺少 ZLBX_TOKEN。请先在开放平台登录后，从 localStorage 的 zlbxkfpt-token 取值，并导出环境变量。")
    return ZLBX_TOKEN


def sandbox_call(method: str, biz_content: Dict[str, Any], version: str = "1.0") -> Dict[str, Any]:
    token = require_token()
    payload = {
        "gatewayUrl": "https://open.zhiliaobiaoxun.com",
        "method": method,
        "appId": APP_ID,
        "appSecret": APP_SECRET,
        "version": version,
        "bizContent": json.dumps(biz_content, ensure_ascii=False),
    }
    resp = SESSION.post(SANDBOX_URL, headers={"token": token}, data=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    api_key = method.replace(".", "_") + "_response"
    api_resp = data.get(api_key)
    if not api_resp:
        raise ZLBXError(f"接口返回异常：{data}")
    if str(api_resp.get("code")) != "10000":
        raise ZLBXError(f"接口调用失败：{api_resp.get('code')} {api_resp.get('msg')} {api_resp.get('sub_msg', '')}")
    return api_resp


def search_bids(days: int = DEFAULT_DAYS, limit: int = DEFAULT_LIMIT) -> List[Dict[str, Any]]:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    biz = {
        "subjectMatter": ",".join(SEARCH_TERMS),
        "province": PROVINCE,
        "city": CITY,
        "startTime": start_date.strftime("%Y-%m-%d"),
        "endTime": end_date.strftime("%Y-%m-%d"),
        "matchMode": 1,
        "matchType": 3,
        "page": 1,
        "limit": limit,
    }
    result = sandbox_call("v2.api.subject.matter.bid.get", biz)
    return result.get("data", [])


def get_bid_detail(uniq_key: str) -> Dict[str, Any]:
    result = sandbox_call("v2.api.uk.bid.get", {"uniqKey": uniq_key})
    return result.get("data", {})


def get_bid_content(uniq_key: str) -> Dict[str, Any]:
    result = sandbox_call("v1.api.content.bid.get", {"uniqKey": uniq_key, "strictUri": 0})
    return result.get("data", {})


def strip_html(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>|</li>|</tr>|</div>|</h\d>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def extract_first(patterns: List[str], text: str, flags=re.I) -> str:
    for pat in patterns:
        m = re.search(pat, text, flags)
        if m:
            value = re.sub(r"\s+", " ", m.group(1).strip())
            if value:
                return value
    return "暂无"


def extract_address(html: str) -> str:
    text = strip_html(html)
    return extract_first([
        r"(?:采购人|采购单位)?地\s*址[：: ]+([^\n]{4,80})",
        r"联系地址[：: ]+([^\n]{4,80})",
        r"开标地点[：: ]+([^\n]{4,80})",
        r"项目地点[：: ]+([^\n]{4,80})",
        r"递交地点[：: ]+([^\n]{4,80})",
    ], text)


def normalize_money(value: Any) -> str:
    if value in (None, "", [], {}):
        return "暂无"
    s = str(value).strip()
    if s == "0":
        return "暂无"
    return s or "暂无"


def join_keywords(row: Dict[str, Any]) -> str:
    return " ".join([
        row.get("title", "") or "",
        row.get("projectName", "") or "",
        " ".join(row.get("smNames", []) or []),
        " ".join(row.get("matchedKeywords", []) or []),
        row.get("callerName", "") or "",
    ])


def pick_first_phone(items: Any) -> str:
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                name = str(item.get("name", "")).strip()
                phone = str(item.get("phone", "")).strip()
                if phone and name:
                    return f"{name} {phone}"
                if phone:
                    return phone
                if name:
                    return name
    return "暂无"


def pick_agency_contact(agency: Any) -> str:
    if isinstance(agency, list):
        for item in agency:
            if not isinstance(item, dict):
                continue
            agency_name = str(item.get("agencyName", "")).strip()
            person = pick_first_phone(item.get("agencyContactPerson", []))
            if agency_name and person != "暂无":
                return f"{agency_name} / {person}"
            if person != "暂无":
                return person
            if agency_name:
                return agency_name
    return "暂无"


def score_terms(hay: str) -> Tuple[int, str]:
    score = 0
    strong_hits = [w for w in STRONG_HINTS if w in hay]
    medium_hits = [w for w in MEDIUM_HINTS if w in hay]
    weak_hits = [w for w in WEAK_HINTS if w in hay]
    negative_hits = [w for w in NEGATIVE_HINTS if w in hay]

    score += len(strong_hits) * 6
    score += len(medium_hits) * 3
    score += len(weak_hits) * 1
    score -= len(negative_hits) * 8

    if strong_hits:
        tier = "强相关"
    elif medium_hits:
        tier = "中相关"
    elif weak_hits:
        tier = "弱相关"
    else:
        tier = "无关"
    return score, tier


def compute_score(item: Dict[str, Any]) -> int:
    hay = join_keywords(item)
    score, _ = score_terms(hay)
    if item.get("callerContactPerson"):
        score += 2
    if normalize_money(item.get("money")) != "暂无":
        score += 1
    if item.get("callerName") and any(x in (item.get("callerName") or "") for x in ["宣传部", "日报", "文旅", "体育", "传媒", "运营"]):
        score += 2
    return score


def relevance_tier(item: Dict[str, Any]) -> str:
    _, tier = score_terms(join_keywords(item))
    return tier


def looks_relevant(item: Dict[str, Any]) -> bool:
    hay = join_keywords(item)
    if not any(k in hay for k in SEARCH_TERMS):
        return False
    if any(bad in hay for bad in NEGATIVE_HINTS):
        return False
    return relevance_tier(item) in ("强相关", "中相关") and compute_score(item) >= 3


def merge_record(row: Dict[str, Any], detail: Dict[str, Any], content: Dict[str, Any]) -> Dict[str, str]:
    caller_contact = pick_first_phone(detail.get("callerContactPerson") or row.get("callerContactPerson"))
    agency_contact = pick_agency_contact(detail.get("agency") or row.get("agency"))
    merged_contact = caller_contact if caller_contact != "暂无" else agency_contact
    address = extract_address(content.get("content", "")) if content else "暂无"
    base = detail or row
    return {
        "相关度": relevance_tier(base),
        "公告名称": base.get("title") or row.get("title") or "暂无",
        "采购单位": base.get("callerName") or row.get("callerName") or "暂无",
        "项目编号": base.get("bidNo") or row.get("bidNo") or "暂无",
        "发布时间": base.get("pubTime") or row.get("pubTime") or "暂无",
        "项目金额（预算）": normalize_money(base.get("money") or row.get("money")),
        "地址": address,
        "联系方式": merged_contact,
        "uniqKey": base.get("uniqKey") or row.get("uniqKey") or "",
        "sourceUrl": (content or {}).get("sourceUrl", "") or base.get("zlBidDetailLink") or row.get("zlBidDetailLink") or "",
    }


def build_records(days: int = DEFAULT_DAYS, limit: int = DEFAULT_LIMIT, detail_limit: int = DEFAULT_DETAIL_LIMIT) -> List[Dict[str, str]]:
    rows = search_bids(days=days, limit=limit)
    rows = [r for r in rows if looks_relevant(r)]
    rows.sort(key=lambda x: (relevance_tier(x) != "强相关", -compute_score(x), x.get("pubTime", "")), reverse=False)
    seen = set()
    filtered = []
    for row in rows:
        uniq = row.get("uniqKey")
        if uniq and uniq not in seen:
            seen.add(uniq)
            filtered.append(row)

    records = []
    for row in filtered[:detail_limit]:
        uniq = row.get("uniqKey", "")
        detail = row
        try:
            detail = get_bid_detail(uniq) if uniq else row
        except Exception:
            detail = row
        content = {}
        try:
            content = get_bid_content(uniq) if uniq else {}
        except Exception:
            content = {}
        records.append(merge_record(row, detail, content))
    return records


def format_records(records: List[Dict[str, str]]) -> str:
    if not records:
        return (
            "温州招标监控（知了标讯）\n"
            "本次未发现符合关键词的公告。\n"
            f"关键词：{','.join(DISPLAY_KEYWORDS)}\n"
            f"地区：{PROVINCE} / {CITY}"
        )
    parts = ["温州招标监控（知了标讯）"]
    for idx, r in enumerate(records, 1):
        parts.extend([
            "",
            f"{idx}. [{r['相关度']}]",
            f"公告名称: {r['公告名称']}",
            f"采购单位: {r['采购单位']}",
            f"项目编号: {r['项目编号']}",
            f"发布时间: {r['发布时间']}",
            f"项目金额（预算）: {r['项目金额（预算）']}",
            f"地址：{r['地址']}",
            f"联系方式：{r['联系方式']}",
        ])
    return "\n".join(parts)


def main() -> int:
    try:
        records = build_records()
        print(format_records(records))
        return 0
    except Exception as e:
        print(f"❌ 运行失败: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
