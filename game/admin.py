from django.contrib import admin
from django.utils.html import format_html
from django.shortcuts import render
from django.contrib import messages
from django.contrib.admin import helpers
from django.utils import timezone
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    PlayerProfile, Level, MinigameType, Minigame, Question, QuestionOption,
    PlayerProgress, Submission, DailyMessage, DailyMessageLog, Memory, Reward,
    PlayerReward, Collection, CollectionItem, PlayerCollectionItem, SpinWheel,
    SpinLog, BingoCard, BingoSquare, PlayerBingoProgress,
    StandaloneQuestion, PlayerQuestionResponse
)


def _auto_unlock_levels(profile: PlayerProfile):
    levels = Level.objects.all().order_by('number')
    max_unlocked = profile.current_level or 1
    for lvl in levels:
        if lvl.number == 1:
            max_unlocked = max(max_unlocked, 1)
            continue
        if lvl.requires_admin_approval:
            continue
        if profile.total_score >= (lvl.required_score or 0):
            max_unlocked = max(max_unlocked, lvl.number)
    if max_unlocked > (profile.current_level or 1):
        profile.current_level = max_unlocked
        profile.save()


class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    extra = 1


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    show_change_link = True


class BingoSquareInline(admin.TabularInline):
    model = BingoSquare
    extra = 9


class CollectionItemInline(admin.TabularInline):
    model = CollectionItem
    extra = 3


@admin.register(PlayerProfile)
class PlayerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'current_level', 'total_score', 'streak_days', 'can_retry_daily', 'can_retry_spin', 'can_retry_question', 'can_view_extra_memory')
    list_editable = ('can_retry_daily', 'can_retry_spin', 'can_retry_question', 'can_view_extra_memory')
    search_fields = ('user__username',)
    list_filter = ('can_retry_daily', 'can_retry_spin', 'can_retry_question', 'can_view_extra_memory', 'current_level')



@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ['number', 'title', 'required_score', 'requires_admin_approval', 'is_locked']
    list_filter = ['is_locked', 'requires_admin_approval']
    search_fields = ['title', 'description']
    ordering = ['number']


@admin.register(MinigameType)
class MinigameTypeAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'name', 'icon']
    search_fields = ['display_name', 'name']


@admin.register(Minigame)
class MinigameAdmin(admin.ModelAdmin):
    list_display = ['title', 'game_type', 'level', 'is_locked', 'points_reward', 'order']
    list_filter = ['game_type', 'level', 'is_locked']
    search_fields = ['title', 'description']
    inlines = [QuestionInline]
    ordering = ['level__number', 'order']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text_short', 'minigame', 'question_type', 'points', 'order']
    list_filter = ['question_type', 'minigame__game_type']
    search_fields = ['question_text']
    inlines = [QuestionOptionInline]
    
    def question_text_short(self, obj):
        if not obj.question_text:
            return ""
        return obj.question_text[:50] + '...' if len(obj.question_text) > 50 else obj.question_text
    question_text_short.short_description = 'Question'


@admin.register(PlayerProgress)
class PlayerProgressAdmin(admin.ModelAdmin):
    list_display = ['player', 'minigame', 'is_completed', 'score', 'percentage', 'approved_by_admin']
    list_filter = ['is_completed', 'approved_by_admin', 'minigame__game_type']
    search_fields = ['player__user__username', 'minigame__title']
    readonly_fields = ['completed_at']
    actions = ['mark_completed_and_award']
    
    fieldsets = (
        ('Player Info', {
            'fields': ('player', 'minigame')
        }),
        ('Progress', {
            'fields': ('is_completed', 'score', 'percentage', 'attempts', 'completed_at')
        }),
        ('Admin Review', {
            'fields': ('approved_by_admin', 'admin_notes')
        }),
    )

    def mark_completed_and_award(self, request, queryset):
        count = 0
        for prog in queryset:
            if not prog.is_completed:
                prog.is_completed = True
                prog.approved_by_admin = True
                prog.completed_at = timezone.now()
                if prog.percentage < 100:
                    prog.percentage = 100
                if prog.score < prog.minigame.points_reward:
                    prog.score = prog.minigame.points_reward
                prog.save()
                profile = prog.player
                profile.total_score += prog.minigame.points_reward
                profile.save()
                _auto_unlock_levels(profile)
                count += 1
        self.message_user(request, f"Marked {count} progresses completed and awarded points.")
    mark_completed_and_award.short_description = 'Mark completed and award points'


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['player', 'minigame', 'submitted_at', 'is_approved', 'has_image']
    list_filter = ['is_approved', 'submitted_at']
    search_fields = ['player__user__username', 'minigame__title']
    readonly_fields = ['submitted_at', 'submission_image_preview']
    actions = ['approve_selected_submissions']
    
    fieldsets = (
        ('Submission Info', {
            'fields': ('player', 'minigame', 'submitted_at')
        }),
        ('Content', {
            'fields': ('submission_text', 'submission_image', 'submission_image_preview')
        }),
        ('Review', {
            'fields': ('is_approved', 'admin_feedback', 'reviewed_at')
        }),
    )
    
    def has_image(self, obj):
        return '✓' if obj.submission_image else '✗'
    has_image.short_description = 'Image'
    
    def submission_image_preview(self, obj):
        if obj.submission_image:
            return format_html('<img src="{}" style="max-width: 300px; max-height: 300px;" />', obj.submission_image.url)
        return "No image"
    submission_image_preview.short_description = 'Image Preview'

    def approve_selected_submissions(self, request, queryset):
        approved_count = 0
        for sub in queryset:
            if not sub.is_approved:
                sub.is_approved = True
                sub.reviewed_at = timezone.now()
                sub.save()
                progress, _ = PlayerProgress.objects.get_or_create(
                    player=sub.player,
                    minigame=sub.minigame
                )
                if not progress.is_completed:
                    progress.is_completed = True
                    progress.approved_by_admin = True
                    progress.completed_at = timezone.now()
                    progress.score = max(progress.score, sub.minigame.points_reward)
                    progress.percentage = max(progress.percentage, 100)
                    progress.save()
                    profile = sub.player
                    profile.total_score += sub.minigame.points_reward
                    profile.save()
                    _auto_unlock_levels(profile)
                approved_count += 1
        self.message_user(request, f"Approved {approved_count} submissions and awarded points.")
    approve_selected_submissions.short_description = 'Approve and award points'


@admin.register(DailyMessage)
class DailyMessageAdmin(admin.ModelAdmin):
    list_display = ['message_preview', 'category', 'is_active', 'created_at']
    list_filter = ['category', 'is_active']
    search_fields = ['message']
    
    def message_preview(self, obj):
        return obj.message[:60] + '...' if len(obj.message) > 60 else obj.message
    message_preview.short_description = 'Message'


@admin.register(Memory)
class MemoryAdmin(admin.ModelAdmin):
    list_display = ['date', 'title', 'is_active', 'image_preview']
    list_filter = ['is_active', 'date']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'image_preview']
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width: 100px; max-height: 100px;" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Preview'


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ['title', 'reward_type', 'is_reusable']
    list_editable = ['is_reusable']
    list_filter = ['reward_type', 'is_reusable']
    search_fields = ['title', 'description']
    actions = ['set_reusable_bulk']

    def set_reusable_bulk(self, request, queryset):
        if 'apply' in request.POST:
            is_reusable = 'is_reusable' in request.POST
            updated = queryset.update(is_reusable=is_reusable)
            self.message_user(request, f"Updated {updated} rewards. Reusable set to: {is_reusable}")
            return None
        
        return render(request, 'admin/set_reusable.html', context={
            'items': queryset,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'opts': self.model._meta,
        })
    set_reusable_bulk.short_description = "Set reusable status for selected items..."


@admin.register(PlayerReward)
class PlayerRewardAdmin(admin.ModelAdmin):
    list_display = ['player', 'reward', 'earned_at', 'is_claimed', 'claimed_at']
    list_filter = ['is_claimed', 'reward__reward_type']
    search_fields = ['player__user__username', 'reward__title']
    readonly_fields = ['earned_at']


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'total_items', 'completion_reward', 'icon']
    search_fields = ['name', 'description']
    inlines = [CollectionItemInline]


@admin.register(SpinWheel)
class SpinWheelAdmin(admin.ModelAdmin):
    list_display = ['reward', 'probability', 'is_active']
    list_editable = ['probability', 'is_active']
    list_filter = ['is_active']
    actions = ['set_probability_bulk', 'distribute_evenly']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('reward')

    def distribute_evenly(self, request, queryset):
        count = queryset.count()
        if count > 0:
            prob = round(100.0 / count, 2)
            queryset.update(probability=prob)
            self.message_user(request, f"Set probability to {prob}% for {count} items.")
    distribute_evenly.short_description = "Distribute 100%% evenly among selected"

    def set_probability_bulk(self, request, queryset):
        if 'apply' in request.POST:
            try:
                new_prob = float(request.POST.get('probability'))
                updated = queryset.update(probability=new_prob)
                self.message_user(request, f"Updated {updated} items to {new_prob}% probability.")
                return None
            except (ValueError, TypeError):
                self.message_user(request, "Invalid probability value.", level=messages.ERROR)
        
        return render(request, 'admin/set_probability.html', context={
            'items': queryset,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            'opts': self.model._meta,
        })
    set_probability_bulk.short_description = "Set probability for selected items..."


@admin.register(BingoCard)
class BingoCardAdmin(admin.ModelAdmin):
    list_display = ['title', 'size', 'duration_days', 'is_active']
    list_filter = ['is_active', 'size']
    search_fields = ['title', 'description']
    inlines = [BingoSquareInline]


@admin.register(PlayerBingoProgress)
class PlayerBingoProgressAdmin(admin.ModelAdmin):
    list_display = ['player', 'card', 'started_at', 'is_completed', 'completed_at']
    list_filter = ['is_completed']
    search_fields = ['player__user__username', 'card__title']
    readonly_fields = ['started_at']


@admin.register(StandaloneQuestion)
class StandaloneQuestionAdmin(admin.ModelAdmin):
    list_display = ['text_preview', 'default_points', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['text']

    def text_preview(self, obj):
        return obj.text[:60] + '...' if len(obj.text) > 60 else obj.text


@admin.register(PlayerQuestionResponse)
class PlayerQuestionResponseAdmin(admin.ModelAdmin):
    list_display = ['player', 'question_preview', 'response_preview', 'admin_score', 'is_graded', 'submitted_at']
    list_filter = ['is_graded']
    search_fields = ['player__user__username', 'question__text', 'response_text', 'admin_feedback']
    readonly_fields = ['submitted_at', 'player', 'question', 'response_text']
    
    def question_preview(self, obj):
        return obj.question.text[:30] + '...'
    
    def response_preview(self, obj):
        return obj.response_text[:50] + '...'

    def save_model(self, request, obj, form, change):
        # Check if we are grading this for the first time
        if change and 'is_graded' in form.changed_data and obj.is_graded:
            # Add points to player profile
            profile = obj.player
            profile.total_score += obj.admin_score
            profile.save()
            
            # Check for level up
            _auto_unlock_levels(profile)
            
            self.message_user(request, f"Added {obj.admin_score} points to {profile.user.username}'s score.")
        
        super().save_model(request, obj, form, change)


# Register remaining models with basic admin
admin.site.register(QuestionOption)
admin.site.register(DailyMessageLog)
admin.site.register(CollectionItem)
admin.site.register(PlayerCollectionItem)
admin.site.register(SpinLog)
admin.site.register(BingoSquare)

# Customize admin site
admin.site.site_header = "Love App Admin"
admin.site.site_title = "Love App"
admin.site.index_title = "Manage Your Love Game"

# --- Integrare Profil Jucător direct în pagina de User ---

class PlayerProfileInline(admin.StackedInline):
    model = PlayerProfile
    can_delete = False
    verbose_name_plural = 'Player Profile Settings'

class UserAdmin(BaseUserAdmin):
    inlines = (PlayerProfileInline,)

# Re-înregistrăm User-ul pentru a include și profilul
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
