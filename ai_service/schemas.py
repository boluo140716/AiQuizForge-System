from pydantic import BaseModel, Field, field_validator
from typing import List

class QuizRequest(BaseModel):  # 生成题目请求模型
    content: str=Field(...,min_length=20,description="用户输入的笔记内容")
    count: int=Field(default=5,ge=1,le=10,description="生成的题目数量,1-10之间")

class QuestionItem(BaseModel):  # 选择题项模型
    stem: str=Field(...,min_length=5,description="题干")
    options: List[str]=Field(...,min_items=4,max_items=4,description="选项列表")
    answer: str=Field(...,pattern=r'^[A-D]$',description="正确答案，必须是 A/B/C/D 之一")
    explanation: str=Field(...,min_length=5,description="解析")

    @field_validator('options')
    @classmethod
    def validate_options(cls, v: List[str]) -> List[str]:
        for i, opt in enumerate(v):
            if not opt or not opt.strip():
                raise ValueError(f'第 {i+1} 个选项不能为空')
            if len(opt.strip()) < 2:
                raise ValueError(f'第 {i+1} 个选项内容过短（至少2个字符）')
        return v

    @field_validator('stem', 'explanation')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('字段不能为空或仅包含空白字符')
        return v.strip()

class QuizOutput(BaseModel):
    questions: List[QuestionItem] = Field(..., description="题目列表")

class QuizResponse(BaseModel):  # 生成题目响应模型
    questions: List[QuestionItem]