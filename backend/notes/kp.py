"""知识点抽取：调用 AI 服务，把结果写入知识库。"""
import logging

import httpx
from django.conf import settings

from notes.models import KnowledgePoint, NoteKnowledgePoint

logger = logging.getLogger(__name__)


def extract_and_store_kps(note, trace_id: str = "") -> int:
    """抽取笔记的知识点并入库；已有则跳过。返回新增的笔记-知识点关联数。

    注意：这是"非关键路径"——失败不能让出题失败，所以调用方要 try/except。
    """
    if NoteKnowledgePoint.objects.filter(note=note).exists():
        return 0

    url = settings.AI_SERVICE_URL + "/api/v1/ai/extract-kp"
    headers = {
        "Authorization": f"Bearer {settings.AI_SERVICE_TOKEN}",
        "Content-Type": "application/json",
        "X-Trace-Id": trace_id,
    }
    payload = {"content": note.content_plain, "max_points": 8}

    with httpx.Client(timeout=httpx.Timeout(10.0, read=120.0)) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    count = 0
    for item in data.get("knowledge_points", []):
        name = (item.get("name") or "").strip()
        if not name:
            continue
        kp, _ = KnowledgePoint.objects.get_or_create(
            user=note.user,
            notebook=note.notebook,
            name=name,
            defaults={"description": item.get("description", "")},
        )
        _, created = NoteKnowledgePoint.objects.get_or_create(note=note, kp=kp)
        if created:
            count += 1
    return count
