from typing import Any, Dict
import httpx
from mcp.server.fastmcp import FastMCP
import logging
import re
from collections import Counter

# Initialize FastMCP server
mcp = FastMCP("taylor-swift-analyzer")

# Constants
SONGS_API_BASE = "https://api.lyrics.ovh/v1"
ARTIST = "Taylor Swift"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def make_song_request(url: str) -> dict[str, Any] | None:
    """Make a request to the lyrics API with proper error handling."""
    headers = {        
        "Accept": "application/json",
        "User-Agent": "TaylorSwiftMCPAnalyzer/1.0"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} for URL: {url}")
            return None
        except Exception as e:
            logger.error(f"Request error for URL {url}: {str(e)}")
            return None


def analyze_lyrics_content(lyrics: str) -> Dict[str, Any]:
    """
    Perform comprehensive analysis of song lyrics
    
    Args:
        lyrics: The song lyrics text
        
    Returns:
        Dictionary with detailed analysis results
    """
    if not lyrics or lyrics == "Lyrics not found.":
        return {"error": "No lyrics available for analysis"}
    
    lyrics_lower = lyrics.lower()
    
    # Emotional word categories
    positive_words = {
        'love', 'happy', 'joy', 'beautiful', 'amazing', 'wonderful', 'perfect', 
        'bright', 'smile', 'laugh', 'dream', 'hope', 'shine', 'magic', 'sweet'
    }
    
    negative_words = {
        'sad', 'cry', 'pain', 'hurt', 'broken', 'lonely', 'dark', 'tears', 
        'goodbye', 'lost', 'empty', 'cold', 'afraid', 'sorry', 'mad'
    }
    
    romantic_words = {
        'love', 'heart', 'kiss', 'romance', 'forever', 'together', 'soul', 
        'dear', 'honey', 'mine', 'yours', 'embrace', 'hold', 'close'
    }
    
    # Extract words using regex
    words = re.findall(r'\b\w+\b', lyrics_lower)
    word_count = len(words)
    unique_words = len(set(words))
    
    # Count emotional indicators
    positive_count = sum(1 for word in words if word in positive_words)
    negative_count = sum(1 for word in words if word in negative_words)
    romantic_count = sum(1 for word in words if word in romantic_words)
    
    # Analyze structure
    lines = [line.strip() for line in lyrics.split('\n') if line.strip()]
    
    # Filter common words for frequency analysis
    common_words = {
        'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 
        'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 
        'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 
        'can', 'cant', 'dont', 'wont', 'im', 'youre', 'hes', 'shes', 'its', 'weve'
    }
    
    meaningful_words = [word for word in words if word not in common_words and len(word) > 2]
    most_frequent = Counter(meaningful_words).most_common(10)
    
    # Determine emotional tendency
    if positive_count > negative_count:
        emotional_tendency = "positive"
    elif negative_count > positive_count:
        emotional_tendency = "negative"
    else:
        emotional_tendency = "neutral"
    
    # Calculate metrics
    vocabulary_density = round(unique_words / word_count * 100, 2) if word_count > 0 else 0
    repetition_score = 1 - (unique_words / word_count) if word_count > 0 else 0
    
    return {
        "basic_stats": {
            "total_words": word_count,
            "unique_words": unique_words,
            "lines_count": len(lines),
            "vocabulary_density_percent": vocabulary_density,
            "repetition_score": round(repetition_score, 3)
        },
        "emotional_analysis": {
            "positive_words_count": positive_count,
            "negative_words_count": negative_count,
            "romantic_words_count": romantic_count,
            "emotional_tendency": emotional_tendency,
            "emotional_intensity": positive_count + negative_count + romantic_count
        },
        "top_words": most_frequent[:5],
        "song_characteristics": {
            "is_romantic": romantic_count >= 3,
            "is_melancholic": negative_count > positive_count and negative_count >= 2,
            "is_upbeat": positive_count > negative_count and positive_count >= 3,
            "is_repetitive": repetition_score > 0.6,
            "is_complex_vocabulary": vocabulary_density > 70
        }
    }


def format_analysis_summary(song_title: str, analysis: Dict[str, Any]) -> str:
    """
    Format the analysis results into a readable summary
    
    Args:
        song_title: Name of the analyzed song
        analysis: Analysis results dictionary
        
    Returns:
        Formatted summary string
    """
    if "error" in analysis:
        return f"❌ Analysis failed for '{song_title}': {analysis['error']}"
    
    stats = analysis["basic_stats"]
    emotions = analysis["emotional_analysis"]
    characteristics = analysis["song_characteristics"]
    top_words = analysis["top_words"]
    
    # Build characteristics list
    char_list = []
    if characteristics["is_romantic"]:
        char_list.append("Romantic")
    if characteristics["is_melancholic"]:
        char_list.append("Melancholic")
    if characteristics["is_upbeat"]:
        char_list.append("Upbeat")
    if characteristics["is_repetitive"]:
        char_list.append("Repetitive")
    if characteristics["is_complex_vocabulary"]:
        char_list.append("Complex vocabulary")
    
    characteristics_str = ", ".join(char_list) if char_list else "Standard pop song structure"
    
    summary = f"""
🎵 TAYLOR SWIFT SONG ANALYSIS: '{song_title.upper()}'

📊 BASIC STATISTICS:
• Total words: {stats['total_words']}
• Unique words: {stats['unique_words']}
• Lines: {stats['lines_count']}
• Vocabulary density: {stats['vocabulary_density_percent']}%

💭 EMOTIONAL PROFILE:
• Overall tendency: {emotions['emotional_tendency'].upper()}
• Positive indicators: {emotions['positive_words_count']}
• Negative indicators: {emotions['negative_words_count']}
• Romantic elements: {emotions['romantic_words_count']}
• Emotional intensity: {emotions['emotional_intensity']}

🎭 SONG CHARACTERISTICS:
• {characteristics_str}

🔤 MOST FREQUENT MEANINGFUL WORDS:"""
    
    for word, count in top_words:
        summary += f"\n• '{word}' appears {count} times"
    
    return summary.strip()


@mcp.tool()
async def get_song_lyrics(song_title: str) -> str:
    """
    Get the lyrics for a Taylor Swift song
    
    Args:
        song_title: Title of the Taylor Swift song
        
    Returns:
        The song lyrics or error message
    """
    songs_url = f"{SONGS_API_BASE}/{ARTIST}/{song_title}"
    logger.info(f"Fetching lyrics for song: {song_title}")

    response = await make_song_request(url=songs_url)

    if not response:
        return f"❌ Unable to fetch lyrics for '{song_title}'. Please check the song title spelling."

    lyrics = response.get("lyrics", "Lyrics not found.")
    
    if lyrics == "Lyrics not found.":
        return f"❌ Lyrics not found for '{song_title}'. The song might not be available in the database."
    
    # Return a brief preview instead of full lyrics to respect copyright
    lines = lyrics.split('\n')[:4]  # First 4 lines only
    preview = '\n'.join(lines)
    
    return f"✅ Lyrics found for '{song_title}'\n\nPreview (first few lines):\n{preview}\n\n[Full lyrics retrieved for analysis]"


@mcp.tool()
async def analyze_song(song_title: str) -> str:
    """
    Perform comprehensive analysis of a Taylor Swift song including lyrics sentiment, 
    statistics, and musical characteristics
    
    Args:
        song_title: Title of the Taylor Swift song to analyze
        
    Returns:
        Detailed analysis report
    """
    songs_url = f"{SONGS_API_BASE}/{ARTIST}/{song_title}"
    logger.info(f"Analyzing song: {song_title}")

    # Fetch lyrics
    response = await make_song_request(url=songs_url)

    if not response:
        return f"❌ Unable to fetch data for '{song_title}'. Please verify the song title."

    lyrics = response.get("lyrics", "")
    
    if not lyrics or lyrics == "Lyrics not found.":
        return f"❌ No lyrics available for analysis of '{song_title}'"
    
    # Perform analysis
    analysis = analyze_lyrics_content(lyrics)
    
    # Format and return results
    return format_analysis_summary(song_title, analysis)


@mcp.tool()
async def compare_songs(song1: str, song2: str) -> str:
    """
    Compare the emotional and structural characteristics of two Taylor Swift songs
    
    Args:
        song1: First song title
        song2: Second song title
        
    Returns:
        Comparative analysis report
    """
    logger.info(f"Comparing songs: '{song1}' vs '{song2}'")
    
    # Fetch lyrics for both songs
    url1 = f"{SONGS_API_BASE}/{ARTIST}/{song1}"
    url2 = f"{SONGS_API_BASE}/{ARTIST}/{song2}"
    
    response1 = await make_song_request(url1)
    response2 = await make_song_request(url2)
    
    if not response1:
        return f"❌ Could not fetch data for '{song1}'"
    if not response2:
        return f"❌ Could not fetch data for '{song2}'"
    
    lyrics1 = response1.get("lyrics", "")
    lyrics2 = response2.get("lyrics", "")
    
    if not lyrics1:
        return f"❌ No lyrics available for '{song1}'"
    if not lyrics2:
        return f"❌ No lyrics available for '{song2}'"
    
    # Analyze both songs
    analysis1 = analyze_lyrics_content(lyrics1)
    analysis2 = analyze_lyrics_content(lyrics2)
    
    if "error" in analysis1:
        return f"❌ Analysis failed for '{song1}'"
    if "error" in analysis2:
        return f"❌ Analysis failed for '{song2}'"
    
    # Generate comparison
    stats1 = analysis1["basic_stats"]
    stats2 = analysis2["basic_stats"]
    emotions1 = analysis1["emotional_analysis"]
    emotions2 = analysis2["emotional_analysis"]
    chars1 = analysis1["song_characteristics"]
    chars2 = analysis2["song_characteristics"]
    
    comparison = f"""
🎵 SONG COMPARISON: '{song1.upper()}' vs '{song2.upper()}'

📊 STATISTICS COMPARISON:
• {song1}: {stats1['total_words']} words, {emotions1['emotional_tendency']} tendency
• {song2}: {stats2['total_words']} words, {emotions2['emotional_tendency']} tendency

💭 EMOTIONAL ANALYSIS:
• {song1}: {emotions1['positive_words_count']} positive, {emotions1['negative_words_count']} negative, {emotions1['romantic_words_count']} romantic
• {song2}: {emotions2['positive_words_count']} positive, {emotions2['negative_words_count']} negative, {emotions2['romantic_words_count']} romantic

🎭 CHARACTERISTICS:
• {song1}: {'Romantic' if chars1['is_romantic'] else 'Non-romantic'}, {'Melancholic' if chars1['is_melancholic'] else 'Non-melancholic'}, {'Upbeat' if chars1['is_upbeat'] else 'Not upbeat'}
• {song2}: {'Romantic' if chars2['is_romantic'] else 'Non-romantic'}, {'Melancholic' if chars2['is_melancholic'] else 'Non-melancholic'}, {'Upbeat' if chars2['is_upbeat'] else 'Not upbeat'}

🏆 COMPARISON WINNERS:
• More positive: {song1 if emotions1['positive_words_count'] > emotions2['positive_words_count'] else song2 if emotions2['positive_words_count'] > emotions1['positive_words_count'] else 'Tie'}
• More romantic: {song1 if emotions1['romantic_words_count'] > emotions2['romantic_words_count'] else song2 if emotions2['romantic_words_count'] > emotions1['romantic_words_count'] else 'Tie'}
• More complex vocabulary: {song1 if stats1['vocabulary_density_percent'] > stats2['vocabulary_density_percent'] else song2}
• Longer: {song1 if stats1['total_words'] > stats2['total_words'] else song2}

🎯 SUMMARY:
Both songs showcase Taylor Swift's songwriting evolution with distinct emotional profiles and structural approaches.
"""
    
    return comparison.strip()


@mcp.tool()
async def get_song_stats_only(song_title: str) -> str:
    """
    Get only the basic statistics for a Taylor Swift song without full analysis
    
    Args:
        song_title: Title of the Taylor Swift song
        
    Returns:
        Basic statistics summary
    """
    songs_url = f"{SONGS_API_BASE}/{ARTIST}/{song_title}"
    logger.info(f"Getting stats for song: {song_title}")

    response = await make_song_request(url=songs_url)

    if not response:
        return f"❌ Unable to fetch data for '{song_title}'"

    lyrics = response.get("lyrics", "")
    
    if not lyrics:
        return f"❌ No lyrics available for '{song_title}'"
    
    analysis = analyze_lyrics_content(lyrics)
    
    if "error" in analysis:
        return f"❌ Analysis failed: {analysis['error']}"
    
    stats = analysis["basic_stats"]
    emotions = analysis["emotional_analysis"]
    
    return f"""
📊 QUICK STATS for '{song_title.upper()}':
• Words: {stats['total_words']} total, {stats['unique_words']} unique
• Lines: {stats['lines_count']}
• Vocabulary density: {stats['vocabulary_density_percent']}%
• Emotional tendency: {emotions['emotional_tendency']}
• Emotional intensity: {emotions['emotional_intensity']}
"""


if __name__ == "__main__":
    logger.info("Starting Taylor Swift MCP Analysis Server...")
    # Initialize and run the server
    mcp.run(transport='stdio')