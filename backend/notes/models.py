from django.db import models
from django.conf import settings

class Notebook(models.Model):
    name = models.CharField(max_length=255, verbose_name="笔记本名称")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notebooks", verbose_name="用户")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "notebooks"
        verbose_name = "笔记本"
        verbose_name_plural = "笔记本"
        ordering = ["-created_at"]
        unique_together = ["name", "user"]

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class Note(models.Model):
    title = models.CharField(max_length=255, verbose_name="笔记标题")
    content_md = models.TextField(verbose_name="笔记内容(Markdown格式)")
    content_plain = models.TextField(verbose_name="笔记内容(纯文本格式)")
    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE, related_name="notes", verbose_name="所属笔记本")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notes", verbose_name="用户")
    tags = models.JSONField(default=list, blank=True, verbose_name="标签")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "notes"
        verbose_name = "笔记"
        verbose_name_plural = "笔记"
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class Quiz(models.Model):
    STATUS_CHOICES = (
        ("processing", "生成中"),
        ("completed", "已完成"),
        ("failed", "生成失败"),
    )

    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="quizzes", verbose_name="所属笔记", null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quizzes", verbose_name="发起用户")
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default="processing", verbose_name="状态")
    question_count = models.IntegerField(default=5, verbose_name="问题数量")
    error_message = models.TextField(blank=True, null=True, verbose_name="错误信息")
    celery_task_id = models.CharField(max_length=255, null=True, blank=True, verbose_name="Celery任务ID")
    idempotency_key = models.CharField(max_length=160, null=True, blank=True, verbose_name="幂等键")
    heartbeat_at = models.DateTimeField(null=True, blank=True, verbose_name="任务心跳时间")
    progress = models.JSONField(default=dict, blank=True, verbose_name="生成进度")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "quizzes"
        verbose_name = "测验记录"
        verbose_name_plural = "测验记录"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "heartbeat_at"], name="idx_quiz_status_hb"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "idempotency_key"], name="uq_quiz_user_idem"),
        ]

    def __str__(self):
        return f"{self.note.title if self.note else '错题重练'} 的测验 ({self.get_status_display()})"


class Question(models.Model):
    stem = models.TextField(verbose_name="问题干")
    options = models.JSONField(verbose_name="选项")
    answer = models.CharField(max_length=10, verbose_name="答案")
    explanation = models.TextField(blank=True, null=True, verbose_name="解析")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions", verbose_name="所属测验")
    origin = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='copies', verbose_name="原始题目")

    class Meta:
        db_table = "questions"
        verbose_name = "测验问题"
        verbose_name_plural = "测验问题"

    def __str__(self):
        return self.stem[:50]


class QuizAttempt(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts", verbose_name="所属测验")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts", verbose_name="用户")
    score = models.IntegerField(default=0, verbose_name="得分")
    total = models.IntegerField(default=5, verbose_name="总题数")
    correct_rate = models.FloatField(default=0.0, verbose_name="正确率")
    answers_detail = models.JSONField(default=list, verbose_name="答题详情")
    completed_at = models.DateTimeField(auto_now_add=True, verbose_name="完成时间")

    class Meta:
        db_table = "quiz_attempts"
        verbose_name = "答题记录"
        verbose_name_plural = "答题记录"
        ordering = ["-completed_at"]

    def __str__(self):
        return f"{self.user.username} 的测验,得分:{self.score}/{self.total}"


class WrongQuestion(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wrong_questions", verbose_name="用户")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="wrong_questions", verbose_name="错题")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="wrong_questions", verbose_name="所属测验")
    user_answer = models.CharField(max_length=255, verbose_name="用户答案")
    wrong_count = models.IntegerField(default=1, verbose_name="错题次数")
    last_wrong_at = models.DateTimeField(auto_now=True, verbose_name="上次错题时间")

    class Meta:
        db_table = "wrong_questions"
        verbose_name = "错题记录"
        verbose_name_plural = "错题记录"
        ordering = ["-last_wrong_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "question"],
                name="uq_wrong_user_question",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} 的错题记录 ({self.question.stem[:30]})"


class FailedTask(models.Model):
    """失败任务留档（DLQ）：最终失败、无法再重试的任务写在这里，供排查与重放。"""

    STATUS_CHOICES = (
        ("pending", "待处理"),
        ("replayed", "已重放"),
        ("ignored", "已忽略"),
    )

    task_name = models.CharField(max_length=255, verbose_name="任务名")
    task_id = models.CharField(max_length=64, null=True, blank=True, verbose_name="任务ID")
    args = models.JSONField(default=list, blank=True, verbose_name="位置参数")
    kwargs = models.JSONField(default=dict, blank=True, verbose_name="关键字参数")
    error = models.TextField(null=True, blank=True, verbose_name="错误信息")
    traceback = models.TextField(null=True, blank=True, verbose_name="堆栈")
    retries = models.IntegerField(default=0, verbose_name="已重试次数")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending", verbose_name="状态")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "failed_task"
        verbose_name = "失败任务"
        verbose_name_plural = "失败任务"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"], name="idx_ft_status_created"),
        ]

    def __str__(self):
        return f"{self.task_name} ({self.status})"


class KnowledgePoint(models.Model):
    """知识点：从笔记中抽取出来的可独立考察的概念。"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="knowledge_points", verbose_name="用户")
    notebook = models.ForeignKey(Notebook, on_delete=models.CASCADE, null=True, blank=True,
                                 related_name="knowledge_points", verbose_name="所属笔记本")
    name = models.CharField(max_length=255, verbose_name="知识点名称")
    description = models.TextField(blank=True, default="", verbose_name="知识点说明")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "knowledge_points"
        verbose_name = "知识点"
        verbose_name_plural = "知识点"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "notebook", "name"], name="uq_kp_user_nb_name"),
        ]

    def __str__(self):
        return self.name


class NoteKnowledgePoint(models.Model):
    """笔记与知识点的关联。"""

    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="kp_links", verbose_name="笔记")
    kp = models.ForeignKey(KnowledgePoint, on_delete=models.CASCADE, related_name="note_links", verbose_name="知识点")

    class Meta:
        db_table = "note_knowledge_point"
        verbose_name = "笔记-知识点"
        verbose_name_plural = "笔记-知识点"
        constraints = [
            models.UniqueConstraint(fields=["note", "kp"], name="uq_note_kp"),
        ]


class QuestionKnowledgePoint(models.Model):
    """题目与知识点的关联（供自适应组卷使用）。"""

    question = models.ForeignKey(Question, on_delete=models.CASCADE,
                                 related_name="kp_links", verbose_name="题目")
    kp = models.ForeignKey(KnowledgePoint, on_delete=models.CASCADE,
                           related_name="question_links", verbose_name="知识点")
    weight = models.FloatField(default=1.0, verbose_name="权重")

    class Meta:
        db_table = "question_knowledge_point"
        verbose_name = "题目-知识点"
        verbose_name_plural = "题目-知识点"
        constraints = [
            models.UniqueConstraint(fields=["question", "kp"], name="uq_q_kp"),
        ]


class UserKPMastery(models.Model):
    """用户对某个知识点的掌握度（BKT 模型）。"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="kp_masteries", verbose_name="用户")
    kp = models.ForeignKey(KnowledgePoint, on_delete=models.CASCADE,
                           related_name="masteries", verbose_name="知识点")
    p_mastery = models.FloatField(default=0.30, verbose_name="当前掌握概率")
    p_init = models.FloatField(default=0.30, verbose_name="初始掌握概率")
    p_transit = models.FloatField(default=0.15, verbose_name="学习转移概率")
    p_slip = models.FloatField(default=0.10, verbose_name="失误概率")
    p_guess = models.FloatField(default=0.25, verbose_name="猜测概率")
    attempts = models.IntegerField(default=0, verbose_name="作答次数")
    correct = models.IntegerField(default=0, verbose_name="答对次数")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "user_kp_mastery"
        verbose_name = "知识点掌握度"
        verbose_name_plural = "知识点掌握度"
        constraints = [
            models.UniqueConstraint(fields=["user", "kp"], name="uq_ukm_user_kp"),
        ]
        indexes = [
            models.Index(fields=["user"], name="idx_ukm_user"),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.kp.name}: {self.p_mastery:.2f}"


class ReviewSchedule(models.Model):
    """SM-2 复习排程：每个用户对每道题的下次复习时间。"""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="review_schedules", verbose_name="用户")
    question = models.ForeignKey(Question, on_delete=models.CASCADE,
                                 related_name="review_schedules", verbose_name="题目")
    kp = models.ForeignKey(KnowledgePoint, on_delete=models.SET_NULL, null=True, blank=True,
                           related_name="review_schedules", verbose_name="知识点")
    ease_factor = models.FloatField(default=2.5, verbose_name="难度因子")
    interval_days = models.IntegerField(default=0, verbose_name="间隔天数")
    repetitions = models.IntegerField(default=0, verbose_name="连续答对次数")
    lapses = models.IntegerField(default=0, verbose_name="遗忘次数")
    due_at = models.DateTimeField(verbose_name="下次复习时间")
    last_reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="上次复习时间")

    class Meta:
        db_table = "review_schedule"
        verbose_name = "复习排程"
        verbose_name_plural = "复习排程"
        ordering = ["due_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "question"], name="uq_review_user_question"),
        ]
        indexes = [
            models.Index(fields=["user", "due_at"], name="idx_review_user_due"),
        ]

    def __str__(self):
        return f"{self.user.username} - Q{self.question_id} due {self.due_at:%Y-%m-%d}"
