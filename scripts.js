document.addEventListener('DOMContentLoaded', function () {
    loadNextRecommendation();
});

async function loadNextRecommendation() {
    console.log("Fetching next recommendation...");
    try {
        const response = await fetch('/get_recommendations');
        if (response.ok) {
            const game = await response.json();
            console.log("Fetched game:", game);
            if (game.error) {
                document.getElementById('recommendation-card').style.display = 'none';
                document.getElementById('no-games-message').style.display = 'block';
            } else {
                document.getElementById('game-title').innerText = game.name;
                document.getElementById('game-image').src = game.background_image;
                document.getElementById('game-genres').innerText = `Genres: ${game.genres.join(', ')}`;
                document.getElementById('game-platforms').innerText = `Platforms: ${game.platforms.join(', ')}`;
                document.getElementById('recommendation-card').style.display = 'block';
                document.getElementById('no-games-message').style.display = 'none';
                document.getElementById('like-button').onclick = function () {
                    likeGame(game.id, game.name);
                };
                document.getElementById('dislike-button').onclick = function () {
                    loadNextRecommendation();
                };
            }
        } else {
            console.log("Failed to fetch recommendation:", response.status);
            document.getElementById('recommendation-card').style.display = 'none';
            document.getElementById('no-games-message').style.display = 'block';
        }
    } catch (error) {
        console.error("Error fetching recommendation:", error);
        document.getElementById('recommendation-card').style.display = 'none';
        document.getElementById('no-games-message').style.display = 'block';
    }
}

async function likeGame(game_id, game_name) {
    console.log("Liking game:", game_id, game_name);
    try {
        const response = await fetch('/like', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ game_id, game_name })
        });
        console.log("Liked game response:", response);
        loadNextRecommendation();
    } catch (error) {
        console.error("Error liking game:", error);
    }
}
