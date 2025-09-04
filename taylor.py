from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import logging


# Initialize FastMCP server
mcp = FastMCP("taylor")

# Constants
SONGS_API_BASE = "https://api.lyrics.ovh/v1"
ARTIST = "Taylor Swift"

async def make_song_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {        
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


@mcp.tool()
async get_song(song_tittle: str) -> str:
    songs_url = f"{SONGS_API_BASE}/{ARTIST}/{song_tittle}"
    logging.info(f"Processing request for song: {song_tittle}\n")

    lyrics = await make_song_request(url=url)

    if not lyrics:
        return "Unable to fetch detailed lyrics for that song."

    return lyrics


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')