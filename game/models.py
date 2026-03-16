from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from typing import TYPE_CHECKING


class PlayerProfile(models.Model):
    """Extended user profile for the player"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='player_profile')
    current_level = models.IntegerField(default=1)
    total_score = models.IntegerField(default=0)
    streak_days = models.IntegerField(default=0)
    last_login_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    can_retry_daily = models.BooleanField(default=False, help_text="Bifează pentru a permite încă un mesaj zilnic azi")
    can_retry_spin = models.BooleanField(default=False, help_text="Bifează pentru a permite încă o rotire la roată azi")
    can_retry_question = models.BooleanField(default=False, help_text="Bifează pentru a permite încă o întrebare azi")
    can_view_extra_memory = models.BooleanField(default=False, help_text="Bifează pentru a permite vizualizarea unei amintiri extra (sneak peek)")
    
    def __str__(self):
        return f"{self.user.username} - Level {self.current_level}"


class Level(models.Model):
    """Game levels with unlock conditions"""
    number = models.IntegerField(unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    required_score = models.IntegerField(default=0)
    requires_admin_approval = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=True)
    reward_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['number']
    
    def __str__(self):
        return f"Level {self.number}: {self.title}"


class MinigameType(models.Model):
    """Types of minigames available"""
    GAME_TYPES = [
        ('REAL_CHALLENGE', 'Real Life Challenge'),
        ('VERSE_COMPLETION', 'Verse/Quote Completion'),
        ('TIMELINE', 'Timeline Challenge'),
        ('GUESS_PLACE', 'Guess the Place'),
        ('MEMORY_MATCH', 'Memory Match'),
        ('BINGO', 'Romantic Bingo'),
        ('QUEST_PROOF', 'Quest with Proof'),
        ('WOULD_RATHER', 'Would You Rather'),
        ('QUIZ', 'Custom Quiz'),
        ('ESCAPE_ROOM', 'Escape Room Puzzle'),
        ('CIPHER', 'Cipher/Cryptogram'),
        ('ANAGRAM', 'Anagram'),
        ('JIGSAW', 'Jigsaw Puzzle'),
    ]
    
    name = models.CharField(max_length=50, choices=GAME_TYPES, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=50, blank=True)  # emoji or icon class
    
    def __str__(self):
        return self.display_name


class Minigame(models.Model):
    """Individual minigame instances"""
    title = models.CharField(max_length=200)
    game_type = models.ForeignKey(MinigameType, on_delete=models.CASCADE)
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name='minigames')
    description = models.TextField()
    is_locked = models.BooleanField(default=True)
    points_reward = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['level__number', 'order']
    
    def __str__(self):
        return f"{self.title} ({self.game_type.display_name})"
    
    if TYPE_CHECKING:
        questions: models.Manager["Question"]
        id: int


class Question(models.Model):
    """Questions for quizzes and challenges"""
    minigame = models.ForeignKey(Minigame, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_type = models.CharField(
        max_length=20,
        choices=[
            ('TEXT', 'Text Answer'),
            ('MULTIPLE', 'Multiple Choice'),
            ('TRUE_FALSE', 'True/False'),
            ('RATING', 'Confidence Rating'),
            ('ORDER', 'Put in Order'),
        ],
        default='TEXT'
    )
    correct_answer = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    points = models.IntegerField(default=10)
    hint = models.TextField(blank=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.minigame.title} - Q{self.order}"
    
    if TYPE_CHECKING:
        options: models.Manager["QuestionOption"]
        id: int


class QuestionOption(models.Model):
    """Options for multiple choice questions"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.question} - {self.option_text[:50]}"
    
    if TYPE_CHECKING:
        id: int


class PlayerProgress(models.Model):
    """Track player progress on minigames"""
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='progress')
    minigame = models.ForeignKey(Minigame, on_delete=models.CASCADE)
    is_completed = models.BooleanField(default=False)
    score = models.IntegerField(default=0)
    percentage = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)]
    )
    attempts = models.IntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    approved_by_admin = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['player', 'minigame']
    
    def __str__(self):
        return f"{self.player.user.username} - {self.minigame.title}"


class Submission(models.Model):
    """Player submissions for challenges requiring proof"""
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='submissions')
    minigame = models.ForeignKey(Minigame, on_delete=models.CASCADE)
    submission_text = models.TextField(blank=True)
    submission_image = models.ImageField(upload_to='submissions/', blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    admin_feedback = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.player.user.username} - {self.minigame.title} - {self.submitted_at.strftime('%Y-%m-%d')}"


class DailyMessage(models.Model):
    """Daily random messages for the player"""
    message = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.CharField(
        max_length=50,
        choices=[
            ('LOVE', 'Love Message'),
            ('MOTIVATION', 'Motivation'),
            ('FUNNY', 'Funny'),
            ('ROMANTIC', 'Romantic'),
            ('ENCOURAGEMENT', 'Encouragement'),
            ('QUESTION', 'Conversation Question'),
        ],
        default='LOVE'
    )
    
    def __str__(self):
        return f"{self.category} - {self.message[:50]}..."


class DailyMessageLog(models.Model):
    """Track which messages were shown to prevent repeats"""
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE)
    message = models.ForeignKey(DailyMessage, on_delete=models.CASCADE)
    shown_date = models.DateField(auto_now_add=True)
    was_claimed = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['player', 'shown_date']
    
    def __str__(self):
        return f"{self.player.user.username} - {self.shown_date}"


class Memory(models.Model):
    """Memories with photos tied to calendar dates"""
    date = models.DateField()
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='memories/')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['date']
        verbose_name_plural = 'Memories'
    
    def __str__(self):
        return f"{self.date.strftime('%Y-%m-%d')} - {self.title}"


class Reward(models.Model):
    """Rewards that can be unlocked"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    reward_type = models.CharField(
        max_length=50,
        choices=[
            ('MESSAGE', 'Special Message'),
            ('HINT', 'Hint for Puzzle'),
            ('UNLOCK', 'Unlock Content'),
            ('VOUCHER', 'Real-life Voucher'),
            ('COLLECTIBLE', 'Collectible Item'),
            ('BOOST', 'Streak Boost'),
            ('EXTRA_QUESTION', 'Extra Question Chance'),
            ('EXTRA_SPIN', 'Extra Spin Chance'),
            ('EXTRA_MEMORY', 'Extra Memory Sneak Peek'),
            ('EXTRA_DAILY_MESSAGE', 'Extra Daily Message Chance'),
        ],
        default='MESSAGE'
    )
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to='rewards/', blank=True, null=True)
    is_reusable = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.reward_type} - {self.title}"


class PlayerReward(models.Model):
    """Track rewards earned by player"""
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE, related_name='rewards')
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
    is_claimed = models.BooleanField(default=False)
    claimed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.player.user.username} - {self.reward.title}"


class Collection(models.Model):
    """Collections of items to complete"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    total_items = models.IntegerField()
    completion_reward = models.ForeignKey(Reward, on_delete=models.SET_NULL, null=True, blank=True)
    icon = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return self.name
    
    if TYPE_CHECKING:
        items: models.Manager["CollectionItem"]
        id: int


class CollectionItem(models.Model):
    """Individual items in a collection"""
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='collection_items/', blank=True, null=True)
    unlock_condition = models.TextField(help_text="Description of how to unlock")
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.collection.name} - {self.name}"


class PlayerCollectionItem(models.Model):
    """Track which collection items player has"""
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE)
    item = models.ForeignKey(CollectionItem, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['player', 'item']
    
    def __str__(self):
        return f"{self.player.user.username} - {self.item.name}"


class SpinWheel(models.Model):
    """Spin the wheel rewards"""
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE)
    probability = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Probability percentage (0-100)"
    )
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.reward.title} ({self.probability}%)"


class SpinLog(models.Model):
    """Track player spins"""
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE)
    reward_won = models.ForeignKey(Reward, on_delete=models.CASCADE)
    spun_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.player.user.username} - {self.spun_at.strftime('%Y-%m-%d')}"


class BingoCard(models.Model):
    """Bingo card template"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    size = models.IntegerField(default=9, choices=[(9, '3x3'), (16, '4x4')])
    duration_days = models.IntegerField(default=7, help_text="How many days to complete")
    reward = models.ForeignKey(Reward, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.title
    
    if TYPE_CHECKING:
        squares: models.Manager["BingoSquare"]
        id: int


class BingoSquare(models.Model):
    """Individual squares on bingo card"""
    card = models.ForeignKey(BingoCard, on_delete=models.CASCADE, related_name='squares')
    task = models.CharField(max_length=200)
    position = models.IntegerField()
    
    class Meta:
        ordering = ['position']
    
    def __str__(self):
        return f"{self.card.title} - {self.task[:30]}"


class PlayerBingoProgress(models.Model):
    """Track player progress on bingo cards"""
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE)
    card = models.ForeignKey(BingoCard, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_squares = models.JSONField(default=list)  # List of completed position numbers
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.player.user.username} - {self.card.title}"


class StandaloneQuestion(models.Model):
    """Questions that don't belong to a minigame"""
    text = models.TextField()
    default_points = models.IntegerField(default=10, help_text="Points awarded for a good answer")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:50]


class PlayerQuestionResponse(models.Model):
    """Player responses to standalone questions"""
    player = models.ForeignKey(PlayerProfile, on_delete=models.CASCADE)
    question = models.ForeignKey(StandaloneQuestion, on_delete=models.CASCADE)
    response_text = models.TextField()
    admin_score = models.IntegerField(default=0)
    admin_feedback = models.TextField(blank=True, help_text="Optional feedback for the player")
    is_graded = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.player.user.username} - {self.question.text[:30]}"
