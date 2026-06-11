# 二八分化配置

## 1. 推送代码到 GitHub

```bash
cd /Users/sunyi/work/code/github/A28
git add .
git commit -m "add erba stats + feishu notification"
git push
```

## 2. 配置飞书 Webhook

在 GitHub 仓库设置中添加一个 **Secret**（Settings → Secrets and variables → Actions）：

| 名称 | 值 |
|------|-----|
| `FEISHU_WEBHOOK` | 你的飞书机器人 Webhook URL |

### 获取飞书 Webhook：

1. 在飞书创建一个群聊
2. 群设置 → 群机器人 → 添加机器人 → **自定义机器人**
3. 复制 Webhook URL（形如 `https://open.feishu.cn/open-apis/bot/v2/hook/xxx`）
4. 粘贴到 GitHub Secrets 中

## 3. 验证运行

配置好之后，可以在 GitHub 仓库的 Actions 页面手动触发一次：

> Actions → 每日二八分化数据 → Run workflow

以后每个交易日 **16:30（北京时间）** 会自动跑一次，并把结果推送到飞书群。

## 本地测试飞书推送

```bash
python3 erba_stats.py --format json | python3 send_feishu.py /dev/stdin
# 或用文件：
python3 erba_stats.py --format json > /tmp/test.json
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx python3 send_feishu.py /tmp/test.json
```
