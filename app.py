from flask import Flask, request, redirect
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import fitz  # PyMuPDF - PDF 텍스트 추출

app = Flask(__name__)

# ✅ 아래 CLIENT_ID / CLIENT_SECRET / REDIRECT_URI를 본인 정보로 교체
CLIENT_ID = "1057067732894-t68kv8c6bdjal9a5rp0a6gdlo1h9coq8.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REDIRECT_URI = "https://gpt-drive-api.onrender.com/callback"  # Render 도메인에 맞게 설정
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

creds = None  # 인증 정보를 전역에 저장 (테스트용, 실제 배포 시 DB 등으로 변경 필요)

@app.route("/")
def index():
    return "✅ Flask 서버가 Render에서 정상 작동 중입니다!"

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

@app.route("/callback")
def callback():
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
    flow.fetch_token(authorization_response=request.url)

    global creds
    creds = flow.credentials
    return "✅ 인증 완료! 이제 GPT에서 사용할 수 있습니다."

@app.route("/search", methods=["POST"])
def search():
    global creds
    if not creds:
        return {"error": "❌ 먼저 /login 에서 인증을 진행해주세요."}

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

    with open("temp.pdf", "wb") as f:
        f.write(file_data)

    doc = fitz.open("temp.pdf")
    text = "".join([page.get_text() for page in doc])
    doc.close()

    return {
        "filename": files[0]['name'],
        "content": text[:3000]  # 너무 길지 않게 제한
    }
