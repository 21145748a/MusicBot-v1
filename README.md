# MusicBot

A Discord music bot that plays music from YouTube.

## Prerequisites

- Python 3.8 or higher
- `pip` (Python package installer)

## Installation

1. Clone the repository:

    ```sh
    git clone https://github.com/yourusername/your-repo.git
    cd your-repo
    ```

2. Install the required dependencies:

    ```sh
    pip install -r requirements.txt
    ```

## Configuration

1. Create a `.env` file in the root directory of the project and add your Discord bot token and FFMPEG path:

    ```env
    DISCORD_TOKEN=your_discord_token
    FFMPEG=path_to_ffmpeg
    ```

## Running the Bot

1. Run the bot:

    ```sh
    python Main.py
    ```

## Files

- `MusicBot.py`: Contains the `MusicBot` class with all the bot commands and event handlers.
- `MusicControlView.py`: Contains the `MusicControlView` class with the button interactions.
- `Main.py`: Contains the `Main` class to run the bot.

## Commands

- `!join`: Join the bot to a voice channel.
- `!play <song_name/url>`: Play a song.
- `!playlist <playlist_url>`: Play a YouTube playlist.
- `!skip/!stop`: Skip the current song.
- `!list`: List the current queue.
- `!clear`: Clear the queue.
- `!pause`: Pause the current song.
- `!resume`: Resume the current song.
- `!quit`: Leave the voice channel.
- `!help`: Show the help message.

## License

This project is licensed under the MIT License.
