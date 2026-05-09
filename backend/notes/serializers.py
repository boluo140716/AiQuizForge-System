from rest_framework import serializers
from .models import Note,Notebook,Quiz,Question,WrongQuestion,QuizAttempt
from .utils import md_to_plain_text

class NotebookSerializer(serializers.ModelSerializer):
    """笔记本序列化器"""
    note_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Notebook
        fields = ['id', 'name', 'note_count', 'created_at']
        read_only_fields = ['id', 'created_at', 'user']

    def get_note_count(self, obj):
        return obj.notes.count()

    def validate_name(self, value):
        user = self.context['request'].user
        instance = getattr(self, 'instance', None)
        qs = Notebook.objects.filter(name=value, user=user)
        if instance:  # 更新时排除自身
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError("你已经有同名笔记本了，请换一个名字。")
        return value
    
class NoteListSerializer(serializers.ModelSerializer):
    notebook_name=serializers.CharField(source='notebook.name',read_only=True)

    class Meta:
        model=Note
        fields=['id','title','notebook','notebook_name','tags','created_at','updated_at']

class NoteDetailSerializer(serializers.ModelSerializer):
    notebook_name=serializers.CharField(source='notebook.name',read_only=True)

    class Meta:
        model=Note
        fields=['id','title','notebook','notebook_name','tags','content_md','content_plain','created_at','updated_at']
        read_only_fields=['user','created_at','updated_at','content_plain']

class NoteCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model=Note
        fields=['title','notebook','tags','content_md']
    
    def create(self, validated_data):
        user=self.context['request'].user  # 从请求中获取当前用户
        validated_data['content_plain']=md_to_plain_text(validated_data.get('content_md',''))
        validated_data['user']=user    # 自动绑定用户
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        if 'content_md' in validated_data:
            validated_data['content_plain']=md_to_plain_text(validated_data['content_md'])
        return super().update(instance, validated_data)
    
class GenerateQuizSerializer(serializers.Serializer):
    question_count = serializers.IntegerField(default=5, min_value=1, max_value=10)
    
class QuizStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model=Quiz
        fields=['id','status','error_message','created_at','question_count']

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model=Question
        fields=['id','stem','options']

class QuestionWithAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id', 'stem', 'options', 'answer', 'explanation']

class AnswerItemSerializer(serializers.Serializer):
    question_id = serializers.IntegerField(required=True)
    selected = serializers.CharField(required=True,max_length=10)

class SubmitAnswerSerializer(serializers.Serializer):
    answers=serializers.ListField(child=AnswerItemSerializer(),min_length=1)

class QuizAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model=QuizAttempt
        fields=['id','quiz','score','total','correct_rate','answers_detail','completed_at']

class WrongQuestionSerializer(serializers.ModelSerializer):
    question_stem = serializers.CharField(source='question.stem', read_only=True)
    question_options = serializers.JSONField(source='question.options', read_only=True)
    question_answer = serializers.CharField(source='question.answer', read_only=True)
    question_explanation = serializers.CharField(source='question.explanation', read_only=True)
    quiz_id = serializers.IntegerField(source='quiz.id', read_only=True)
    note_title = serializers.CharField(source='quiz.note.title', read_only=True)

    class Meta:
        model = WrongQuestion
        fields = [
            'id', 'question', 'question_stem', 'question_options',
            'question_answer', 'question_explanation',
            'quiz_id', 'note_title', 'user_answer',
            'wrong_count', 'last_wrong_at'
        ]




