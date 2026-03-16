# Love App

## Introduction

The Love App is a gamified web application designed to help couples strengthen their relationship through a variety of fun and interactive activities. It's a private and personalized space where two people can connect, reminisce, and grow together. The app uses a level-based system with points, rewards, and daily challenges to keep the experience engaging and exciting.

## Features

### Authentication and User Management
-   **User Registration**: New users can create an account with a unique username and password.
-   **User Login**: Registered users can log in to access their personalized dashboard.
-   **Player Profile**: Each user has a profile that tracks their progress, including their current level, total score, and daily login streak.

### Gamification Elements
-   **Levels**: The app is structured around levels, each with a unique theme and set of challenges. Players unlock new levels by earning points.
-   **Points**: Players earn points by completing minigames, answering questions, and participating in daily activities.
-   **Daily Login Streak**: The app tracks consecutive daily logins and displays a streak to encourage regular engagement.
-   **Rewards**: Players can earn a variety of rewards, such as special messages, hints for puzzles, and even real-life vouchers.
-   **Collections**: A history of all earned rewards is kept in a collections section.
-   **Spin the Wheel**: A daily spin-the-wheel game gives players a chance to win random rewards.
-   **Bingo**: A romantic bingo game with a grid of tasks to complete for a special reward.

### Core Activities
-   **Daily Messages**: Each day, players receive a unique, randomly selected message that can be a love note, a motivational quote, or a conversation starter.
-   **Memories**: Players can view photos and memories associated with the current date, creating a "this day in history" experience for their relationship.
-g   **Minigames**: A wide variety of minigames are available, including:
    -   **Real Life Challenges**: Tasks to be completed in the real world.
    -   **Verse/Quote Completion**: Finishing a romantic verse or quote.
    -   **Timeline Challenge**: Arranging events in chronological order.
    -   **Guess the Place**: Identifying a location from a photo.
    -   **Quizzes**: Answering questions about the relationship or other topics.
    -   And many more!
-   **Standalone Questions**: The app presents thought-provoking questions to spark deep conversations. Players can submit their answers, which can then be reviewed by their partner.

### Admin Features
-   **Admin Dashboard**: A Django admin interface for managing all aspects of the game, including users, levels, minigames, questions, and rewards.
-   **Manual Approval**: Some levels and submissions require admin approval, giving the couple control over the game's progression.
-   **Content Management**: The admin can easily add new daily messages, memories, minigames, and questions.

## Technologies Used

-   **Backend**:
    -   **Python**: The core programming language for the backend.
    -   **Django**: A high-level Python web framework for rapid development.
    -   **Django REST Framework**: Used for creating a browsable API (although not the primary focus of the current implementation).
-   **Frontend**:
    -   **HTML**: The standard markup language for creating web pages.
    -   **CSS**: Used for styling the application and creating a visually appealing user interface.
    -   **JavaScript**: For interactive features and dynamic content.
-   **Database**:
    -   **SQLite**: The default database for Django, used for its simplicity and ease of setup.

## Database Schema

The application uses a comprehensive set of database models to store all game-related data:

-   `PlayerProfile`: Stores player-specific data, linked to the default Django `User` model.
-   `Level`: Defines the game levels.
-   `MinigameType`: Defines the different types of minigames.
-   `Minigame`: Represents individual minigames.
-   `Question` and `QuestionOption`: Store questions and their options for quizzes.
-   `PlayerProgress`: Tracks player progress on minigames.
-   `Submission`: Stores player submissions for challenges.
-   `DailyMessage` and `DailyMessageLog`: Manage daily messages.
-   `Memory`: Stores memories with photos.
-   `Reward` and `PlayerReward`: Manage rewards and track which players have earned them.
-   `Collection`, `CollectionItem`, and `PlayerCollectionItem`: Manage collections of items.
-   `SpinWheel` and `SpinLog`: Manage the spin-the-wheel game.
-   `BingoCard`, `BingoSquare`, and `PlayerBingoProgress`: Manage the bingo game.
-   `StandaloneQuestion` and `PlayerQuestionResponse`: Manage standalone questions and their responses.

## How to Run the Project

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    ```
2.  **Create a virtual environment**:
    ```bash
    python -m venv .venv
    ```
3.  **Activate the virtual environment**:
    -   On Windows:
        ```bash
        .venv\Scripts\activate
        ```
    -   On macOS/Linux:
        ```bash
        source .venv/bin/activate
        ```
4.  **Install the dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
5.  **Run the migrations**:
    ```bash
    python manage.py migrate
    ```
6.  **Create a superuser**:
    ```bash
    python manage.py createsuperuser
    ```
7.  **Run the development server**:
    ```bash
    python manage.py runserver
    ```
8.  **Access the application**: Open your web browser and go to `http://127.0.0.1:8000/`.

## Project Structure

The project follows a standard Django project structure:

-   `config/`: Contains the main project configuration, including `settings.py` and `urls.py`.
-   `game/`: The main application, containing all the models, views, templates, and static files for the game.
-   `media/`: Stores user-uploaded media files, such as photos for memories and submissions.
-   `static/`: Stores static files like CSS and JavaScript.
-   `manage.py`: A command-line utility for interacting with the Django project.
-   `db.sqlite3`: The SQLite database file.
-   `requirements.txt`: A list of Python dependencies.
