from flask import Flask, request, redirect
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import fitz  # PDF 텍스트 추출

app = Flask(__name__)

CLIENT_ID = "1057067732894-t68kv8c6bdjal9a5rp0a6gdlo1h9coq8.apps.googleusercontent.com"
CLIENT_SECRET = "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"
REDIRECT_URI = "https://gpt-drive-api.onrender.com/callback"
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

creds = None

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
    return "✅ 인증 완료! 이제 GPT에서 사용 가능합니다."

@app.route("/search", methods=["POST"])
def search():
    global creds
    if not creds:
        return {"error": "인증이 필요합니다. 먼저 /login 접속하세요."}

    query = request.json.get("query", "")
    drive_service = build('drive', 'v3', credentials=creds)
    results = drive_service.files().list(
        q=f"name contains '{query}' and mimeType='application/pdf'",
        fields="files(id, name)"
    ).execute()

    files = results.get("files", [])
    if not files:
        return {"result": "❌ PDF 파일을 찾을 수 없습니다."}

    file_id = files[0]['id']
    file_data = drive_service.files().get_media(fileId=file_id).execute()

    with open("temp.pdf", "wb") as f:
        f.write(file_data)

    doc = fitz.open("temp.pdf")
    text = "".join([page.get_text() for page in doc])
    doc.close()

    return {
        "filename": files[0]['name'],
        "content": text[:3000]
    }

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
