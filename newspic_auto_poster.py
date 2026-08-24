import os
import requests
import re
import json
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
    
    # 1. First Pass: Generate Initial Draft
    prompt = """당신은 대형 커뮤니티(디시인사이드, 에펨코리아 등)의 가십/속보 전문 마케터이자, 동시에 구글 SEO 전문가입니다.
한국의 현재 가장 핫한 트렌드(연예, 사회, 경제 등)에 대한 글을 작성해주세요.

다음의 정확한 포맷을 준수하여 작성해야 합니다:

[TITLE]
(클릭을 유도하는 자극적인 제목)
[HOOK]
(스레드 및 블로그 상단에 노출될 3줄짜리 도파민 유발 후킹 멘트. 독자가 뒷내용을 미치도록 궁금하게 만들고 끝내세요.)
[SEO_BODY]
(구글 검색 로봇이 좋아할 1000자 분량의 객관적이고 전문적인 뉴스/정보 텍스트. H2, H3 태그를 적절히 사용하세요.)
"""
    
    models_to_try = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite']
    response = None
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            print(f'Successfully generated content using model: {model_name}')
            break
        except Exception as e:
            continue
                
    if not response:
        raise Exception('All models failed.')
        
    text = response.text
    
    # 2. Second Pass: SEO/GEO/AEO Revision (Only for the SEO_BODY part)
    print("Evaluating draft...")
    eval_prompt = f"""You are a master Editor and SEO/AEO/GEO Specialist.
Review the following draft:

{text}

Evaluate the [SEO_BODY] section on three criteria (0-100 score each):
1. SEO (Search Engine Optimization): Keyword usage, headers, readability.
2. GEO (Generative Engine Optimization): Clear structured data, concise facts for AI to parse.
3. AEO (Answer Engine Optimization): Direct answers to the user's implicit question.

If the total score is below 285/300, logically MODIFY and REFINE the [SEO_BODY] section to improve the score. Do NOT rewrite from scratch. Enhance the vocabulary, headings, and keyword density while strictly preserving the structure.
Ensure the [TITLE] and [HOOK] remain incredibly sensational and click-inducing.
CRITICAL: You must return the response in the exact same format: [TITLE]... [HOOK]... [SEO_BODY]..."""

    revised_response = None
    for model_name in models_to_try:
        try:
            revised_response = client.models.generate_content(model=model_name, contents=eval_prompt)
            print(f'Successfully revised content using model: {model_name}')
            break
        except Exception as e:
            continue
            
    if revised_response and revised_response.text.strip():
        text = revised_response.text.strip()
        
    # Parsing the output
    try:
        title = text.split('[TITLE]')[1].split('[HOOK]')[0].strip()
        hook = text.split('[HOOK]')[1].split('[SEO_BODY]')[0].strip()
        body = text.split('[SEO_BODY]')[1].strip()
    except Exception as e:
        print("Parsing failed, returning raw text as body")
        title = "긴급 속보"
        hook = "지금 막 들어온 엄청난 소식입니다."
        body = text
    
    hook_html = "".join([f"<p class='mb-3'>{line}</p>" for line in hook.split('\n') if line.strip()])
    body_html = "".join([f"<p>{line}</p>" for line in body.split('\n') if line.strip()])
    
    return title, hook, hook_html, body_html

def create_html(nid, title, hook_raw, hook_html, body_html):
    target_link = f"https://www.newspic.kr/view.html?nid={nid}&pn={PARTNER_ID}"
    thumbnail_url = "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=600&auto=format&fit=crop&q=60"
    
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <script async src='https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-2228289204702106' crossorigin='anonymous'></script>
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
            <p class="text-[10px] text-gray-400 mt-3 text-center">
                이 포스팅은 뉴스픽 파트너스 활동의 일환으로, 클릭 시 일정액의 수수료를 제공받을 수 있습니다.
            </p>
        </div>
    </div>
</body>
</html>"""

    with open(f"article_{nid}.html", 'w', encoding='utf-8') as f:
        f.write(html)
        
    threads_data = {
        "title": title,
        "thread_post": f"{hook_raw}\n\n👉 내용 보기: https://somsoo.github.io/newspic-blog/article_{nid}.html",
        "nid": nid
    }
    with open("latest_thread.json", "w", encoding="utf-8") as f:
        json.dump(threads_data, f, ensure_ascii=False, indent=2)
        
    print(f"Created article_{nid}.html and latest_thread.json")

if __name__ == "__main__":
    nid = get_latest_newspic()
    title, hook_raw, hook_html, body = generate_content()
    create_html(nid, title, hook_raw, hook_html, body)
