from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session
from models import db, User, LikedGame
import requests
from config import Config
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

routes = Blueprint('routes', __name__)

@routes.route('/')
def home():
    return redirect(url_for('routes.login'))

@routes.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        username = data['username']
        password = data['password']
        platform = request.form.getlist('platforms')
        genres = request.form.getlist('genres')
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('routes.register'))
        
        user = User(username=username, password=password, platform=','.join(platform), genres=','.join(genres))
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('routes.login'))
    return render_template('register.html')

@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        username = data['username']
        password = data['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session['user_id'] = user.id
            session['suggested_games'] = []
            flash('Login successful!', 'success')
            return redirect(url_for('routes.recommendations'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')

@routes.route('/recommendations')
def recommendations():
    return render_template('recommendations.html')

def fetch_games_from_rawg(max_pages=5):
    games = []
    page = 1
    while page <= max_pages:
        response = requests.get(f'https://api.rawg.io/api/games?key={Config.RAWG_API_KEY}&page={page}&page_size=40')
        if response.status_code == 200:
            page_games = response.json().get('results', [])
            if not page_games:
                break
            games.extend(page_games)
            page += 1
        else:
            print(f"Failed to fetch games: {response.status_code}")
            break
    print(f"Fetched {len(games)} games from RAWG API")
    return games

@routes.route('/get_recommendations', methods=['GET'])
def get_recommendations():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(user_id)
    liked_games = LikedGame.query.filter_by(user_id=user_id).all()
    liked_game_ids = {game.game_id for game in liked_games}

    suggested_games = session.get('suggested_games', [])

    print(f"User ID: {user_id}")
    print(f"Liked games: {liked_game_ids}")
    print(f"Suggested games: {suggested_games}")

    liked_genres = set()
    liked_platforms = set()
    liked_developers = set()
    liked_tags = set()
    liked_descriptions = []

    if liked_games:
        for liked_game in liked_games:
            game_id = liked_game.game_id
            game_response = requests.get(f'https://api.rawg.io/api/games/{game_id}?key={Config.RAWG_API_KEY}')
            if game_response.status_code == 200:
                game_data = game_response.json()
                for genre in game_data.get('genres', []):
                    liked_genres.add(genre['name'].lower())
                for platform in game_data.get('platforms', []):
                    liked_platforms.add(platform['platform']['name'].lower())
                for developer in game_data.get('developers', []):
                    liked_developers.add(developer['name'].lower())
                for tag in game_data.get('tags', []):
                    liked_tags.add(tag['name'].lower())
                description = game_data.get('description_raw', '')
                if description:
                    liked_descriptions.append(description)
            else:
                print(f"Failed to fetch liked game {game_id}: {game_response.status_code}")

    games = fetch_games_from_rawg()

    filtered_games = []
    for game in games:
        if game['id'] in liked_game_ids or str(game['id']) in suggested_games:
            continue

        game_platforms = [p['platform']['name'].lower() for p in game['platforms']]
        game_genres = [g['name'].lower() for g in game['genres']]
        game_developers = [d['name'].lower() for d in game.get('developers', [])]
        game_tags = [t['name'].lower() for t in game.get('tags', [])]

        if not liked_games or (
            any(platform in game_platforms for platform in liked_platforms) or
            any(genre in game_genres for genre in liked_genres) or
            any(developer in game_developers for developer in liked_developers) or
            any(tag in game_tags for tag in liked_tags)
        ):
            filtered_games.append(game)

    print(f"Filtered games count: {len(filtered_games)}")

    recommended_games = []
    if liked_descriptions and filtered_games:
        descriptions = [game.get('description_raw', '') for game in filtered_games if 'description_raw' in game]
        if descriptions:
            vectorizer = TfidfVectorizer().fit_transform(liked_descriptions + descriptions)
            vectors = vectorizer.toarray()
            cosine_matrix = cosine_similarity(vectors[:len(liked_descriptions)], vectors[len(liked_descriptions):])
            similarity_scores = cosine_matrix.mean(axis=0)
            recommended_indices = np.argsort(similarity_scores)[::-1]
            recommended_games = [filtered_games[i] for i in recommended_indices]

    if not recommended_games:
        recommended_games = filtered_games

    if not recommended_games:
        print("No recommendations found")
        return jsonify({'error': 'No recommendations found'}), 404

    game = recommended_games[0]
    game_data = {
        'id': game['id'],
        'name': game['name'],
        'background_image': game.get('background_image', ''),
        'genres': [genre['name'] for genre in game['genres']],
        'platforms': [platform['platform']['name'] for platform in game['platforms']]
    }

    suggested_games.append(str(game['id']))
    session['suggested_games'] = suggested_games

    print(f"Recommended game: {game_data}")
    return jsonify(game_data)

@routes.route('/like', methods=['POST'])
def like_game():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    game_id = data['game_id']
    game_name = data['game_name']
    liked_game = LikedGame(game_id=game_id, game_name=game_name, user_id=user_id)
    db.session.add(liked_game)
    db.session.commit()
    return jsonify(message="Game liked"), 201

@routes.route('/profile')
def profile():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('routes.login'))
    
    liked_games = LikedGame.query.filter_by(user_id=user_id).all()
    liked_game_details = []

    for liked_game in liked_games:
        game_id = liked_game.game_id
        game_response = requests.get(f'https://api.rawg.io/api/games/{game_id}?key={Config.RAWG_API_KEY}')
        if game_response.status_code == 200:
            game_data = game_response.json()
            liked_game_details.append({
                'id': liked_game.id,
                'game_id': liked_game.game_id,
                'game_name': liked_game.game_name,
                'rating': liked_game.rating,
                'background_image': game_data.get('background_image', '')
            })

    return render_template('profile.html', games=liked_game_details)

@routes.route('/rate', methods=['POST'])
def rate_game():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json()
    game_id = data['game_id']
    rating = data['rating']
    liked_game = LikedGame.query.filter_by(game_id=game_id, user_id=user_id).first()
    liked_game.rating = rating
    db.session.commit()
    return jsonify(message="Game rated"), 200

@routes.route('/preferences', methods=['GET'])
def get_preferences():
    platforms_response = requests.get(f'https://api.rawg.io/api/platforms?key={Config.RAWG_API_KEY}')
    genres_response = requests.get(f'https://api.rawg.io/api/genres?key={Config.RAWG_API_KEY}')
    
    if platforms_response.status_code == 200 and genres_response.status_code == 200:
        platforms = platforms_response.json()['results']
        genres = genres_response.json()['results']
        return jsonify({'platforms': platforms, 'genres': genres})
    else:
        return jsonify({'error': 'Failed to fetch preferences from RAWG API'}), 500
