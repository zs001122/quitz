from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import os
import re
import jieba
import jieba.analyse

app = Flask(__name__, template_folder="./templates")

# ===== 内存存储 =====
uploaded_files = []        # 文件名列表
file_paragraphs = {}       # {filename: [段落列表]}
file_data = {}             # 文件元数据 {filename: {chars, size, status}}
indexed_files = set()
file_contents = {}         # {filename: bytes} 直接存文件内容

# ===== OpenAI 客户端 =====
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "sk-fac374c7b5d74366a9765404d305b87c"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
)


# ===== 首页 =====
@app.route("/")
def index():
    return render_template("index.html")

# ===== 上传文件 =====
@app.route("/upload", methods=["POST"])
def upload_file():
    global uploaded_files, file_paragraphs, file_data, file_contents, indexed_files

    # 清空上一次的文件数据
    uploaded_files.clear()
    file_paragraphs.clear()
    file_data.clear()
    file_contents.clear()
    indexed_files.clear()

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    content = file.read()
    file_contents[file.filename] = content

    # 处理文本
    text = content.decode(errors="ignore")
    paragraphs = [p.strip() for p in re.split(r'\n+', text) if p.strip()]
    file_paragraphs[file.filename] = paragraphs

    # 文件元数据
    file_data[file.filename] = {
        "chars": len(text),
        "size": len(content),
        "status": "Pending"
    }

    uploaded_files.append(file.filename)

    total_chars = sum(fd["chars"] for fd in file_data.values())
    return jsonify({
        "files": uploaded_files,
        "total_files": len(uploaded_files),
        "total_chars": total_chars,
        "indexed_files": len(indexed_files)
    })

# ===== 索引文件 =====
@app.route("/index", methods=["POST"])
def index_files():
    global indexed_files, file_data
    if not uploaded_files:
        return jsonify({
            "status": "error",
            "message": "No files to index",
            "total_files": len(uploaded_files),
            "indexed_files": len(indexed_files)
        })

    try:
        for filename in uploaded_files:
            if filename not in indexed_files:
                indexed_files.add(filename)
                file_data[filename]["status"] = "Indexed"

        total_chars = sum(fd["chars"] for fd in file_data.values())
        return jsonify({
            "status": "success",
            "message": "Files indexed successfully",
            "files": uploaded_files,
            "total_files": len(uploaded_files),
            "total_chars": total_chars,
            "indexed_files": len(indexed_files)
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "total_files": len(uploaded_files),
            "indexed_files": len(indexed_files)
        })

# ===== 简单检索函数 =====
def retrieve_relevant_context(question: str, top_k=5):
    question_words = jieba.lcut(question)
    keywords = jieba.analyse.extract_tags(question, topK=10)
    if not keywords:
        keywords = question_words

    stop_words = {'的','了','在','是','我','有','和','就','不','人','都','一','一个','上','也','很','到','说','要','去','你','会','着','没有','看','好','自己','这','吗','呢','啊','呀'}
    filtered_keywords = [w for w in keywords if w not in stop_words and len(w)>1]
    if not filtered_keywords:
        filtered_keywords = keywords

    results = []
    for filename, paragraphs in file_paragraphs.items():
        for idx, para in enumerate(paragraphs):
            para_words = jieba.lcut(para)
            match_count = sum(1 for w in filtered_keywords if w in para_words)
            if match_count > 0:
                results.append({
                    'filename': filename,
                    'paragraph_idx': idx + 1,
                    'content': para,
                    'score': match_count,
                    'matched_words': [w for w in filtered_keywords if w in para_words]
                })
    results.sort(key=lambda x: x['score'], reverse=True)
    top_results = results[:top_k]

    if top_results:
        return "\n\n".join([
            f"[{item['filename']} - 段落 {item['paragraph_idx']}] (匹配{item['score']}个关键词: {', '.join(item['matched_words'])}):\n{item['content']}"
            for item in top_results
        ])
    return "未找到相关内容。"

# ===== 提问接口 =====
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    question = data.get("message", "")

    # 判断是否有上传文件
    if uploaded_files:
        # 使用文档内容回答
        context_prompt = retrieve_relevant_context(question)
        system_instruction = f"""
你是一个专业的文档问答助手，以下是用户的问题以及从文档中检索到的相关内容。  
请基于提供的内容尽量回答问题，如果信息不足，可以结合上下文合理推测，但不要凭空编造事实。

用户问题：
{question}

检索到的相关内容：
{context_prompt}

要求：
1. 回答使用简洁、清晰的中文，使用Markdown格式。
2. 尽量引用文档中的信息，不要随意生成无关内容。
3. 当信息不足时，可以根据上下文合理推测，但要明确说明这是推测。
4. 保持条理清晰，可使用列表或段落分隔。

请开始回答：
"""
    else:
        # 闲聊模式：直接回答
        system_instruction = f"""
你是一个友好的聊天助手，请回答用户提出的问题：

用户问题：
{question}

请使用简洁、清晰的中文回答，保持自然交流风格。
"""

    try:
        completion = client.chat.completions.create(
            model="deepseek-v3.1",
            messages=[{"role": "user", "content": system_instruction}]
        )
        answer = completion.choices[0].message.content
    except Exception as e:
        answer = f"Error: {str(e)}"

    return jsonify({"reply": answer})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
