from rest_framework import serializers
from .models import Note,Notebook
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
