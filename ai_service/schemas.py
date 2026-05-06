from pydantic import BaseModel, Field
from typing import List

class QuizRequest(BaseModel):  # 生成题目请求模型
    content: str=Field(...,min_length=20,description="用户输入的笔记内容")
    count: int=Field(default=5,ge=1,le=10,description="生成的题目数量,1-10之间")

class QuestionItem(BaseModel):  # 选择题项模型
    stem: str=Field(...,description="题干")
    options: List[str]=Field(...,min_items=4,max_items=4,description="选项列表")
    answer: str=Field(...,description="正确答案")
    explanation: str=Field(...,description="解析")

class QuizResponse(BaseModel):  # 生成题目响应模型
    questions: List[QuestionItem]
