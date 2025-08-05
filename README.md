# Alert Forwarder

## What does this program do?
This program transfers Alertmanager messages to Lark, Telegram, and Slack.

## How to use it?
To use this program, configure a receiver in your Alertmanager configuration as follows:

```yaml
receivers:
  - name: "slack"
    webhook_configs:
      - url: "http://alert-forwarder/alert?platform=slack&url=https://hooks.slack.com/services/xxxxx"
        send_resolved: true
  - name: "feishu-watchdog"
    webhook_configs:
      - url: "http://alert-forwarder/alert?platform=feishu&url=https://open.larksuite.com/open-apis/bot/v2/hook/xxx"
        send_resolved: true
  - name: "telegram-alert"
    webhook_configs:
      - url: "http://alert-forwarder/alert?platform=telegram&telegram_token=xxxx:xxx&telegram_chat_id=xxxx"
        send_resolved: true
