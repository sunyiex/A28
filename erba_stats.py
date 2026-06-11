#!/usr/bin/env python3
"""
A 股 二八分化 数据统计脚本
通过 akshare 获取主要指数行情，按大盘（二）/小盘（八）分类展示近N日涨跌幅。

大盘 = 二：沪深300、上证50、中证100
小盘 = 八：创业板指、科创50、中证500、中证1000、国证2000、北证50、中证2000、微盘股

使用方式：
  python3 erba_stats.py                            # 终端展示
  python3 erba_stats.py --format json              # JSON 输出（供飞书调用）
  python3 erba_stats.py --format json -d 2026-06-01  # 指定日期
  python3 erba_stats.py -n 10                       # 自定义周期
"""

import akshare as ak
import pandas as pd
from datetime import datetime
import warnings
import json
import sys
import argparse
import os

warnings.filterwarnings("ignore")

# ─── 指数列表配置 ───
INDEX_LIST = [
    {"cat": "二 (大盘)", "name": "沪深300", "code": "sh000300", "em_code": "1.000300"},
    {"cat": "二 (大盘)", "name": "上证50",  "code": "sh000016", "em_code": "1.000016"},
    {"cat": "二 (大盘)", "name": "中证100", "code": "sh000903", "em_code": "1.000903"},
    {"cat": "八 (小盘)", "name": "创业板指",  "code": "sz399006", "em_code": "0.399006"},
    {"cat": "八 (小盘)", "name": "科创50",    "code": "sh000688", "em_code": "1.000688"},
    {"cat": "八 (小盘)", "name": "中证500",  "code": "sh000905", "em_code": "1.000905"},
    {"cat": "八 (小盘)", "name": "中证1000", "code": "sh000852", "em_code": "1.000852"},
    {"cat": "八 (小盘)", "name": "国证2000", "code": "sz399303", "em_code": "0.399303"},
    {"cat": "八 (小盘)", "name": "北证50",   "code": "sz899050", "em_code": "0.899050"},
    {"cat": "八 (小盘)", "name": "中证2000", "code": "sh932000", "em_code": "1.932000"},
    {"cat": "八 (小盘)", "name": "微盘股",   "code": "sh884173", "em_code": "1.884173"},
]

# 只在 GitHub Actions 上尝试 EM 接口
IS_GH_ACTION = os.environ.get("GITHUB_ACTIONS") == "true"


def fetch_sina(code, name):
    """新浪 sinajs 接口"""
    try:
        df = ak.stock_zh_index_daily(symbol=code)
        if df is None or df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)
        return df
    except Exception:
        return None


def fetch_em(em_code, name):
    """东方财富 EM 接口（GA 环境可用）"""
    if not IS_GH_ACTION:
        return None
    try:
        # 通过原始 HTTP 请求绕过 akshare 的代理设置
        import requests
        secid = em_code
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": secid,
            "fields1": "f1,f2,f3,f4,f5",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
            "klt": "101",
            "fqt": "1",
            "beg": "20200101",
            "end": "20261231",
        }
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()
        if not data.get("data") or not data["data"].get("klines"):
            return None
        lines = data["data"]["klines"]
        rows = []
        for line in lines:
            parts = line.split(",")
            rows.append({
                "date": pd.to_datetime(parts[0]),
                "open": float(parts[1]),
                "close": float(parts[2]),
                "high": float(parts[3]),
                "low": float(parts[4]),
                "volume": float(parts[5]),
            })
        df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        return df
    except Exception:
        return None


def fetch_index(code, em_code, name):
    """尝试所有接口获取指数数据"""
    # 本地优先用新浪
    df = fetch_sina(code, name)
    if df is not None and len(df) >= 21:
        return df

    # GA 环境尝试 EM 接口
    df = fetch_em(em_code, name)
    if df is not None and len(df) >= 21:
        return df

    return None


def calc_perf(df, target_date, days=20):
    """计算截止到 target_date 的前 days 个交易日的涨跌幅"""
    if df is None or len(df) < days + 1:
        return None, None, None

    mask = df["date"] <= pd.Timestamp(target_date)
    if not mask.any():
        return None, None, None

    valid = df[mask]
    end_row = valid.iloc[-1]
    end_date = end_row["date"]
    end_price = end_row["close"]
    end_pos = df[df["date"] == end_date].index[0]
    start_pos = max(0, end_pos - days)

    if end_pos - start_pos < days:
        return None, end_date, end_price

    start_price = df.iloc[start_pos]["close"]
    start_date = df.iloc[start_pos]["date"]
    pct = (end_price - start_price) / start_price * 100
    return round(pct, 2), end_date, round(end_price, 2)


def main():
    parser = argparse.ArgumentParser(description="A股二八分化数据统计")
    parser.add_argument("-d", "--date", default=None, help="查询日期 (YYYY-MM-DD)")
    parser.add_argument("-n", "--period", type=int, default=20, help="统计周期，默认20")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="输出格式: text(终端) / json(机器可读)")
    args = parser.parse_args()

    query_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else None
    period = args.period
    date_label = query_date.strftime("%Y-%m-%d") if query_date else "最新"
    out_format = args.format

    if out_format == "text":
        print("=" * 60)
        print(f"   A股 二八分化 数据统计")
        print(f"   查询日期: {date_label}  |  周期: {period}日")
        if IS_GH_ACTION:
            print(f"   数据源: 东方财富 (GitHub Actions)")
        else:
            print(f"   数据源: 新浪 (本地)")
        print("=" * 60)

    results = []
    for idx in INDEX_LIST:
        cat = idx["cat"]
        name = idx["name"]
        code = idx["code"]
        em_code = idx["em_code"]

        if out_format == "text":
            print(f"\n  📡 {cat:8s} | {name} ({code})...", end=" ")

        df = fetch_index(code, em_code, name)
        if df is None:
            if out_format == "text":
                print("❌")
            continue

        perf, actual_date, close_price = calc_perf(df, query_date or df["date"].max(), period)
        if perf is None:
            if out_format == "text":
                print("❌ 数据不足")
            continue

        perf_5d, _, _ = calc_perf(df, query_date or df["date"].max(), 5)
        perf_60d, _, _ = calc_perf(df, query_date or df["date"].max(), min(60, len(df)))

        if out_format == "text":
            sign = "🔴" if perf < 0 else "🟢"
            print(f"✅ {sign} {perf:+.2f}%")

        data_date_str = str(actual_date.date()) if actual_date else ""
        results.append({
            "分类": "二" if "二" in cat else "八",
            "指数名称": name,
            "代码": code,
            f"近{period}日涨跌幅(%)": perf,
            "涨跌幅(%)": perf,
            "近5日涨跌幅(%)": perf_5d,
            "近60日涨跌幅(%)": perf_60d,
            "收盘价": close_price,
            "数据日期": data_date_str,
        })

    if out_format == "json":
        er = [r for r in results if r["分类"] == "二"]
        ba = [r for r in results if r["分类"] == "八"]
        avg_er = sum(r["涨跌幅(%)"] for r in er) / len(er) if er else None
        avg_ba = sum(r["涨跌幅(%)"] for r in ba) / len(ba) if ba else None
        diff = round(avg_er - avg_ba, 2) if avg_er is not None and avg_ba is not None else None

        output = {
            "查询日期": date_label,
            "数据日期": results[0]["数据日期"] if results else "",
            "统计周期": period,
            "大盘平均": avg_er,
            "小盘平均": avg_ba,
            "二八差距": diff,
            "指数": results,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    # ===== 文本输出 =====
    er = [r for r in results if r["分类"] == "二"]
    ba = [r for r in results if r["分类"] == "八"]
    print("\n" + "=" * 60)
    print(f"   📊 近{period}日涨跌幅一览 ({date_label})")
    print("=" * 60)
    for r in results:
        sign = "🔴" if r["涨跌幅(%)"] < 0 else "🟢"
        icon = "🏛️" if r["分类"] == "二" else "📈"
        print(f"  {icon} {r['指数名称']:8s}  {sign} {r['涨跌幅(%)']:+.2f}%")

    if er and ba:
        avg_er = sum(r["涨跌幅(%)"] for r in er) / len(er)
        avg_ba = sum(r["涨跌幅(%)"] for r in ba) / len(ba)
        diff = avg_er - avg_ba
        print(f"\n   📋 二 vs 八")
        print(f"     大盘(二) 平均: {avg_er:+.2f}%")
        print(f"     小盘(八) 平均: {avg_ba:+.2f}%")
        print(f"     二八差距:     {diff:+.2f}%")
        if diff > 1:
            print(f"     分化程度: 明显分化（大盘抗跌）")
        elif diff > 0:
            print(f"     分化程度: 弱分化")
        else:
            print(f"     分化程度: 小盘占优")
        best = max(results, key=lambda r: r["涨跌幅(%)"])
        worst = min(results, key=lambda r: r["涨跌幅(%)"])
        print(f"     🏆 最强: {best['指数名称']} ({best['涨跌幅(%)']:+.2f}%)")
        print(f"     🪦 最弱: {worst['指数名称']} ({worst['涨跌幅(%)']:+.2f}%)")

    missing = [idx["name"] for idx in INDEX_LIST
               if idx["name"] not in [r["指数名称"] for r in results]]
    if missing and not IS_GH_ACTION:
        print(f"\n  ⚠️ 以下指数本地未获取: {', '.join(missing)}")
        print(f"    推送到 GitHub Actions 后会自动获取完整数据")

    print(f"\n✅ 统计完成")


if __name__ == "__main__":
    main()
