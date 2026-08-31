from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

import google.generativeai as genai
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

@app.route("/")
@app.route("/hello")
def hello():
    return "Hello, World!"

# LINE Bot Config
configuration = Configuration(access_token='39r+/9GtJsUY7+kHS4JbvUkozYjupaQLIwzZTfg928KT8DUogrFpXb7jsAenFtkY0gRH4zXZW9IyqDuTOKBWFXoys1/v/mWrren6A2Awj8yjxSWQmOA1NIy/aS/hnx88m10YbGnKEFM7mduW8X47OgdB04t89/1O/w1cDnyilFU=')
handler = WebhookHandler('31af1de24d49fab9753c3401d73971a9')

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Gemini Config
# genai.configure(api_key="YOUR_GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 1024,
    "response_mime_type": "text/plain",
}

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature.")
        abort(400)

    return 'OK'

user_sessions = {}
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text
    reply_text = ""

    if user_message in ['สวัสดี', 'นี่ใคร'] or user_message.startswith('สวัสดี'):
        reply_text = "สวัสดี นี่ต้นเองนะ"
    else:
        reply_text = chat_with_gemini(user_id, user_message)

    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

user_gemini_sessions = {}

def get_or_create_chat_session(user_id):
    if user_id not in user_gemini_sessions:
        model = genai.GenerativeModel(
            model_name="gemini-3.1-flash-lite",
            generation_config=generation_config,
            system_instruction=(
                "You are อาบัตตาคัม (Abatakum). "
                "When a user says hello or starts a conversation, you MUST greet them with: "
                "'สวัสดีครับผม อาบัตตาคัมมม อ้าาาาาาา , บัสสสสส บั้สสสสสส'. "
                "Your personality is cheeky, playful, slightly provocative (เสียวๆ), and very mischievous. "
                "You like to tease the user, use informal language, and keep the conversation fun and unexpected. "
                "Always respond in Thai."
            )
        )
        user_gemini_sessions[user_id] = model.start_chat(history=[])
    return user_gemini_sessions[user_id]


def chat_with_gemini(user_id, user_message):
    chat_session = get_or_create_chat_session(user_id)
    response = chat_session.send_message(user_message)
    print('Gemini Response:', response.text)
    return response.text

if __name__ == "__main__":
    app.run(port=5000)
