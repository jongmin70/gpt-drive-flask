from flask import Flask, request, redirect
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from werkzeug.middleware.proxy_fix import ProxyFix
import fitz  # PyMuPDF
import os

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# ✅ 본인의 Google OAuth 정보로 설정하세요
CLIENT_ID = "1057067732894-t68kv8c6bdjal9a5rp0a6gdlo1h9coq8.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REDIRECT_URI = "https://gpt-drive-api.onrender.com/callback"
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

creds = None  # 인증된 사용자 정보를 저장 (간단 구현)

# 🔹 서버 작동 확인용
@app.route("/")
def index():
    return "✅ Flask 서버가 Render에서 정상 작동 중입니다!"

# 🔹 로그인 시작
@app.route("/login")
def login():
    flow = Flow.from_client_config({
        "web": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "redirect_uris": [REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }, scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI
    auth_url, _ = flow.authorization_url(prompt='consent')
    return redirect(auth_url)

# 🔹 구글 로그인 완료 후 돌아오는 콜백
@app.route("/callback")
def callback():
    try:
        flow = Flow.from_client_config({
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }, scopes=SCOPES)
        flow.redirect_uri = REDIRECT_URI
        flow.fetch_token(
            authorization_response=request.url,
            redirect_uri=REDIRECT_URI
        )
        global creds
        creds = flow.credentials
        return "✅ 인증 완료! 이제 GPT에서 사용할 수 있습니다."
    except Exception as e:
        return f"❌ 인증 중 오류 발생: {str(e)}", 500

# 🔹 PDF 파일 검색 + 추출
@app.route("/search", methods=["POST"])
def search():
    global creds
    if not creds:
        return {"error": "❌ 인증이 필요합니다. 먼저 /login 을 완료해주세요."}

    query = request.json.get("query", "")
    drive_service = build('drive', 'v3', credentials=creds)
    results = drive_service.files().list(
        q=f"name contains '{query}' and mimeType='application/pdf'",
        fields="files(id, name)"
    ).execute()

    files = results.get("files", [])
    if not files:
        return {"result": "❌ 관련 PDF 파일을 찾을 수 없습니다."}

    file_id = files[0]['id']
    file_data = drive_service.files().get_media(fileId=file_id).execute()

    with open("/tmp/temp.pdf", "wb") as f:
        f.write(file_data)

    doc = fitz.open("/tmp/temp.pdf")
    text = "".join([page.get_text() for page in doc])
    doc.close()

    return {
        "filename": files[0]['name'],
        "content": text[:3000]  # GPT에 넘기기 좋은 길이로 제한
    }

# 🔹 Render용 포트 바인딩
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
