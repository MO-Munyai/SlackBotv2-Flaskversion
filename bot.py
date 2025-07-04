import os
import re
from flask import Flask, request, jsonify
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Load env vars
load_dotenv()
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
client = WebClient(token=SLACK_BOT_TOKEN)

# Get bot ID once
BOT_USER_ID = client.auth_test()["user_id"]
BOT_MENTION = f"<@{BOT_USER_ID}>"

app = Flask(__name__)

@app.route("/slack/events", methods=["POST"])
def slack_events():
    data = request.json

    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})

    event = data.get("event", {})
    event_type = event.get("type")

    if event_type == "app_mention":
        channel = event.get("channel")
        user = event.get("user")
        raw_text = event.get("text", "")
        text = re.sub(r'\s+', ' ', raw_text.replace(BOT_MENTION, "")).strip().lower()


        print(f"[MENTION] <@{user}> said: {text}")

        # /create_channel
        if text.startswith("/create_channel"):
            channel_name = text.split("/create_channel")[-1].strip().replace(" ", "-")
            try:
                new_channel = client.conversations_create(name=channel_name)
                new_channel_id = new_channel["channel"]["id"]
                client.conversations_invite(channel=new_channel_id, users=user)
                client.chat_postMessage(
                    channel=channel,
                    text=f"✅ Channel *#{channel_name}* created and <@{user}> invited!"
                )
            except SlackApiError as e:
                client.chat_postMessage(
                    channel=channel,
                    text=f"❌ Could not create channel: `{e.response['error']}`"
                )
            return jsonify({"ok": True})

        # /list_channels
        elif text == "/list_channels":
            try:
                response = client.conversations_list(exclude_archived=True)
                channels = response["channels"]
                if not channels:
                    msg = "📭 No channels found."
                else:
                    msg = "📋 Channels:\n" + "\n".join([f"• #{ch['name']}" for ch in channels])
                client.chat_postMessage(channel=channel, text=msg)
            except SlackApiError as e:
                client.chat_postMessage(
                    channel=channel,
                    text=f"❌ Could not fetch channels: `{e.response['error']}`"
                )
            return jsonify({"ok": True})

        # /get_messages
        elif text.startswith("/get_messages"):
            try:
                target_name = text.split("/get_messages")[-1].strip().replace("#", "")
                all_channels = client.conversations_list(exclude_archived=True)["channels"]
                target = next((c for c in all_channels if c["name"] == target_name), None)

                if not target:
                    client.chat_postMessage(channel=channel, text=f"❌ Channel `#{target_name}` not found.")
                else:
                    try:
                        history = client.conversations_history(channel=target["id"], limit=10)
                        messages = history.get("messages", [])
                        if not messages:
                            msg = f"🕸 No messages in `#{target_name}` yet."
                        else:
                            msg = f"🗂 Last messages in `#{target_name}`:\n" + "\n".join([
                            f"• {m.get('user', 'bot')}: {m.get('text', '[no text]')}" for m in messages
                    ])
                        client.chat_postMessage(channel=channel, text=msg)
                    except SlackApiError as e:
                        print("Slack API Error (history):", e.response["error"])
                        client.chat_postMessage(channel=channel, text=f"❌ Could not fetch history: `{e.response['error']}`")
            except Exception as ex:
                print("🚨 Unhandled error in /get_messages:", str(ex))
                client.chat_postMessage(channel=channel, text="❌ Unexpected error while fetching messages.")
            return jsonify({"ok": True})


        # Friendly chat responses
        elif "hello bot" in text:
            client.chat_postMessage(channel=channel, text=f"👋 Hello <@{user}>! Need something?")
            return jsonify({"ok": True})

        elif "how are you" in text:
            client.chat_postMessage(channel=channel, text="🤖 I'm just a bunch of functions, but I'm feeling logical today!")
            return jsonify({"ok": True})

        # fallback
        client.chat_postMessage(
            channel=channel,
            text=f"🤖 Unknown command. Try: `/create_channel name`, `/list_channels`, `/get_messages name`"
        )
        return jsonify({"ok": True})

    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(port=3000)
