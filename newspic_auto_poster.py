import os
import requests
import re
from datetime import datetime
from google import genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
PARTNER_ID = "7440c8"

def get_latest_newspic():
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get('https://www.newspic.kr/', headers=headers)
    nid_matches = re.findall(r'view\.html\?nid=([0-9a-zA-Z]+)', resp.text)
    if not nid_matches:
        raise Exception("Could not find NIDs")
    return nid_matches[0]

def generate_content():
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = """
    Write a highly engaging news article about a current trending topic in South Korea.
    Format exactly:
    [TITLE]
    (title)
    [HOOK]
    (3 lines hook)
    [SEO_BODY]
    (500 words SEO body)
    """
    models_to_try = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']
    response = None
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            print(f'Successfully generated content using model: {model_name}')
            break
        except Exception as e:
            if '429' in str(e) or 'quota' in str(e).lower():
                print(f'Quota exceeded for model {model_name}. Trying next model...')
                continue
            else:
                print(f'Error with {model_name}: {e}')
                continue
                
    if not response:
        raise Exception('All models failed.')
    text = response.text
    
    title = text.split('[TITLE]')[1].split('[HOOK]')[0].strip()
    hook = text.split('[HOOK]')[1].split('[SEO_BODY]')[0].strip()
    body = text.split('[SEO_BODY]')[1].strip()
    
    hook_html = "".join([f"<p class='mb-3'>{line}</p>" for line in hook.split('\n') if line.strip()])
    body_html = "".join([f"<p>{line}</p>" for line in body.split('\n') if line.strip()])
    
    return title, hook_html, body_html

def create_html(nid, title, hook_html, body_html):
    target_link = f"https://www.newspic.kr/view.html?nid={nid}&pn={PARTNER_ID}"
    thumbnail_url = "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=600&auto=format&fit=crop&q=60"
    
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;600;700&display=swap');
        body {{ font-family: 'Pretendard', sans-serif; background-color: #f8f9fa; }}
        .content-mask {{ position: relative; max-height: 250px; overflow: hidden; }}
        .content-mask::after {{ content: ""; position: absolute; bottom: 0; left: 0; width: 100%; height: 150px; background: linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,1) 90%); pointer-events: none; }}
    </style>
</head>
<body class="flex items-center justify-center min-h-screen">
    <div class="bg-white w-full max-w-md mx-auto shadow-lg sm:rounded-xl overflow-hidden relative pb-20">
        <img src="{thumbnail_url}" alt="News Thumbnail" class="w-full h-56 object-cover">
        <div class="p-5">
            <span class="text-xs font-bold text-red-500 bg-red-50 px-2 py-1 rounded">단독/속보</span>
            <h1 class="text-xl font-bold mt-3 mb-4 text-gray-900 leading-snug">{title}</h1>
            <div class="content-mask text-gray-600 leading-relaxed text-sm">
                {hook_html}
                <div class="text-transparent selection:bg-transparent text-[8px] leading-tight mt-10">
                    {body_html}
                </div>
            </div>
        </div>
        <div class="absolute bottom-6 left-0 w-full px-5 flex flex-col items-center z-10">
            <a href="{target_link}" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg text-center shadow-lg transform transition active:scale-95 flex items-center justify-center">
                👉 기사 원문 계속 읽기
            </a>
        </div>
    </div>
</body>
</html>"""

    # We will write to the current directory when executed inside the repo
    with open(f"article_{nid}.html", 'w', encoding='utf-8') as f:
        f.write(html)
        
    print(f"Created article_{nid}.html")

if __name__ == "__main__":
    nid = get_latest_newspic()
    title, hook, body = generate_content()
    create_html(nid, title, hook, body)
