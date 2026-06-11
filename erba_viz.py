#!/usr/bin/env python3
"""
二八分化数据可视化 — 生成交互式 HTML 图表
支持指定日期查询。

使用方式：
  python3 erba_viz.py                          # 可视化最新数据
  python3 erba_viz.py -d 2026-06-01            # 可视化指定日期数据
  python3 erba_viz.py -d 2026-03-15 -n 30      # 指定日期 + 自定义周期
"""

import json
import sys
import os
import argparse
from datetime import datetime

# 先运行 erba_stats.py 获取数据
def fetch_data(date=None, period=20):
    """调用 erba_stats.py 获取数据，返回 JSON 数据"""
    cmd = f"python3 /Users/sunyi/work/code/github/A28/erba_stats.py --format json"
    if date:
        cmd += f" -d {date}"
    if period != 20:
        cmd += f" -n {period}"

    print(f"📡 正在获取数据: {'最新' if not date else date} (周期:{period}日)")
    result = os.popen(cmd).read()
    if not result.strip():
        print("❌ 数据获取失败（返回为空）")
        sys.exit(1)

    try:
        data = json.loads(result)
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败: {e}")
        print(result[:500])
        sys.exit(1)

    return data


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>A股二八分化 - <DATE_LABEL></title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
  body { font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
         max-width: 1000px; margin: 0 auto; padding: 24px; background: #f8fafc; }
  h1 { font-size: 24px; display: flex; align-items: center; gap: 8px; }
  .subtitle { color: #64748b; font-size: 14px; margin-top: -8px; margin-bottom: 24px; }
  .card { background: white; border-radius: 12px; padding: 24px; margin-bottom: 20px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }
  .stat-box { background: white; border-radius: 12px; padding: 16px; text-align: center;
              box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  .stat-box .value { font-size: 28px; font-weight: 700; margin: 4px 0; }
  .stat-box .label { font-size: 13px; color: #64748b; }
  .green { color: #22c55e; }
  .red { color: #ef4444; }
  .amber { color: #f59e0b; }
  .blue { color: #3b82f6; }
  .note { color: #94a3b8; font-size: 12px; text-align: center; margin-top: 16px; }
  .disclaimer { color: #94a3b8; font-size: 11px; text-align: center; margin-top: 32px;
                padding: 16px; border-top: 1px solid #e2e8f0; }
  .table-wrap { overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 14px; }
  th { background: #f1f5f9; color: #475569; padding: 10px 12px; text-align: center; font-weight: 600; }
  td { padding: 10px 12px; text-align: center; border-bottom: 1px solid #f1f5f9; }
  .cat-badge { display: inline-block; padding: 2px 10px; border-radius: 99px; font-size: 12px; font-weight: 600; }
  .cat-er { background: #dbeafe; color: #1d4ed8; }
  .cat-ba { background: #fce7f3; color: #db2777; }
  .miss { color: #94a3b8; font-style: italic; }
  .date-nav { text-align: center; margin-bottom: 16px; font-size: 14px; }
  .date-nav input { padding: 6px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
  .date-nav button { padding: 6px 16px; background: #3b82f6; color: white; border: none;
                     border-radius: 6px; cursor: pointer; font-size: 14px; }
  .date-nav button:hover { background: #2563eb; }
</style>
</head>
<body>

<h1>📊 A股 二八分化 统计</h1>
<div class="subtitle">
  查询日期: <strong><DATE_LABEL></strong> |
  统计周期: <strong><PERIOD>个交易日</strong> |
  数据日期: <strong><DATA_DATE></strong>
</div>

<div class="date-nav">
  <input type="date" id="datePicker" value="<DATE_VALUE>" />
  <button onclick="goDate()">查询</button>
  <span style="margin:0 8px">|</span>
  <button onclick="goLatest()" style="background:#64748b">最新</button>
  <span style="margin-left:12px;font-size:13px;color:#94a3b8">周期:
    <select id="periodSelect" onchange="goDate()">
      <option value="5" <PERIOD_5_SEL>>5日</option>
      <option value="10" <PERIOD_10_SEL>>10日</option>
      <option value="20" <PERIOD_20_SEL>>20日</option>
      <option value="30" <PERIOD_30_SEL>>30日</option>
      <option value="60" <PERIOD_60_SEL>>60日</option>
    </select>
  </span>
</div>

<div class="summary-grid" id="summaryGrid">
  <div class="stat-box"><div class="label">大盘(二) 均值</div><div class="value red" id="erAvg">--</div></div>
  <div class="stat-box"><div class="label">小盘(八) 均值</div><div class="value red" id="baAvg">--</div></div>
  <div class="stat-box"><div class="label">二八差距</div><div class="value green" id="diffVal">--</div></div>
  <div class="stat-box"><div class="label">分化程度</div><div class="value amber" id="diffLvl">--</div></div>
</div>

<div class="card">
  <h2>📈 近<PERIOD>日涨跌幅对比</h2>
  <canvas id="barChart" height="350"></canvas>
</div>

<div class="card">
  <h2>📊 近5 / 近<PERIOD> / 近60日涨跌幅</h2>
  <canvas id="groupChart" height="350"></canvas>
</div>

<div class="card">
  <h2>📋 详细数据表</h2>
  <div class="table-wrap">
    <table>
      <thead><tr>
        <th>分类</th><th>指数名称</th><th>代码</th>
        <th>收盘价</th><th>近5日</th><th>近<PERIOD>日</th><th>近60日</th><th>数据日期</th>
      </tr></thead>
      <tbody id="tableBody"></tbody>
    </table>
  </div>
  <div class="note"><MISS_NOTE></div>
</div>

<div class="disclaimer">
  ⚠️ 数据来源：akshare (新浪/东方财富) | 仅供学习参考，不构成投资建议<br>
  生成时间：<span id="footerTime"><GENERATED_AT></span>
</div>

<script>
const data = <JSON_DATA>;
const period = <PERIOD>;

document.getElementById('footerTime').textContent = data.数据日期 || data.查询日期;

const erAvg = data.大盘平均, baAvg = data.小盘平均, diff = data.二八差距;
document.getElementById('erAvg').textContent = (erAvg >= 0 ? '+' : '') + erAvg.toFixed(2) + '%';
document.getElementById('erAvg').className = 'value ' + (erAvg < 0 ? 'red' : 'green');
document.getElementById('baAvg').textContent = (baAvg >= 0 ? '+' : '') + baAvg.toFixed(2) + '%';
document.getElementById('baAvg').className = 'value ' + (baAvg < 0 ? 'red' : 'green');
document.getElementById('diffVal').textContent = (diff >= 0 ? '+' : '') + diff.toFixed(2) + '%';
document.getElementById('diffVal').className = 'value ' + (diff > 0 ? 'green' : 'red');

let lvl = '弱分化';
if (diff > 3) lvl = '强分化';
else if (diff > 1) lvl = '明显分化';
else if (diff < 0) lvl = '小盘占优';
document.getElementById('diffLvl').textContent = lvl;
document.getElementById('diffLvl').className = 'value amber';

const items = data.指数;
const pctCol = '近' + period + '日涨跌幅(%)';
const labels = items.map(i => i.指数名称);
const mainPct = items.map(i => i[pctCol]);
const pct5 = items.map(i => i['近5日涨跌幅(%)']);
const pct60 = items.map(i => i['近60日涨跌幅(%)']);

// 柱状图
new Chart(document.getElementById('barChart'), {
  type: 'bar',
  data: {
    labels: labels,
    datasets: [{
      label: '近' + period + '日涨跌幅 (%)',
      data: mainPct,
      backgroundColor: mainPct.map(v => v < 0 ? 'rgba(239,68,68,0.7)' : 'rgba(34,197,94,0.7)'),
      borderColor: mainPct.map(v => v < 0 ? '#ef4444' : '#22c55e'),
      borderWidth: 2,
      borderRadius: 4,
    }]
  },
  options: {
    responsive: true,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          afterLabel: function(ctx) {
            const item = items[ctx.dataIndex];
            return '分类: ' + item.分类 + ' | 收盘: ' + item.收盘价.toLocaleString();
          }
        }
      }
    },
    scales: {
      y: { grid: { color: '#f1f5f9' }, ticks: { callback: v => v + '%' } },
      x: { grid: { display: false } }
    }
  }
});

// 分组柱状图
new Chart(document.getElementById('groupChart'), {
  type: 'bar',
  data: {
    labels: labels,
    datasets: [
      { label: '近5日', data: pct5, backgroundColor: 'rgba(251,191,36,0.7)', borderRadius: 3 },
      { label: '近' + period + '日', data: mainPct, backgroundColor: 'rgba(239,68,68,0.7)', borderRadius: 3 },
      { label: '近60日', data: pct60, backgroundColor: 'rgba(99,102,241,0.7)', borderRadius: 3 },
    ]
  },
  options: {
    responsive: true,
    plugins: { legend: { position: 'top' } },
    scales: {
      y: { grid: { color: '#f1f5f9' }, ticks: { callback: v => v + '%' } },
      x: { grid: { display: false } }
    }
  }
});

// 表格
const tbody = document.getElementById('tableBody');
items.forEach(i => {
  const catClass = i.分类.includes('二') ? 'cat-er' : 'cat-ba';
  const pct = i[pctCol];
  const p5 = i['近5日涨跌幅(%)'];
  const p60 = i['近60日涨跌幅(%)'];
  const row = `<tr>
    <td><span class="cat-badge ${catClass}">${i.分类.replace('(','').replace(')','')}</span></td>
    <td><strong>${i.指数名称}</strong></td>
    <td style="color:#94a3b8;font-size:12px">${i.代码}</td>
    <td><strong>${i.收盘价.toLocaleString()}</strong></td>
    <td class="${p5 < 0 ? 'red' : 'green'}">${(p5 >= 0 ? '+' : '') + p5.toFixed(2)}%</td>
    <td class="${pct < 0 ? 'red' : 'green'}">${(pct >= 0 ? '+' : '') + pct.toFixed(2)}%</td>
    <td class="${p60 < 0 ? 'red' : 'green'}">${(p60 >= 0 ? '+' : '') + p60.toFixed(2)}%</td>
    <td style="color:#94a3b8">${i.数据日期}</td>
  </tr>`;
  tbody.innerHTML += row;
});

function goDate() {
  const d = document.getElementById('datePicker').value;
  const p = document.getElementById('periodSelect').value;
  const params = [];
  if (d) params.push('d=' + d);
  if (p != 20) params.push('n=' + p);
  const suffix = params.length > 0 ? '?' + params.join('&') : '';
  window.location.href = window.location.pathname + suffix;
}

function goLatest() {
  const p = document.getElementById('periodSelect').value;
  const params = p != 20 ? '?n=' + p : '';
  window.location.href = window.location.pathname + params;
}
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="二八分化数据可视化")
    parser.add_argument("-d", "--date", type=str, default=None,
                        help="查询日期 (YYYY-MM-DD)")
    parser.add_argument("-n", "--period", type=int, default=20,
                        help="统计周期（交易日数），默认 20")
    args = parser.parse_args()

    # 获取数据
    data = fetch_data(date=args.date, period=args.period)

    date_label = args.date if args.date else "最新"
    date_value = args.date if args.date else datetime.now().strftime("%Y-%m-%d")
    data_date = data.get("数据日期", data.get("指数", [{}])[0].get("数据日期", "--"))
    period = args.period
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    missing = data.get("缺失指数", [])
    miss_note = "注：" + "、".join(missing) + " 因接口限制未获取" if missing else ""

    # 周期选项选中状态
    sel = {5: "", 10: "", 20: "", 30: "", 60: ""}
    if period in sel:
        sel[period] = "selected"

    html = (HTML_TEMPLATE
            .replace("<DATE_LABEL>", date_label)
            .replace("<DATE_VALUE>", date_value)
            .replace("<DATA_DATE>", data_date)
            .replace("<PERIOD>", str(period))
            .replace("<GENERATED_AT>", generated_at)
            .replace("<MISS_NOTE>", miss_note)
            .replace("<JSON_DATA>", json.dumps(data, ensure_ascii=False))
            .replace("<PERIOD_5_SEL>", sel[5])
            .replace("<PERIOD_10_SEL>", sel[10])
            .replace("<PERIOD_20_SEL>", sel[20])
            .replace("<PERIOD_30_SEL>", sel[30])
            .replace("<PERIOD_60_SEL>", sel[60])
            )

    viz_path = "/Users/sunyi/work/code/github/A28/erba_viz.html"
    with open(viz_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n✅ 可视化已生成: {viz_path}")
    print(f"   查询: {date_label} | 周期: {period}日")
    print(f"   大盘均值: {data['大盘平均']:+.2f}% | 小盘均值: {data['小盘平均']:+.2f}% | 差距: {data['二八差距']:+.2f}%")
    print(f"\n💡 在浏览器中打开 erba_viz.html 即可查看交互图表")
    print(f"   页面内有日期选择器和周期选择器，可直接切换查询\n")


if __name__ == "__main__":
    main()
