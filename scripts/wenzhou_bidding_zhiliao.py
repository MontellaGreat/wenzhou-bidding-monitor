#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
温州招标监控（知了标讯 API 版）

当前实现：
1. 通过 v2 按产品关键词（含高级字段）做主检索
2. 通过 v1 标讯正文接口做单条补全
3. 从正文内容中提取地址、联系人、预算、原文链接
4. 对“政府采购意向”做单独标识
5. 联系人与电话号码分字段输出
6. 对字段缺失较多的记录自动降权
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
DEFAULT_DETAIL_LIMIT = int(os.environ.get("ZLBX_DETAIL_LIMIT", "12"))

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
    "宣传", "视频", "活动策划", "策划", "运营服务", "战略合作", "美陈", "文化活动", "会展", "公益电影"
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


def extract_origin_url(content: Dict[str, Any]) -> str:
    if not isinstance(content, dict):
        return "暂无"

    candidate_keys = [
        "sourceUrl", "originUrl", "originalUrl", "url", "href", "uri", "strictUri", "link"
    ]
    for key in candidate_keys:
        value = content.get(key)
        if isinstance(value, str) and value.strip().startswith(("http://", "https://")):
            return value.strip()

    for key in ["content", "html", "body", "text"]:
        value = content.get(key)
        if isinstance(value, str):
            m = re.search(r'https?://[^\s"\'<>]+', value)
            if m:
                return m.group(0)

    return "暂无"


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
        r"地址[：: ]+([^\n]{4,80})",
    ], text)


def extract_budget_from_text(html: str) -> str:
    text = strip_html(html)
    candidates = [
        extract_first([r"预算金额[（(]元[）)]?[：: ]+([0-9,.]+)"], text),
        extract_first([r"预算金额[：: ]+([0-9,.]+万元)"], text),
        extract_first([r"预算金额[：: ]+([0-9,.]+)"], text),
        extract_first([r"拟采购的货物或服务的预算总金额[（(]元[）)]?[：: ]+([0-9,.]+)"], text),
    ]
    for c in candidates:
        if c != "暂无":
            return c
    return "暂无"


def extract_contact_from_text(html: str) -> Dict[str, str]:
    text = strip_html(html)
    person = extract_first([
        r"项目联系人[：: ]+([^\n：:]{1,20})",
        r"联\s*系\s*人[：: ]+([^\n：:]{1,20})",
        r"联系人[：: ]+([^\n：:]{1,20})",
    ], text)
    phone = extract_first([
        r"联系方式[：: ]+([0-9\-]{7,20})",
        r"联系电话[：: ]+([0-9\-]{7,20})",
        r"电\s*话[：: ]+([0-9\-]{7,20})",
    ], text)
    return {"person": person, "phone": phone}


def nullify(value: Any) -> str:
    if value in (None, "", [], {}, "暂无"):
        return "null"
    s = str(value).strip()
    return s if s else "null"


def normalize_money(value: Any) -> str:
    if value in (None, "", [], {}):
        return "null"
    s = str(value).strip()
    if s == "0":
        return "null"
    return s or "null"


def join_keywords(row: Dict[str, Any]) -> str:
    return " ".join([
        row.get("title", "") or "",
        row.get("projectName", "") or "",
        " ".join(row.get("smNames", []) or []),
        " ".join(row.get("matchedKeywords", []) or []),
        row.get("callerName", "") or "",
    ])


def pick_person_phone(items: Any) -> Dict[str, str]:
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                name = str(item.get("name", "")).strip() or "暂无"
                phone = str(item.get("phone", "")).strip() or "暂无"
                if name != "暂无" or phone != "暂无":
                    return {"person": name, "phone": phone}
    return {"person": "暂无", "phone": "暂无"}


def pick_agency_contact(agency: Any) -> Dict[str, str]:
    if isinstance(agency, list):
        for item in agency:
            if not isinstance(item, dict):
                continue
            persons = pick_person_phone(item.get("agencyContactPerson", []))
            agency_name = str(item.get("agencyName", "")).strip() or "暂无"
            if persons["person"] != "暂无" or persons["phone"] != "暂无":
                return persons
            if agency_name != "暂无":
                return {"person": agency_name, "phone": "暂无"}
    return {"person": "暂无", "phone": "暂无"}


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


def detect_notice_type(title: str, source_text: str) -> str:
    hay = f"{title} {source_text}"
    if "采购意向" in hay:
        return "采购意向"
    if "单一来源" in hay:
        return "单一来源"
    if "变更公告" in hay:
        return "变更公告"
    if "招标" in hay or "采购公告" in hay or "资格预审" in hay or "公告" in title:
        return "招标公告"
    if "中标" in hay or "成交" in hay:
        return "中标/成交"
    return "其他"


def missing_fields_penalty(record: Dict[str, str]) -> int:
    penalty = 0
    for key in ["地址", "联系人", "联系方式"]:
        if record.get(key) == "null":
            penalty += 1
    if record.get("项目编号") in ("null", "采购意向无正式编号"):
        penalty += 1
    return penalty


def looks_relevant(item: Dict[str, Any]) -> bool:
    hay = join_keywords(item)
    if not any(k in hay for k in SEARCH_TERMS):
        return False
    if any(bad in hay for bad in NEGATIVE_HINTS):
        return False
    return relevance_tier(item) in ("强相关", "中相关") and compute_score(item) >= 3


def merge_record(row: Dict[str, Any], content: Dict[str, Any]) -> Dict[str, str]:
    base = row
    content_html = ""
    for key in ["content", "html", "body", "text"]:
        value = content.get(key) if isinstance(content, dict) else None
        if isinstance(value, str) and value.strip():
            content_html = value
            break

    caller_contact = pick_person_phone(base.get("callerContactPerson") or row.get("callerContactPerson"))
    agency_contact = pick_agency_contact(base.get("agency") or row.get("agency"))
    text_contact = extract_contact_from_text(content_html) if content_html else {"person": "暂无", "phone": "暂无"}

    chosen = caller_contact
    if chosen["person"] == "暂无" and chosen["phone"] == "暂无":
        chosen = agency_contact
    if chosen["person"] == "暂无" and chosen["phone"] == "暂无":
        chosen = text_contact

    notice_type = detect_notice_type(base.get("title", ""), strip_html(content_html) if content_html else "")
    money = normalize_money(base.get("money") or row.get("money"))
    if money == "null" and content_html:
        money = nullify(extract_budget_from_text(content_html))

    address = "null"
    if content_html:
        address = nullify(extract_address(content_html))

    record = {
        "相关度": relevance_tier(base),
        "公告类型": notice_type,
        "公告名称": nullify(base.get("title") or row.get("title")),
        "采购单位": nullify(base.get("callerName") or row.get("callerName")),
        "项目编号": nullify(base.get("bidNo") or row.get("bidNo") or ("采购意向无正式编号" if notice_type == "采购意向" else None)),
        "发布时间": nullify(base.get("pubTime") or row.get("pubTime")),
        "项目金额（预算）": money,
        "地址": address,
        "联系人": nullify(chosen["person"]),
        "联系方式": nullify(chosen["phone"]),
        "uniqKey": base.get("uniqKey") or row.get("uniqKey") or "",
        "detailUrl": nullify(base.get("zlBidDetailLink") or row.get("zlBidDetailLink") or ""),
        "originUrl": nullify(extract_origin_url(content)),
    }
    record["缺失项数"] = str(missing_fields_penalty(record))
    return record


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
    for row in filtered[:detail_limit * 2]:
        uniq = row.get("uniqKey", "")
        content = {}
        try:
            content = get_bid_content(uniq) if uniq else {}
        except Exception:
            content = {}
        records.append(merge_record(row, content))

    records.sort(key=lambda r: (r["相关度"] != "强相关", int(r["缺失项数"]), r["公告类型"] == "采购意向", r["发布时间"]), reverse=False)
    return records[:detail_limit]


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
            f"{idx}. [{r['相关度']} / {r['公告类型']}]",
            f"公告名称: {r['公告名称']}",
            f"采购单位: {r['采购单位']}",
            f"项目编号: {r['项目编号']}",
            f"发布时间: {r['发布时间']}",
            f"项目金额（预算）: {r['项目金额（预算）']}",
            f"地址：{r['地址']}",
            f"联系人：{r['联系人']}",
            f"联系方式：{r['联系方式']}",
            f"详情链接：{r['detailUrl'] or '暂无'}",
            f"原文链接：{r['originUrl'] or '暂无'}",
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
