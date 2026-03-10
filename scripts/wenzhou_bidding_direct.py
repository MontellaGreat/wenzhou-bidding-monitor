#!/usr/bin/env python3
"""
温州本地招投标监控 - 直接发送到飞书
不经过AI总结，直接发送标准格式
"""

import http.client
import json
import re
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os
from urllib.parse import quote

# API 配置
API_KEY = "8ra2g7qdr5ejvwwyoiuon2okscmufbzt"
FEISHU_USER_ID = "ou_1e914047483f105cfd57f14f0db20746"

# 精简关键词列表
KEYWORDS = ["视频", "宣传片", "公众号", "体育", "活动"]

# 温州市及区县代码
WENZHOU_CODES = {
    "330300": "温州市", "330302": "鹿城区", "330303": "龙湾区",
    "330304": "瓯海区", "330305": "洞头区", "330324": "永嘉县",
    "330326": "平阳县", "330327": "苍南县", "330328": "文成县",
    "330329": "泰顺县", "330381": "瑞安市", "330382": "乐清市"
}


def get_project_detail(project_id: str, publish_time: str) -> Optional[Dict[str, Any]]:
    """获取项目详情"""
    try:
        conn = http.client.HTTPSConnection("23330.o.apispace.com")
        encoded_time = quote(publish_time)
        payload = f"id={project_id}&publishTime={encoded_time}"
        headers = {
            "X-APISpace-Token": API_KEY,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        conn.request("POST", "/project-info-upgrade/detail", payload, headers)
        res = conn.getresponse()
        data = res.read()
        result = json.loads(data.decode("utf-8"))
        if result.get("code") == 200:
            return result.get("data", {})
        return None
    except:
        return None
    finally:
        conn.close()


def extract_contact_info(content: str) -> Dict[str, str]:
    """从content中提取地址和联系方式"""
    result = {"address": "暂无", "contact": "暂无"}
    if not content:
        return result
    
    content = re.sub(r'<[^>]+>', '', content)
    
    # 提取地址
    for pattern in [r'地\s*址[：:]\s*([^\n\r]+)', r'联系地址[：:]\s*([^\n\r]+)']:
        match = re.search(pattern, content)
        if match:
            address = match.group(1).strip()
            if len(address) > 5 and '温州' in address:
                result["address"] = address
                break
    
    # 提取联系方式
    for pattern in [r'联系电话[：:]\s*([0-9\-\s]+)', r'联系方式[：:]\s*([0-9\-\s]+)']:
        match = re.search(pattern, content)
        if match:
            contact = match.group(1).strip()
            if re.match(r'^[0-9\-\s]{7,}$', contact):
                result["contact"] = contact
                break
    
    return result


def extract_origin_link(content: str) -> str:
    """从正文内容中提取原文链接"""
    if not content:
        return "暂无"
    matches = re.findall(r'https?://[^\s"\'<>]+', content)
    if not matches:
        return "暂无"
    # 优先返回非知了 detail 链接
    for url in matches:
        if 'zhiliaobiaoxun.com/detail/' not in url:
            return url
    return matches[0]


def search_wenzhou_projects(days=60) -> List[Dict[str, Any]]:
    """搜索温州本地项目"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    all_results = []
    
    for keyword in KEYWORDS:
        conn = http.client.HTTPSConnection("23330.o.apispace.com")
        payload = {
            "keyword": keyword,
            "searchMode": 1,
            "areaCode": {"ProviceCodeList": ["330000"], "CityCodeList": ["330300"], "CuntyCodeList": []},
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "userID": 2,
            "pageID": 1,
            "pageNumber": 20,
            "searchType": 1,
            "industryCode": {"firstCodeList": ["0"], "secondCodeList": [], "thirdCodeList": []},
            "projectClassID": "-100",
            "purchaseTypeID": "-100",
            "projectMoneyMin": 0,
            "projectMoneyMax": 0
        }
        headers = {"X-APISpace-Token": API_KEY, "Content-Type": "application/json"}
        
        try:
            conn.request("POST", "/project-info-upgrade/project-list", json.dumps(payload), headers)
            res = conn.getresponse()
            data = res.read()
            result = json.loads(data.decode("utf-8"))
            
            if result.get("code") == 200:
                projects = result.get("data", {}).get("data", [])
                for project in projects:
                    city_code = project.get("cityCode", "")
                    title = project.get("title", "") or ""
                    content = project.get("content", "") or ""
                    if city_code in WENZHOU_CODES or "温州" in title or "温州" in content:
                        if not any(p.get("id") == project.get("id") for p in all_results):
                            all_results.append(project)
        except:
            pass
        finally:
            conn.close()
    
    return all_results


def format_message(projects: List[Dict[str, Any]]) -> str:
    """格式化为标准格式"""
    if not projects:
        return "⚠️ 未找到温州本地项目"
    
    projects.sort(key=lambda x: x.get("publishTime", ""), reverse=True)
    lines = []
    project_count = len(projects)
    
    if project_count <= 3:
        # 自动查询详情
        for project in projects:
            title = project.get("title", "N/A").replace("<span style='color:red;'>", "").replace("</span>", "")
            part_a = ", ".join(project.get("partANameList", [])) or "N/A"
            project_id = str(project.get("id", ""))
            publish_time = project.get("publishTime", "")
            
            lines.append(f"公告名称: {title}")
            lines.append(f"采购单位: {part_a}")
            lines.append(f"项目编号: {project_id}")
            lines.append(f"发布时间: {publish_time}")
            lines.append(f"项目金额（预算）: {project.get('projectMoney', '暂无')}")
            
            if project_id and publish_time:
                detail = get_project_detail(project_id, publish_time)
                if detail:
                    content = detail.get("content", "")
                    contact_info = extract_contact_info(content)
                    origin_link = extract_origin_link(content)
                    lines.append(f"地址: {contact_info['address']}")
                    lines.append(f"联系方式: {contact_info['contact']}")
                    lines.append(f"原文链接: {origin_link}")
                else:
                    lines.append("地址: 查询失败")
                    lines.append("联系方式: 查询失败")
                    lines.append("原文链接: 查询失败")
            else:
                lines.append("地址: 无法查询")
                lines.append("联系方式: 无法查询")
                lines.append("原文链接: 无法查询")
            
            lines.append("-" * 50)
    else:
        # 只显示基本信息
        for project in projects[:15]:
            title = project.get("title", "N/A").replace("<span style='color:red;'>", "").replace("</span>", "")
            part_a = ", ".join(project.get("partANameList", [])) or "N/A"
            
            lines.append(f"公告名称: {title}")
            lines.append(f"采购单位: {part_a}")
            lines.append(f"项目编号: {project.get('id', 'N/A')}")
            lines.append(f"发布时间: {project.get('publishTime', 'N/A')}")
            lines.append(f"项目金额（预算）: {project.get('projectMoney', '暂无')}")
            lines.append("-" * 50)
    
    return "\n".join(lines)


def send_to_feishu(message: str):
    """直接发送到飞书"""
    try:
        subprocess.run([
            "openclaw", "message", "send",
            "--channel", "feishu",
            "--target", FEISHU_USER_ID,
            "--message", message
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        print(f"发送失败: {e}")


def main():
    """主函数"""
    projects = search_wenzhou_projects(days=60)
    message = format_message(projects)
    send_to_feishu(message)
    print("✅ 已发送到飞书")


if __name__ == "__main__":
    main()
