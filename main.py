import feedparser
import requests
import json
import os

WEBHOOK_URL = os.getenv("WECHAT_WEBHOOK")

# ========== 多源 RSS 配置 ==========
# 格式：{"来源名称": "RSS地址"}，可随意增删
RSS_FEEDS = {
    "运维派": "https://www.yunweipai.com/feed",
    "InfoQ中文": "https://www.infoq.cn/feed",
    "开源中国": "https://www.oschina.net/news/rss",
    "DevOps.com": "https://devops.com/feed/",
    "阿里云公告": "https://www.aliyun.com/rss/notice/zh.xml",
    "Grafana官方": "https://grafana.com/blog/index.xml",
    "Prometheus官方": "https://prometheus.io/blog/feed.xml",
    "Kubernetes官方": "https://kubernetes.io/feed.xml",
    "OpenAI博客": "https://openai.com/blog/rss.xml"
}

HISTORY_FILE = "pushed_links.txt"  # 已推送链接记录，所有源共用


def load_history():
    """加载已推送的文章链接"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f)
    return set()


def save_history(links):
    """保存已推送的文章链接"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        for link in links:
            f.write(link + '\n')


def send_wechat_message(text):
    """推送 Markdown 消息到企业微信群"""
    data = {
        "msgtype": "markdown",
        "markdown": {"content": text}
    }
    headers = {"Content-Type": "application/json"}
    requests.post(WEBHOOK_URL, data=json.dumps(data), headers=headers)


def main():
    pushed_links = load_history()
    print(f"调试信息：历史记录数量 = {len(pushed_links)}")

    # 收集所有源的新文章
    all_new_entries = []  # 格式：(来源名称, entry对象)

    for feed_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            if not feed.entries:
                print(f"⚠️ {feed_name} 未获取到内容")
                continue

            # 每个源只取最新 5 篇检查
            for entry in feed.entries[:5]:
                if entry.link not in pushed_links:
                    all_new_entries.append((feed_name, entry))
        except Exception as e:
            print(f"❌ {feed_name} 抓取失败: {e}")

    # 首次运行：所有源的最新文章全部标记为已读，不推送
    if not pushed_links:
        print("首次运行，初始化所有源的历史记录")
        all_links = []
        for feed_name, feed_url in RSS_FEEDS.items():
            feed = feedparser.parse(feed_url)
            all_links.extend([entry.link for entry in feed.entries])
        save_history(all_links)
        print(f"已标记全部 {len(all_links)} 篇文章，下次只推送新增文章")
        return

    if not all_new_entries:
        print("没有新文章")
        return

    # 组装推送消息，按来源分组
    msg_lines = ["**📢 运维资讯更新：**\n"]
    current_source = None

    for feed_name, entry in all_new_entries:
        if feed_name != current_source:
            msg_lines.append(f"\n**🔹 {feed_name}**")
            current_source = feed_name
        msg_lines.append(f"> [{entry.title}]({entry.link})")

    msg = "\n".join(msg_lines)

    # 更新历史记录：新链接放前面
    new_links = [entry.link for _, entry in all_new_entries]
    all_links = new_links + [link for link in pushed_links if link not in new_links]

    send_wechat_message(msg)
    save_history(all_links)
    print(f"推送完成！共推送 {len(all_new_entries)} 篇新文章")


if __name__ == "__main__":
    main()
