import re
import os

def count_words(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 统计总字符数（包含空格和换行）
    total_chars_with_spaces = len(content)
    
    # 统计总字符数（不含空格和换行）
    total_chars_no_spaces = len(content.replace(' ', '').replace('\n', '').replace('\t', ''))
    
    # 统计中文字符数
    chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', content))
    
    # 统计英文单词数
    english_words = len(re.findall(r'\b[a-zA-Z]+\b', content))
    
    # 统计数字串数
    numbers = len(re.findall(r'\b\d+\b', content))

    print(f"--- 【{os.path.basename(file_path)}】字数统计 ---")
    print(f"总字符数（含空格/换行）: {total_chars_with_spaces}")
    print(f"总字符数（不含空格/换行）: {total_chars_no_spaces}")
    print(f"中文字符数: {chinese_chars}")
    print(f"英文单词数: {english_words}")
    print(f"数字串数: {numbers}")
    
    # 毕设通常的字数统计口径：中文字符数 + 英文单词数
    approx_word_count = chinese_chars + english_words
    print(f"==> 预估毕设有效字数（中文字符 + 英文单词）: {approx_word_count}")

if __name__ == "__main__":
    import sys
    file_path = sys.argv[1] if len(sys.argv) > 1 else "/data/workspace/Interview-Agent/毕设论文正文_v3.md"
    count_words(file_path)
