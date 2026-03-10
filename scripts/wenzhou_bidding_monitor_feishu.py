#!/usr/bin/env python3
"""
温州本地招投标监控 - 飞书通知版
输出标准格式，直接发送到飞书
"""

import http.client
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os
from urllib.parse import quote

# API 配置
API_KEY = os.environ.get("APISPACE_API_KEY", "8ra2g7qdr5ejvwwyoiuon2okscmufbzt")

# 精简关键词列表
KEYWORDS = [
    "视频",          # 视频制作相关
    "宣传片",        # 核心业务
    "公众号",        # 新媒体运营
    "体育",          # 体育赛事
    "活动"           # 活动拍摄
]

# 温州市及区县代码
WENZHOU_CODES = {
    "330300": "温州市",
    "330302": "鹿城区",
    "330303": "龙湾区",
    "330304": "瓯海区",
    "330305": "洞头区",
    "330324": "永嘉县",
    "330326": "平阳县",
    "330327": "苍南县",
    "330328": "文成县",
    "330329": "泰顺县",
    "330381": "瑞安市",
    "330382": "乐清市"
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
        else:
            return None
    
    except Exception as e:
        return None
    
    finally:
        conn.close()


def extract_contact_info(content: str) -> Dict[str, str]:
    """从content中提取地址和联系方式"""
    result = {"address": "暂无", "contact": "暂无"}
    
    if not content:
        return result
    
    # 清理HTML标签
    content = re.sub(r'<[^>]+>', '', content)
    
    # 提取地址
    address_patterns = [
        r'地\s*址[：:]\s*([^\n\r]+)',
        r'联系地址[：:]\s*([^\n\r]+)',
        r'详细地址[：:]\s*([^\n\r]+)',
        r'项目地址[：:]\s*([^\n\r]+)',
        r'采购单位地址[：:]\s*([^\n\r]+)',
    ]
    
    for pattern in address_patterns:
        match = re.search(pattern, content)
        if match:
            address = match.group(1).strip()
            if len(address) > 5 and '温州' in address:
                result["address"] = address
                break
    
    # 提取联系方式
    contact_patterns = [
        r'联系电话[：:]\s*([0-9\-\s]+)',
        r'联系方式[：:]\s*([0-9\-\s]+)',
        r'电\s*话[：:]\s*([0-9\-\s]+)',
        r'手\s*机[：:]\s*([0-9\-\s]+)',
        r'联系人[：:][^0-9]*([0-9\-\s]+)',
    ]
    
    for pattern in contact_patterns:
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
    for url in matches:
        if 'zhiliaobiaoxun.com/detail/' not in url:
            return url
    return matches[0]


def search_wenzhou_projects(days=60, max_per_keyword=20) -> List[Dict[str, Any]]:
    """搜索温州本地项目"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    all_results = []
    
    for keyword in KEYWORDS:
        conn = http.client.HTTPSConnection("23330.o.apispace.com")
        
        payload = {
            "keyword": keyword,
            "excludeKW": None,
            "inCludeKW": None,
            "searchMode": 1,
            "areaCode": {
                "ProviceCodeList": ["330000"],
                "CityCodeList": ["330300"],
                "CuntyCodeList": []
            },
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "userID": 2,
            "pageID": 1,
            "pageNumber": max_per_keyword,
            "searchType": 1,
            "industryCode": {
                "firstCodeList": ["0"],
                "secondCodeList": [],
                "thirdCodeList": []
            },
            "projectClassID": "-100",
            "purchaseTypeID": "-100",
            "projectMoneyMin": 0,
            "projectMoneyMax": 0
        }
        
        headers = {
            "X-APISpace-Token": API_KEY,
            "Content-Type": "application/json"
        }
        
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
        
        except Exception as e:
            pass
        
        finally:
            conn.close()
    
    return all_results


def format_output(projects: List[Dict[str, Any]]) -> str:
    """格式化输出为标准格式"""
    if not projects:
        return "⚠️ 未找到温州本地项目"
    
    # 按发布时间排序
    projects.sort(key=lambda x: x.get("publishTime", ""), reverse=True)
    
    project_count = len(projects)
    output_lines = []
    
    # 如果项目≤3个，自动查询详情
    if project_count <= 3:
        for project in projects:
            title = project.get("title", "N/A")
            title = title.replace("<span style='color:red;'>", "").replace("</span>", "")
            
            part_a_list = project.get("partANameList", [])
            part_a = ", ".join(part_a_list) if part_a_list else "N/A"
            
            project_id = str(project.get("id", ""))
            publish_time = project.get("publishTime", "")
            
            output_lines.append(f"公告名称: {title}")
            output_lines.append(f"采购单位: {part_a}")
            output_lines.append(f"项目编号: {project_id}")
            output_lines.append(f"发布时间: {publish_time}")
            output_lines.append(f"项目金额（预算）: {project.get('projectMoney', '暂无')}")
            
            # 查询详情
            if project_id and publish_time:
                detail = get_project_detail(project_id, publish_time)
                
                if detail:
                    content = detail.get("content", "")
                    contact_info = extract_contact_info(content)
                    origin_link = extract_origin_link(content)
                    
                    output_lines.append(f"地址: {contact_info['address']}")
                    output_lines.append(f"联系方式: {contact_info['contact']}")
                    output_lines.append(f"原文链接: {origin_link}")
                else:
                    output_lines.append(f"地址: 查询失败")
                    output_lines.append(f"联系方式: 查询失败")
                    output_lines.append(f"原文链接: 查询失败")
            else:
                output_lines.append(f"地址: 无法查询")
                output_lines.append(f"联系方式: 无法查询")
                output_lines.append(f"原文链接: 无法查询")
            
            output_lines.append("-" * 50)
    
    else:
        # 项目>3个，只显示基本信息
        for project in projects[:15]:
            title = project.get("title", "N/A")
            title = title.replace("<span style='color:red;'>", "").replace("</span>", "")
            
            part_a_list = project.get("partANameList", [])
            part_a = ", ".join(part_a_list) if part_a_list else "N/A"
            
            output_lines.append(f"公告名称: {title}")
            output_lines.append(f"采购单位: {part_a}")
            output_lines.append(f"项目编号: {project.get('id', 'N/A')}")
            output_lines.append(f"发布时间: {project.get('publishTime', 'N/A')}")
            output_lines.append(f"项目金额（预算）: {project.get('projectMoney', '暂无')}")
            output_lines.append("-" * 50)
    
    return "\n".join(output_lines)


def main():
    """主函数"""
    # 搜索项目
    projects = search_wenzhou_projects(days=60, max_per_keyword=20)
    
    # 格式化输出
    output = format_output(projects)
    
    # 直接打印（会被发送到飞书）
    print(output)
    
    # 保存结果
    if projects:
        output_file = "/home/admin/.openclaw/workspace/wenzhou_bidding_results.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(projects, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
