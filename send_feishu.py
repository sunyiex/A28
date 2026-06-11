#!/usr/bin/env python3
"""
将二八分化数据发送到飞书群机器人

使用方式：
  python3 erba_stats.py --format json > /tmp/erba.json
  python3 send_feishu.py /tmp/erba.json
"""

import json
import sys
import os
import requests


def build_feishu_card(data):
    """构建飞书消息卡片"""
    indexes = data.get("指数", [])
    period = data.get("统计周期", 20)
    date_label = data.get("数据日期", data.get("查询日期", ""))

    # 构建表格行
    elements = []

    # --- 标题区 ---
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"**📊 A股 二八分化 | {date_label} | 近{period}日涨跌幅**"
        }
    })

    # --- 概要指标 ---
    avg_er = data.get("大盘平均")
    avg_ba = data.get("小盘平均")
    diff = data.get("二八差距")

    summary_text = ""
    if avg_er is not None:
        summary_text += f"🏛️ 大盘(二)均值: **{avg_er:+.2f}%**\n"
    if avg_ba is not None:
        summary_text += f"📈 小盘(八)均值: **{avg_ba:+.2f}%**\n"
    if diff is not None:
        diff_label = "明显分化(大盘抗跌)" if diff > 1 else ("弱分化" if diff > 0 else "小盘占优")
        summary_text += f"📏 二八差距: **{diff:+.2f}%** ({diff_label})"

    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": summary_text}
    })

    elements.append({"tag": "hr"})

    # --- 指数表格 ---
    for idx in indexes:
        pct = idx.get("涨跌幅(%)")
        name = idx["指数名称"]
        cat = idx["分类"]
        tag = "【二】" if cat == "二" else "【八】"
        sign = "🔴" if pct and pct < 0 else "🟢"
        price = idx.get("收盘价", "")

        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"{tag} {name:8s}  {sign} **{pct:+.2f}%**  (收盘 {price})"
            }
        })

    elements.append({"tag": "hr"})

    # 最佳/最差
    if indexes:
        best = max(indexes, key=lambda r: r.get("涨跌幅(%)", 0))
        worst = min(indexes, key=lambda r: r.get("涨跌幅(%)", 0))
        if best and worst:
            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"🏆 最强: {best['指数名称']} ({best['涨跌幅(%)']:+.2f}%)\n🪦 最弱: {worst['指数名称']} ({worst['涨跌幅(%)']:+.2f}%)"
                }
            })

    # 注脚
    elements.append({
        "tag": "note",
        "text": {
            "tag": "plain_text",
            "content": f"数据来源: akshare (东方财富) | 自动推送 @ {data.get('查询日期', '')}"
        }
    })

    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"📊 A股 二八分化 | {date_label}"},
            "template": "blue"
        },
        "elements": elements
    }

    return card


def send_to_feishu(webhook_url, card):
    """发送飞书消息"""
    payload = {
        "msg_type": "interactive",
        "card": card
    }
    resp = requests.post(webhook_url, json=payload, timeout=15)
    result = resp.json()
    if result.get("code") == 0:
        print(f"✅ 飞书发送成功 (code=0)")
    else:
        print(f"❌ 飞书发送失败: {result}")
    return result


def main():
    if len(sys.argv) < 2:
        print("用法: python3 send_feishu.py <json_file>")
        sys.exit(1)

    json_path = sys.argv[1]
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 从环境变量或参数获取 webhook
    webhook_url = os.environ.get("FEISHU_WEBHOOK", "")
    if not webhook_url:
        print("❌ 请设置 FEISHU_WEBHOOK 环境变量")
        sys.exit(1)

    card = build_feishu_card(data)
    send_to_feishu(webhook_url, card)


if __name__ == "__main__":
    main()
