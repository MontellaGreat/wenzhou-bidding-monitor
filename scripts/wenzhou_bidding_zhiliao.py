#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
温州招标监控（知了标讯 API 版）

当前实现：
1. 通过知了标讯开放平台调试沙箱接口检索候选公告
2. 通过“单个标讯(含高级字段)”接口补全结构化字段
3. 通过“标讯正文”接口兜底补地址和联系方式
4. 输出为用户指定的简洁格式
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta
from html import unescape
from typing import Any, Dict, List

import requests

SANDBOX_URL = "https://user-open-website.zhiliaobiaoxun.com/sandbox/test_v2"
APP_ID = os.environ.get("ZLBX_APP_ID", "202603081480343542189522944")
APP_SECRET = os.environ.get("ZLBX_APP_SECRET", "dbb6bb44741c4066a4025e284145fce0")
ZLBX_TOKEN = os.environ.get("ZLBX_TOKEN", "")

KEYWORDS = ["活动", "图文", "公众号", "视频制作", "宣传片"]
PROVINCE = "浙江"
CITY = "温州"
DEFAULT_DAYS = int(os.environ.get("ZLBX_DAYS", "3"))
DEFAULT_LIMIT = int(os.environ.get("ZLBX_LIMIT", "20"))
DEFAULT_DETAIL_LIMIT = int(os.environ.get("ZLBX_DETAIL_LIMIT", "8"))

NEGATIVE_HINTS = [
    "摄像头", "监控设备", "安防", "LED", "广播系统", "电视机", "电脑", "网络设备",
    "球场建设", "疗休养", "疗养项目", "职工疗养"
]
PREFERRED_HINTS = [
    "宣传", "视频", "图文", "公众号", "新媒体", "活动", "拍摄", "制作", "运营", "设计"
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
        "subjectMatter": ",".join(KEYWORDS),
        "province": PROVINCE,
        "city": CITY,
        "startTime": start_date.strftime("%Y-%m-%d"),
        "endTime": end_date.strftime("%Y-%m-%d"),
        "matchMode": 1,
        "matchType": 3,
        "page": 1,
        "limit": limit,
    }
    result = sandbox_call("v1.api.subject.matter.bid.free.get", biz)
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


def extract_contact_info(html: str) -> Dict[str, str]:
    text = strip_html(html)
    address = extract_first([
        r"(?:采购人|采购单位)?地\s*址[：: ]+([^\n]{4,80})",
        r"联系地址[：: ]+([^\n]{4,80})",
        r"开标地点[：: ]+([^\n]{4,80})",
        r"项目地点[：: ]+([^\n]{4,80})",
    ], text)
    phone = extract_first([
        r"联系方式[：: ]+([0-9\-]{7,20})",
        r"联系电话[：: ]+([0-9\-]{7,20})",
        r"电\s*话[：: ]+([0-9\-]{7,20})",
        r"项目联系人[\s\S]{0,20}?([0-9\-]{7,20})",
    ], text)
    person = extract_first([
        r"项目联系人[：: ]+([^\n：:]{1,20})",
        r"联\s*系\s*人[：: ]+([^\n：:]{1,20})",
    ], text)
    if phone != "暂无" and person != "暂无":
        contact = f"{person} {phone}"
    elif phone != "暂无":
        contact = phone
    else:
        contact = person
    return {"address": address, "contact": contact or "暂无", "text": text}


def normalize_money(value: Any) -> str:
    if value in (None, "", [], {}):
        return "暂无"
    s = str(value).strip()
    return s or "暂无"


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
            persons = item.get("agencyContactPerson", [])
            person = pick_first_phone(persons)
            if agency_name and person != "暂无":
                return f"{agency_name} / {person}"
            if person != "暂无":
                return person
            if agency_name:
                return agency_name
    return "暂无"


def compute_score(item: Dict[str, Any]) -> int:
    hay = " ".join([
        item.get("title", "") or "",
        " ".join(item.get("smNames", []) or []),
        " ".join(item.get("matchedKeywords", []) or []),
    ])
    score = 0
    for word in PREFERRED_HINTS:
        if word in hay:
            score += 2
    for bad in NEGATIVE_HINTS:
        if bad in hay:
            score -= 5
    return score


def looks_relevant(item: Dict[str, Any]) -> bool:
    hay = " ".join([
        item.get("title", "") or "",
        " ".join(item.get("smNames", []) or []),
        " ".join(item.get("matchedKeywords", []) or []),
    ])
    if not any(k in hay for k in KEYWORDS):
        return False
    if any(bad in hay for bad in NEGATIVE_HINTS):
        return False
    return compute_score(item) >= 2


def merge_record(row: Dict[str, Any], detail: Dict[str, Any], content: Dict[str, Any]) -> Dict[str, str]:
    html = content.get("content", "") if content else ""
    extracted = extract_contact_info(html) if html else {"address": "暂无", "contact": "暂无"}

    caller_contact = pick_first_phone(detail.get("callerContactPerson"))
    agency_contact = pick_agency_contact(detail.get("agency"))
    merged_contact = caller_contact if caller_contact != "暂无" else agency_contact
    if merged_contact == "暂无":
        merged_contact = extracted.get("contact", "暂无")

    address = extracted.get("address", "暂无")

    return {
        "公告名称": detail.get("title") or row.get("title") or "暂无",
        "采购单位": detail.get("callerName") or row.get("callerName") or "暂无",
        "项目编号": detail.get("bidNo") or row.get("bidNo") or "暂无",
        "发布时间": detail.get("pubTime") or row.get("pubTime") or "暂无",
        "项目金额（预算）": normalize_money(detail.get("money") or row.get("money")),
        "地址": address,
        "联系方式": merged_contact,
        "uniqKey": detail.get("uniqKey") or row.get("uniqKey") or "",
        "sourceUrl": content.get("sourceUrl", "") if content else "",
    }


def build_records(days: int = DEFAULT_DAYS, limit: int = DEFAULT_LIMIT, detail_limit: int = DEFAULT_DETAIL_LIMIT) -> List[Dict[str, str]]:
    rows = search_bids(days=days, limit=limit)
    rows = [r for r in rows if looks_relevant(r)]
    rows.sort(key=compute_score, reverse=True)
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
        detail = {}
        content = {}
        try:
            detail = get_bid_detail(uniq) if uniq else {}
        except Exception:
            detail = {}
        try:
            need_fallback = not detail.get("callerContactPerson")
            content = get_bid_content(uniq) if uniq and need_fallback else {}
        except Exception:
            content = {}
        records.append(merge_record(row, detail, content))
    return records


def format_records(records: List[Dict[str, str]]) -> str:
    if not records:
        return (
            "温州招标监控（知了标讯）\n"
            "本次未发现符合关键词的公告。\n"
            f"关键词：{','.join(KEYWORDS)}\n"
            f"地区：{PROVINCE} / {CITY}"
        )
    parts = ["温州招标监控（知了标讯）"]
    for idx, r in enumerate(records, 1):
        parts.extend([
            "",
            f"{idx}.",
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
