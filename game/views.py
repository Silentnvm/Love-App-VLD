from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Q
from datetime import date, timedelta
import math
import random
import json

from .models import (
    PlayerProfile, Level, Minigame, Question, QuestionOption,
    PlayerProgress, Submission, DailyMessage, DailyMessageLog,
    Memory, Reward, PlayerReward, Collection, CollectionItem,
    PlayerCollectionItem, SpinWheel, SpinLog, BingoCard,
    BingoSquare, PlayerBingoProgress, StandaloneQuestion,
    PlayerQuestionResponse
)


def get_or_create_player_profile(user):
    """Helper function to get or create player profile"""
    profile, created = PlayerProfile.objects.get_or_create(user=user)
    
    # Update streak
    today = date.today()
    if profile.last_login_date:
        days_diff = (today - profile.last_login_date).days
        if days_diff == 1:
            profile.streak_days += 1
        elif days_diff > 1:
            profile.streak_days = 1
            
        # Reset daily bonus flags on new day
        if days_diff > 0:
            profile.can_view_extra_memory = False
    else:
        profile.streak_days = 1
    
    profile.last_login_date = today
    profile.save()
    
    return profile


def update_player_level(profile):
    """Auto-unlock levels based on total_score when admin approval is not required."""
    levels = Level.objects.all().order_by('number')
    max_unlocked = profile.current_level or 1
    for lvl in levels:
        if lvl.number == 1:
            max_unlocked = max(max_unlocked, 1)
            continue
        if lvl.requires_admin_approval:
            # Skip auto-unlock levels that require manual approval
            continue
        if profile.total_score >= (lvl.required_score or 0):
            max_unlocked = max(max_unlocked, lvl.number)
    if max_unlocked > (profile.current_level or 1):
        profile.current_level = max_unlocked
        profile.save()


def login_view(request):
    """Player login"""
    if request.user.is_authenticated:
        return redirect('player_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            get_or_create_player_profile(user)
            return redirect('player_dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'game/login.html')


def register(request):
    """Player registration"""
    if request.user.is_authenticated:
        return redirect('player_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password != confirm_password:
            messages.error(request, 'Parolele nu coincid!')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Acest username este deja folosit.')
        else:
            user = User.objects.create_user(username=username, password=password)
            login(request, user)
            get_or_create_player_profile(user)
            messages.success(request, f'Bun venit, {username}!')
            return redirect('player_dashboard')
    
    return render(request, 'game/register.html')


def logout_view(request):
    """Player logout"""
    logout(request)
    return redirect('login')


@login_required
def player_dashboard(request):
    """Main dashboard for player"""
    profile = get_or_create_player_profile(request.user)
    
    # Get current level and available minigames
    current_level = Level.objects.filter(number=profile.current_level).first()
    all_levels = Level.objects.all().order_by('number')
    
    # Get player progress
    completed_minigames = PlayerProgress.objects.filter(
        player=profile,
        is_completed=True
    ).count()
    
    # Check if daily message is available
    today = date.today()
    daily_claimed = DailyMessageLog.objects.filter(
        player=profile,
        shown_date=today,
        was_claimed=True
    ).exists()
    
    context = {
        'profile': profile,
        'current_level': current_level,
        'all_levels': all_levels,
        'completed_minigames': completed_minigames,
        'daily_claimed': daily_claimed,
    }
    
    return render(request, 'game/dashboard.html', context)


@login_required
def daily_message(request):
    """Show random daily message"""
    profile = get_or_create_player_profile(request.user)
    today = date.today()
    
    # Check if already shown today
    daily_log = DailyMessageLog.objects.filter(
        player=profile,
        shown_date=today
    ).first()
    
    # Check for admin permission (can_retry_daily)
    if daily_log and daily_log.was_claimed and profile.can_retry_daily:
        daily_log.delete()
        daily_log = None
        profile.can_retry_daily = False
        profile.save()
        messages.success(request, "Ai primit o șansă extra de la admin!")
    
    # Allow admin/superuser to get multiple messages (reset if claimed)
    if daily_log and daily_log.was_claimed and request.user.is_superuser:
        daily_log.delete()
        daily_log = None
    
    if daily_log:
        message = daily_log.message
    else:
        # Get all shown messages for this player
        shown_message_ids = DailyMessageLog.objects.filter(
            player=profile
        ).values_list('message_id', flat=True)
        
        # Get a random message that hasn't been shown
        available_messages = DailyMessage.objects.filter(
            is_active=True
        ).exclude(id__in=shown_message_ids)
        
        if available_messages.exists():
            message = random.choice(available_messages)
            daily_log = DailyMessageLog.objects.create(
                player=profile,
                message=message
            )
        else:
            message = None
    
    context = {
        'message': message,
        'daily_log': daily_log,
    }
    
    return render(request, 'game/daily_message.html', context)


@login_required
def claim_daily_reward(request):
    """Claim daily reward"""
    if request.method == 'POST':
        profile = get_or_create_player_profile(request.user)
        today = date.today()
        
        daily_log = DailyMessageLog.objects.filter(
            player=profile,
            shown_date=today
        ).first()
        
        if daily_log and not daily_log.was_claimed:
            daily_log.was_claimed = True
            daily_log.save()
            
            # Award points
            profile.total_score += 5
            profile.save()
            update_player_level(profile)
            
            messages.success(request, 'Daily reward claimed! +5 points')
        
        return redirect('daily_message')
    
    return redirect('player_dashboard')


@login_required
def memories_view(request):
    """Show memories for today's date"""
    profile = get_or_create_player_profile(request.user)
    today = date.today()
    
    # Get memories for today
    memories = Memory.objects.filter(
        is_active=True,
        date=today
    )
    
    # Also show all unlocked memories (past and today)
    recent_memories = Memory.objects.filter(
        is_active=True,
        date__lte=today
    ).order_by('-date')
    
    # Check for bonus memory (Sneak Peek)
    bonus_memory = None
    if profile.can_view_extra_memory:
        # Get the next upcoming memory
        bonus_memory = Memory.objects.filter(is_active=True, date__gt=today).order_by('date').first()
    
    context = {
        'today_memories': memories,
        'recent_memories': recent_memories,
        'bonus_memory': bonus_memory,
        'profile': profile,
    }
    
    return render(request, 'game/memories.html', context)


@login_required
def level_detail(request, level_number):
    """Show level details and minigames"""
    profile = get_or_create_player_profile(request.user)
    level = get_object_or_404(Level, number=level_number)
    
    # Check if level is accessible
    if level.number > profile.current_level:
        messages.warning(request, 'This level is locked!')
        return redirect('player_dashboard')
    
    # Get minigames for this level
    minigames = Minigame.objects.filter(level=level)
    
    # Get player progress for each minigame
    progress_data = {}
    for minigame in minigames:
        progress = PlayerProgress.objects.filter(
            player=profile,
            minigame=minigame
        ).first()
        progress_data[minigame.pk] = progress
    
    context = {
        'level': level,
        'minigames': minigames,
        'progress_data': progress_data,
        'profile': profile,
    }
    
    return render(request, 'game/level_detail.html', context)


@login_required
def minigame_detail(request, minigame_id):
    """Show minigame details"""
    profile = get_or_create_player_profile(request.user)
    minigame = get_object_or_404(Minigame, id=minigame_id)
    
    # Check if accessible
    if minigame.is_locked or minigame.level.number > profile.current_level:
        messages.warning(request, 'This minigame is locked!')
        return redirect('player_dashboard')
    
    # Get or create progress
    progress, created = PlayerProgress.objects.get_or_create(
        player=profile,
        minigame=minigame
    )
    
    context = {
        'minigame': minigame,
        'progress': progress,
        'profile': profile,
    }
    
    return render(request, 'game/minigame_detail.html', context)


@login_required
def play_minigame(request, minigame_id):
    """Play a minigame"""
    profile = get_or_create_player_profile(request.user)
    minigame = get_object_or_404(Minigame, id=minigame_id)
    
    # Check if accessible
    if minigame.is_locked or minigame.level.number > profile.current_level:
        messages.warning(request, 'This minigame is locked!')
        return redirect('player_dashboard')
    
    # Get or create progress
    progress, created = PlayerProgress.objects.get_or_create(
        player=profile,
        minigame=minigame
    )
    
    # Get questions if applicable
    questions = minigame.questions.all().order_by('order')
    
    context = {
        'minigame': minigame,
        'progress': progress,
        'questions': questions,
        'profile': profile,
    }
    
    # Render different templates based on game type
    game_type = minigame.game_type.name
    template_map = {
        'VERSE_COMPLETION': 'game/minigames/verse_completion.html',
        'TIMELINE': 'game/minigames/timeline.html',
        'GUESS_PLACE': 'game/minigames/guess_place.html',
        'MEMORY_MATCH': 'game/minigames/memory_match.html',
        'QUIZ': 'game/minigames/quiz.html',
        'ANAGRAM': 'game/minigames/anagram.html',
        'WOULD_RATHER': 'game/minigames/would_rather.html',
        'REAL_CHALLENGE': 'game/minigames/real_challenge.html',
        'QUEST_PROOF': 'game/minigames/quest_proof.html',
    }
    
    template = template_map.get(game_type, 'game/minigames/default.html')
    
    return render(request, template, context)


@login_required
def submit_minigame(request, minigame_id):
    """Submit minigame answers"""
    if request.method != 'POST':
        return redirect('play_minigame', minigame_id=minigame_id)
    
    profile = get_or_create_player_profile(request.user)
    minigame = get_object_or_404(Minigame, id=minigame_id)
    
    # Get or create progress
    progress, created = PlayerProgress.objects.get_or_create(
        player=profile,
        minigame=minigame
    )
    
    progress.attempts += 1
    
    # Handle different submission types
    game_type = minigame.game_type.name
    
    if game_type in ['REAL_CHALLENGE', 'QUEST_PROOF']:
        # Handle submission with proof
        submission_text = request.POST.get('submission_text', '')
        submission_image = request.FILES.get('submission_image')
        
        Submission.objects.create(
            player=profile,
            minigame=minigame,
            submission_text=submission_text,
            submission_image=submission_image
        )
        
        messages.success(request, 'Submission received! Waiting for admin approval.')
        progress.save()
        
    else:
        # Handle quiz/question based minigames
        score = 0
        total_points = 0
        
        questions = minigame.questions.all()
        for question in questions:
            total_points += question.points
            user_answer = request.POST.get(f'question_{question.id}')
            
            if user_answer:
                # Simple answer checking (you can make this more sophisticated)
                if question.question_type == 'MULTIPLE':
                    correct_option = question.options.filter(is_correct=True).first()
                    if correct_option and str(correct_option.id) == user_answer:
                        score += question.points
                elif question.question_type == 'TEXT':
                    if user_answer.lower().strip() == question.correct_answer.lower().strip():
                        score += question.points
        
        # Calculate percentage
        percentage = (score / total_points * 100) if total_points > 0 else 0
        
        progress.score = score
        progress.percentage = percentage
        
        # Check if passed (e.g., 70% threshold)
        if percentage >= 70:
            if not progress.is_completed:
                progress.is_completed = True
                progress.completed_at = timezone.now()
                
                # Award points
                profile.total_score += minigame.points_reward
                profile.save()
                update_player_level(profile)
                
                messages.success(request, f'Congratulations! You scored {percentage:.1f}% and earned {minigame.points_reward} points!')
            else:
                messages.info(request, f'Good job! You scored {percentage:.1f}%. (Already completed)')
        else:
            messages.warning(request, f'You scored {percentage:.1f}%. Try again to get 70% or higher!')
        
        progress.save()
    
    return redirect('minigame_detail', minigame_id=minigame_id)


@login_required
def rewards_view(request):
    """Show player rewards"""
    profile = get_or_create_player_profile(request.user)
    
    # Get earned rewards
    earned_rewards = PlayerReward.objects.filter(
        player=profile
    ).select_related('reward').order_by('-earned_at')
    
    context = {
        'profile': profile,
        'earned_rewards': earned_rewards,
    }
    
    return render(request, 'game/rewards.html', context)


@login_required
def spin_wheel(request):
    """Spin the wheel for rewards"""
    profile = get_or_create_player_profile(request.user)
    today = date.today()
    
    # Check if already spun today
    today_spins = SpinLog.objects.filter(
        player=profile,
        spun_at__date=today
    )
    already_spun = today_spins.exists()
    
    # Check for admin permission (can_retry_spin)
    if already_spun and profile.can_retry_spin:
        today_spins.delete()
        already_spun = False
        profile.can_retry_spin = False
        profile.save()
        messages.success(request, "Ai primit o șansă extra la roată de la admin!")
    
    if request.method == 'POST' and not already_spun:
        # Get active wheel items
        wheel_items = list(SpinWheel.objects.filter(is_active=True))
        
        if wheel_items:
            # Weighted random selection
            total_prob = sum(item.probability for item in wheel_items)
            rand = random.uniform(0, total_prob)
            
            cumulative = 0
            won_reward = None
            for item in wheel_items:
                cumulative += item.probability
                if rand <= cumulative:
                    won_reward = item.reward
                    break
            
            if won_reward:
                # Log the spin
                SpinLog.objects.create(
                    player=profile,
                    reward_won=won_reward
                )
                
                # Grant reward
                PlayerReward.objects.create(
                    player=profile,
                    reward=won_reward
                )
                
                messages.success(request, f'You won: {won_reward.title}!')
                return redirect('rewards')
    
    context = {
        'profile': profile,
        'already_spun': already_spun,
        'wheel_items': SpinWheel.objects.filter(is_active=True),
    }
    
    return render(request, 'game/spin_wheel.html', context)


@login_required
def collections_view(request):
    """Show all earned rewards history (Collections)"""
    profile = get_or_create_player_profile(request.user)
    
    # Fetch all earned rewards history
    rewards_history = PlayerReward.objects.filter(
        player=profile
    ).select_related('reward').order_by('-earned_at')
    
    context = {
        'profile': profile,
        'rewards_history': rewards_history,
    }
    
    return render(request, 'game/collections.html', context)


@login_required
def claim_listing_reward(request, reward_id):
    """Claim a specific reward from the collections list"""
    if request.method == 'POST':
        profile = get_or_create_player_profile(request.user)
        player_reward = get_object_or_404(PlayerReward, id=reward_id, player=profile)
        
        if not player_reward.is_claimed:
            # Apply reward effects only when claimed
            rt = player_reward.reward.reward_type
            
            if rt == 'EXTRA_SPIN':
                if profile.can_retry_spin:
                    messages.warning(request, "Ai deja o rotire extra activă! Folosește-o înainte să revendici alta.")
                    return redirect('collections')
                profile.can_retry_spin = True
                profile.save()
            elif rt == 'EXTRA_QUESTION':
                if profile.can_retry_question:
                    messages.warning(request, "Ai deja o întrebare extra activă! Răspunde la ea înainte să revendici alta.")
                    return redirect('collections')
                profile.can_retry_question = True
                profile.save()
            elif rt == 'EXTRA_DAILY_MESSAGE':
                if profile.can_retry_daily:
                    messages.warning(request, "Ai deja un mesaj extra activ! Citește-l înainte să revendici altul.")
                    return redirect('collections')
                profile.can_retry_daily = True
                profile.save()
            elif rt == 'EXTRA_MEMORY':
                if profile.can_view_extra_memory:
                    messages.warning(request, "Ai deja o amintire extra activă! Vezi-o înainte să revendici alta.")
                    return redirect('collections')
                profile.can_view_extra_memory = True
                profile.save()
            
            player_reward.is_claimed = True
            player_reward.claimed_at = timezone.now()
            player_reward.save()
            
            msg = f"Claimed: {player_reward.reward.title}"
            if player_reward.reward.content:
                msg += f" - {player_reward.reward.content}"
            
            messages.success(request, msg)
        else:
            messages.warning(request, "This reward is already claimed!")
            
    return redirect('collections')


@login_required
def bingo_view(request):
    """Show active bingo cards"""
    profile = get_or_create_player_profile(request.user)
    
    # Get active bingo cards
    active_cards = BingoCard.objects.filter(is_active=True)
    
    # Get player's progress on each card
    player_progress = {}
    for card in active_cards:
        progress = PlayerBingoProgress.objects.filter(
            player=profile,
            card=card
        ).first()
        player_progress[card.id] = progress
    
    context = {
        'profile': profile,
        'active_cards': active_cards,
        'player_progress': player_progress,
    }
    
    return render(request, 'game/bingo.html', context)


@login_required
def bingo_card_detail(request, card_id):
    """Show bingo card detail"""
    profile = get_or_create_player_profile(request.user)
    card = get_object_or_404(BingoCard, id=card_id)
    
    # Get or create progress
    progress, created = PlayerBingoProgress.objects.get_or_create(
        player=profile,
        card=card
    )
    
    # Get all squares
    squares = card.squares.all()
    
    context = {
        'profile': profile,
        'card': card,
        'progress': progress,
        'squares': squares,
    }
    
    return render(request, 'game/bingo_card.html', context)


@login_required
def toggle_bingo_square(request, card_id, position):
    """Toggle bingo square completion"""
    if request.method != 'POST':
        return redirect('bingo_card_detail', card_id=card_id)
    
    profile = get_or_create_player_profile(request.user)
    card = get_object_or_404(BingoCard, id=card_id)
    
    progress, created = PlayerBingoProgress.objects.get_or_create(
        player=profile,
        card=card
    )
    
    completed = progress.completed_squares
    
    if position in completed:
        completed.remove(position)
    else:
        completed.append(position)
    
    progress.completed_squares = completed
    
    # Bingo completion: line (row/col/diag) detection
    n = int(math.sqrt(card.size)) if card.size in (9, 16) else None
    if n:
        s = set(completed)
        lines = []
        # rows
        for r in range(n):
            row = [(r * n) + c + 1 for c in range(n)]
            lines.append(row)
        # cols
        for c in range(n):
            col = [c + 1 + (r * n) for r in range(n)]
            lines.append(col)
        # diagonals
        diag1 = [1 + (n + 1) * k for k in range(n)]
        diag2 = [n + (n - 1) * k for k in range(n)]
        lines.append(diag1)
        lines.append(diag2)

        has_line = any(all(pos in s for pos in line) for line in lines)
        if has_line and not progress.is_completed:
            progress.is_completed = True
            progress.completed_at = timezone.now()
            if card.reward:
                PlayerReward.objects.create(
                    player=profile,
                    reward=card.reward
                )
                messages.success(request, f'Bingo completed! You earned: {card.reward.title}')
    
    progress.save()
    
    return redirect('bingo_card_detail', card_id=card_id)


@login_required
def questions_view(request):
    """Show conversation questions"""
    profile = get_or_create_player_profile(request.user)
    today = date.today()

    # Check if answered today
    answered_today = PlayerQuestionResponse.objects.filter(
        player=profile,
        submitted_at__date=today
    ).exists()

    # Determine if player can answer (not answered today OR has extra chance)
    can_answer = not answered_today or profile.can_retry_question

    if request.method == 'POST':
        if not can_answer:
            messages.error(request, "Ai răspuns deja la întrebarea zilei!")
            return redirect('questions')
            
        question_id = request.POST.get('question_id')
        response_text = request.POST.get('response_text')
        
        if question_id and response_text:
            question = get_object_or_404(StandaloneQuestion, id=question_id)
            
            # Consume extra chance if used
            if answered_today and profile.can_retry_question:
                profile.can_retry_question = False
                profile.save()
            
            PlayerQuestionResponse.objects.create(
                player=profile,
                question=question,
                response_text=response_text,
                admin_score=question.default_points  # Default suggestion for admin
            )
            messages.success(request, "Răspuns trimis! Așteaptă evaluarea adminului. ❤️")
            return redirect('questions')

    # Get IDs of questions already answered by this player
    answered_ids = PlayerQuestionResponse.objects.filter(player=profile).values_list('question_id', flat=True)
    
    # Get history of responses
    history = PlayerQuestionResponse.objects.filter(player=profile).select_related('question').order_by('-submitted_at')
    
    # Get one random unanswered question
    question = None
    limit_reached = False

    if can_answer:
        questions = StandaloneQuestion.objects.filter(is_active=True).exclude(id__in=answered_ids)
        if questions.exists():
            question = random.choice(questions)
    else:
        limit_reached = True
    
    context = {
        'profile': profile,
        'question': question,
        'limit_reached': limit_reached,
        'history': history,
    }
    
    return render(request, 'game/questions.html', context)


@login_required
def profile_view(request):
    """Show player profile"""
    profile = get_or_create_player_profile(request.user)
    
    # Get statistics
    total_completed = PlayerProgress.objects.filter(
        player=profile,
        is_completed=True
    ).count()
    
    total_rewards = PlayerReward.objects.filter(player=profile).count()
    
    context = {
        'profile': profile,
        'total_completed': total_completed,
        'total_rewards': total_rewards,
    }
    
    return render(request, 'game/profile.html', context)
