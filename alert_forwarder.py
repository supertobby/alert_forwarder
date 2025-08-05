from flask import Flask, request, jsonify
import requests
import json
import logging
import asyncio
from telegram import Bot
from telegram.constants import ParseMode
from datetime import datetime

app = Flask(__name__)

# 配置日志记录
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def escape_markdown_v2(text):
    """
    转义 Telegram MarkdownV2 格式中需要特殊处理的字符
    """
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + char if char in escape_chars else char for char in text])

def format_time(time_str):
    """
    格式化时间字符串，使其更加易读
    """
    try:
        time_obj = datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%SZ')
        return time_obj.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logger.error(f"Failed to format time: {str(e)}")
        return time_str

@app.route('/alert', methods=['POST'])
def alertmanager_webhook():
    webhook_url = request.args.get('url')
    platform = request.args.get('platform')
    telegram_token = request.args.get('telegram_token')
    telegram_chat_id = request.args.get('telegram_chat_id')
    message_thread_id = request.args.get('message_thread_id')

    if platform == 'feishu' and not webhook_url:
        logger.error("Webhook URL parameter is missing for Feishu")
        return jsonify({'status': 'error', 'message': 'Webhook URL parameter is missing for Feishu'}), 400

    if platform == 'telegram' and (not telegram_token or not telegram_chat_id):
        logger.error("Telegram token or chat ID is missing")
        return jsonify({'status': 'error', 'message': 'Telegram token或chat ID is missing'}), 400

    if platform == 'slack' and not webhook_url:
        logger.error("Webhook URL parameter is missing for Slack")
        return jsonify({'status': 'error', 'message': 'Webhook URL parameter is missing for Slack'}), 400

    data = request.json

    if not data:
        logger.error("No JSON data received")
        return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400

    logger.info(f"Received alert data: {data}")

    # 提取必要的信息并转换为目标格式
    alerts = data.get('alerts', [])
    if not alerts:
        logger.error("No alerts found in the received data")
        return jsonify({'status': 'error', 'message': 'No alerts found in the received data'}), 400

    for alert in alerts:
        alert_name = alert['labels'].get('alertname', 'No alertname')
        severity = alert['labels'].get('severity', 'No severity')
        summary = alert['annotations'].get('summary', 'No summary')
        description = alert['annotations'].get('description', 'No description')
        starts_at = format_time(alert.get('startsAt', 'No start time'))
        ends_at = format_time(alert.get('endsAt', 'No end time'))
        status = alert['status']

        if platform == 'feishu':
            # 根据状态设置颜色
            status_color = "red" if status == "firing" else "green"
            status_text = "告警" if status == "firing" else "恢复"
            title_text = "告警通知" if status == "firing" else "恢复通知"

            message = {
                "msg_type": "interactive",
                "card": {
                    "config": {
                        "wide_screen_mode": True,
                        "enable_forward": True
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": f"**告警名称:** {alert_name}\n"
                                           f"**状态:** <font color=\"{status_color}\">{status_text}</font>\n"
                                           f"**严重性:** {severity}\n"
                                           f"**摘要:** {summary}\n"
                                           f"**详情:** {description}\n"
                                           f"**开始时间:** {starts_at}\n"
                                           f"**结束时间:** {ends_at}\n"
                            }
                        }
                    ],
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": f"{title_text}"
                        },
                    }
                }
            }

            logger.info(f"Sending message to Feishu webhook: {message}")

            # 发送请求到指定的Webhook
            response = requests.post(webhook_url, headers={'Content-Type': 'application/json'}, data=json.dumps(message))

            if response.status_code != 200:
                logger.error(f"Failed to send alert to Feishu webhook: {response.text}")
                return jsonify({'status': 'error', 'message': 'Failed to send alert to Feishu webhook'}), 500

        elif platform == 'telegram':
            status_text = "Firing" if status == "firing" else "Resolved"
            emoji = "🔥🔥🔥🔥" if status == "firing" else "✅✅✅✅"
            message = (
                f"*告警名称:* {escape_markdown_v2(alert_name)}\n"
                f"*状态:* {escape_markdown_v2(status_text)} {emoji}\n"
                f"*告警级别:* {escape_markdown_v2(severity)}\n"
                f"*摘要:* {escape_markdown_v2(summary)}\n"
                f"*详情:* {escape_markdown_v2(description)}\n"
                f"*开始时间:* {escape_markdown_v2(starts_at)}\n"
                f"*结束时间:* {escape_markdown_v2(ends_at)}"
            )
            logger.info(f"Sending message to Telegram: {message}")

            # 创建 Telegram Bot 实例
            telegram_bot = Bot(token=telegram_token)

            # 发送请求到Telegram
            try:
                if message_thread_id:
                    asyncio.run(telegram_bot.send_message(chat_id=telegram_chat_id, text=message, parse_mode=ParseMode.MARKDOWN_V2, message_thread_id=message_thread_id))
                else:
                    asyncio.run(telegram_bot.send_message(chat_id=telegram_chat_id, text=message, parse_mode=ParseMode.MARKDOWN_V2))
            except Exception as e:
                logger.error(f"Failed to send alert to Telegram: {str(e)}")
                return jsonify({'status': 'error', 'message': 'Failed to send alert to Telegram'}), 500

        elif platform == 'slack':
            status_text = "Firing" if status == "firing" else "Resolved"
            emoji = ":fire:" if status == "firing" else ":white_check_mark:"
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*告警名称:* {alert_name}\n*状态:* {status_text} {emoji}\n*严重性:* {severity}\n*摘要:* {summary}\n*详情:* {description}\n*开始时间:* {starts_at}\n*结束时间:* {ends_at}"
                    }
                }
            ]

            message = {
                "blocks": blocks
            }

            logger.info(f"Sending message to Slack webhook: {message}")

            # 发送请求到指定的Webhook
            response = requests.post(webhook_url, headers={'Content-Type': 'application/json'}, data=json.dumps(message))

            if response.status_code != 200:
                logger.error(f"Failed to send alert to Slack webhook: {response.text}")
                return jsonify({'status': 'error', 'message': 'Failed to send alert to Slack webhook'}), 500

        else:
            logger.error("Unsupported platform")
            return jsonify({'status': 'error', 'message': 'Unsupported platform'}), 400

    return jsonify({'status': 'success', 'message': 'Alerts forwarded successfully'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)