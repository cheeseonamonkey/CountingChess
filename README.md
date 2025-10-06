# Chess Game Analysis Tool

A Python-based chess analytics tool that fetches games from Chess.com, evaluates positions, and calculates strategic metrics to analyze player performance and game dynamics.

## Overview

This project provides a comprehensive framework for analyzing chess games by:
- Fetching game data from Chess.com's public API
- Evaluating chess positions using piece-square tables
- Computing positional metrics (openness, mobility, king safety, etc.)
- Analyzing games from a player's perspective
- Generating structured data for performance analysis

## Features

### Data Collection
- **User Game Fetching**: Retrieve all games for specified Chess.com usernames
- **Random Game Sampling**: Fetch random games from various countries and skill levels
- **Rate Limiting**: Built-in delays to respect Chess.com API limits

### Position Evaluation
- **FEN-based Evaluation**: Convert and evaluate chess positions from FEN notation
- **Piece-Square Tables**: Material and positional evaluation using optimized PST
- **Caching**: LRU cache for efficient repeated evaluations

### Strategic Metrics
- **Openness**: Measure of pawn structure and open files
- **Development**: Minor piece activation
- **Mobility**: Available moves for pieces
- **Sharpness**: Tactical complexity indicator
- **Center Control**: Evaluation of central square dominance
- **King Safety**: King position and exposure assessment
- **Pawn Structure**: Pawn formation quality
- **Space**: Territory control measurement

### Analysis Features
- **Perspective Analysis**: Analyze games from a specific player's viewpoint
- **Centipawn Loss**: Calculate blunder and inaccuracy metrics
- **Time Management**: Track time spent per move
- **Data Structuring**: Export to pandas DataFrame for further analysis

## Technologies

- **Python 3.11+**: Core programming language
- **httpx**: HTTP client for Chess.com API requests
- **python-chess**: Chess game parsing and move validation
- **pandas**: Data manipulation and analysis
- **asciichartpy**: Terminal-based visualization

## Project Structure

```
.
├── main.py              # Main orchestration script
├── Fetchers.py          # Chess.com API integration
├── Sunfish.py           # Position evaluation engine
├── Plotting.py          # Visualization utilities
├── pyproject.toml       # Project configuration
├── uv.lock              # Dependency lock file
└── *.csv                # Generated analysis data
```

### Core Modules

#### `Fetchers.py`
Handles all Chess.com API interactions:
- `fetch_all_users_games()`: Fetch complete game history for users
- `fetch_random_games()`: Sample games from random players
- `_verify_user_exists()`: Validate username before fetching
- `_fetch_user_archives()`: Retrieve game archive URLs
- `_fetch_archive_games()`: Fetch games from specific month/year

#### `Sunfish.py`
Position evaluation and metric calculation:
- `evaluate_fen()`: Static position evaluation using PST
- `calculate_metrics()`: Compute 8 strategic metrics
- `fen_to_board()`: Convert FEN to internal board representation
- Piece values: P=100, N=280, B=320, R=479, Q=929, K=60000

#### `main.py`
Main analysis pipeline:
- `process_game()`: Extract metrics from game PGN
- Perspective-based analysis (flip evaluations for Black)
- DataFrame construction with move-by-move data
- Multi-game aggregation

#### `Plotting.py`
Visualization tools:
- `plot_vectors()`: ASCII chart rendering for metric visualization

## Installation

### Prerequisites
- Python 3.11 or higher
- pip or uv package manager

### Setup

1. **Clone or download the project**

2. **Install dependencies**:
   ```bash
   pip install requests httpx python-chess pandas asciichartpy
   ```

   Or using the project configuration:
   ```bash
   pip install -e .
   ```

## Usage

### Basic Usage

Edit `main.py` to specify target usernames:

```python
myGames = Fetchers.fetch_all_users_games(
    ['username1', 'username2'],  # Your Chess.com usernames
    None,  # Fetch all games (or specify a limit)
    True   # Verbose output
)
```

Run the analysis:
```bash
python main.py
```

### Fetching Random Games

```python
randomGames = Fetchers.fetch_random_games(
    50,   # Number of games
    120,  # Days back to search
    True  # Verbose output
)
```

### Game Processing

```python
df = process_game(
    game,                        # chess.pgn.Game object
    perspective_user='username', # Analyze from this player's perspective
    verbose=True                 # Print move-by-move details
)
```

## Data Output

The analysis generates DataFrames with the following columns:

| Column | Description |
|--------|-------------|
| `eval` | Position evaluation (centipawns) |
| `openness` | Pawn structure openness metric |
| `development` | Minor piece development score |
| `mobility` | Total piece mobility |
| `sharpness` | Tactical complexity measure |
| `center_control` | Central square control |
| `king_safety` | King safety evaluation |
| `pawn_structure` | Pawn formation quality |
| `space` | Space advantage metric |
| `time_spent` | Seconds spent on move |
| `centipawn_loss` | CP loss from previous position |
| `winner` | Game result (white/black/draw) |
| `perspective_user` | Username being analyzed |
| `perspective_color` | Color from perspective (white/black) |

Data is indexed by `(game_id, move_id)` for multi-game analysis.

## Chess.com API Endpoints

The tool uses the following public API endpoints:

- User archives: `https://api.chess.com/pub/player/{username}/games/archives`
- Monthly games: `https://api.chess.com/pub/player/{username}/games/{year}/{month}`
- Country players: `https://api.chess.com/pub/country/{country}/players`

## Evaluation Algorithm

### Position Evaluation
- Uses piece-square tables (PST) adapted from Sunfish chess engine
- Evaluates material + positional value
- Returns centipawn score from White's perspective
- Automatically flips for Black's perspective in analysis

### Metric Calculation
All metrics are calculated from a single FEN string:
1. Parse board to 120-square representation
2. Single-pass piece iteration for efficiency
3. Compute all 8 metrics simultaneously
4. Apply perspective transformation if needed

## Performance Optimizations

- **LRU Caching**: `@lru_cache` on FEN evaluation and metrics (512-32896 entries)
- **Rate Limiting**: Automatic delays between API calls (5-35ms)
- **Efficient Parsing**: Optimized board representation for fast metric calculation
- **Batch Processing**: Process multiple games in sequence

## Example Output

```
===== My Game 1 =====

Result: 1-0 (Winner: white)
Perspective: username (white)

Move 1: e4
  Eval: 48, Time: 0s, CP Loss: 0
Move 2: d4
  Eval: 52, Time: 3s, CP Loss: 0
...
```

## Limitations

- Requires stable internet connection for Chess.com API
- Rate limited by Chess.com API policies
- Evaluation is static (no search/lookahead)
- Metrics are heuristic-based approximations

## Future Enhancements

- Integration with chess engines (Stockfish) for deeper analysis
- Machine learning models for pattern recognition
- Web-based visualization dashboard
- Export to standard chess formats (PGN with annotations)
- Comparative analysis between players

## License

This project uses algorithms adapted from the Sunfish chess engine for position evaluation.

## Attribution

- Position evaluation based on Sunfish chess engine piece-square tables
- Chess.com API for game data
- python-chess library for game parsing
