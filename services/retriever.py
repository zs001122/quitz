import jieba
import jieba.analyse

STOP_WORDS = {'的','了','在','是','我','有','和','就','不','人','都','一','一个','上','也','很','到','说','要','去','你','会','着','没有','看','好','自己','这','吗','呢','啊','呀'}

def retrieve_relevant_context(question: str, file_paragraphs, top_k=5):
    question_words = jieba.lcut(question)
    keywords = jieba.analyse.extract_tags(question, topK=10) or question_words
    filtered = [w for w in keywords if w not in STOP_WORDS and len(w) > 1]

    results = []
    for fname, paragraphs in file_paragraphs.items():
        for idx, para in enumerate(paragraphs):
            para_words = jieba.lcut(para)
            match_count = sum(1 for w in filtered if w in para_words)
            if match_count:
                results.append({
                    "filename": fname,
                    "paragraph_idx": idx + 1,
                    "content": para,
                    "score": match_count,
                    "matched_words": [w for w in filtered if w in para_words]
                })

    results.sort(key=lambda x: x['score'], reverse=True)
    top_results = results[:top_k]
    if top_results:
        return "\n\n".join(
            f"[{r['filename']} - 段落 {r['paragraph_idx']}] "
            f"(匹配到{r['score']}个关键词: {', '.join(r['matched_words'])}):\n{r['content']}"
            for r in top_results
        )
    return "未找到相关内容。"
