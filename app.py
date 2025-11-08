import os
import re
from flask import Flask, render_template, request, jsonify
from curl_cffi.requests import Session, errors

# --- 配置 ---
# 用于请求 Sora API 的 Token (必须)
SORA_AUTH_TOKEN = os.getenv('SORA_AUTH_TOKEN') 
# 用于保护本应用的访问令牌 (可选)
APP_ACCESS_TOKEN = os.getenv('APP_ACCESS_TOKEN', None)
# 代理配置 (可选)
HTTP_PROXY = os.getenv('HTTP_PROXY', None)

app = Flask(__name__)

# 创建一个 curl_cffi session
session = Session(impersonate="chrome110")

@app.route('/')
def index():
    """
    渲染主页。
    向前端传递一个标志，告知是否需要显示令牌输入框。
    """
    auth_required = APP_ACCESS_TOKEN is not None and APP_ACCESS_TOKEN != ""
    return render_template('index.html', auth_required=auth_required)

@app.route('/get-sora-link', methods=['POST'])
def get_sora_link():
    """接收Sora URL，返回下载链接"""
    # 检查 SORA_AUTH_TOKEN 是否配置
    if not SORA_AUTH_TOKEN:
        return jsonify({"error": "服务器配置错误：未设置 SORA_AUTH_TOKEN。"}), 500

    # --- 新增：应用访问权限验证 ---
    if APP_ACCESS_TOKEN:
        user_token = request.json.get('token')
        if not user_token or user_token != APP_ACCESS_TOKEN:
            return jsonify({"error": "无效或缺失的访问令牌。"}), 401 # 401 Unauthorized

    # --- 原有逻辑 ---
    sora_url = request.json.get('url')
    if not sora_url:
        return jsonify({"error": "未提供 URL"}), 400

    match = re.search(r'sora\.chatgpt\.com/p/([a-zA-Z0-9_]+)', sora_url)
    if not match:
        return jsonify({"error": "无效的 Sora 链接格式"}), 400
    
    video_id = match.group(1)
    api_url = f"https://sora.chatgpt.com/backend/project_y/post/{video_id}"
    
    headers = {
        'User-Agent': 'Sora/1.2025.308 (Android 13; M2012K11AC; build 2530800)',
        'Accept': 'application/json',
        'Accept-Encoding': 'gzip',
        'oai-package-name': 'com.openai.sora',
        'authorization': f'Bearer {SORA_AUTH_TOKEN}'
    }
    
    proxies = {"http": HTTP_PROXY, "https": HTTP_PROXY} if HTTP_PROXY else {}

    try:
        response = session.get(api_url, headers=headers, proxies=proxies, timeout=20)
        response.raise_for_status()
        response_data = response.json()
        download_link = response_data['post']['attachments'][0]['encodings']['source']['path']
        return jsonify({"download_link": download_link})

    except errors.RequestsError as e:
        app.logger.error(f"请求失败: {e}")
        error_message = f"请求 OpenAI API 失败。请检查网络、代理或 SORA_AUTH_TOKEN。错误: {e}"
        if hasattr(e, 'response') and e.response is not None:
             if e.response.status_code in [401, 403]:
                error_message = "请求被拒绝 (401/403): 请检查你的 SORA_AUTH_TOKEN 是否有效或已过期。"
        return jsonify({"error": error_message}), 500
    except (KeyError, IndexError) as e:
        app.logger.error(f"解析JSON响应失败: {e}")
        return jsonify({"error": "无法从API响应中找到下载链接，可能是API结构已更改。"}), 500
    except Exception as e:
        app.logger.error(f"未知错误: {e}")
        return jsonify({"error": f"发生未知错误: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)