from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.player_dashboard, name='player_dashboard'),
    
    # Daily features
    path('daily-message/', views.daily_message, name='daily_message'),
    path('claim-daily/', views.claim_daily_reward, name='claim_daily_reward'),
    path('memories/', views.memories_view, name='memories'),
    
    # Levels and minigames
    path('level/<int:level_number>/', views.level_detail, name='level_detail'),
    path('minigame/<int:minigame_id>/', views.minigame_detail, name='minigame_detail'),
    path('minigame/<int:minigame_id>/play/', views.play_minigame, name='play_minigame'),
    path('minigame/<int:minigame_id>/submit/', views.submit_minigame, name='submit_minigame'),
    
    # Rewards
    path('rewards/', views.rewards_view, name='rewards'),
    path('spin-wheel/', views.spin_wheel, name='spin_wheel'),
    
    # Collections
    path('collections/', views.collections_view, name='collections'),
    path('collections/claim/<int:reward_id>/', views.claim_listing_reward, name='claim_listing_reward'),
    
    # Questions
    path('questions/', views.questions_view, name='questions'),
    
    # Bingo
    path('bingo/', views.bingo_view, name='bingo'),
    path('bingo/<int:card_id>/', views.bingo_card_detail, name='bingo_card_detail'),
    path('bingo/<int:card_id>/toggle/<int:position>/', views.toggle_bingo_square, name='toggle_bingo_square'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
]
