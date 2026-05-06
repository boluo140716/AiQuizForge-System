import re
import markdown
from bs4 import BeautifulSoup


def md_to_plain_text(md_content: str) -> str:
    """将 Markdown 文本转为纯文本，去除所有标记"""
    html = markdown.markdown(md_content, extensions=['extra', 'codehilite'])
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text(separator=' ', strip=True)
    # 压缩多余空白
    text = re.sub(r'\s+', ' ', text)
    return text.strip()