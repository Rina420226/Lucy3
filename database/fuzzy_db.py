from rapidfuzz import process, fuzz
from .ia_filterdb import Media, Media2
import logging

logger = logging.getLogger(__name__)

async def get_all_file_names(limit: int = 10000):
    """
    डेटाबेस से सभी फाइल नाम लाकर लौटाता है
    Fuzzy Search Suggestions के लिए उपयोगी
    """
    try:
        # Media collection से file_names लो
        cursor1 = Media.find({}, {"file_name": 1, "_id": 0})
        docs1 = await cursor1.to_list(length=limit)
        
        # Media2 collection से file_names लो
        cursor2 = Media2.find({}, {"file_name": 1, "_id": 0})
        docs2 = await cursor2.to_list(length=limit)
        
        # दोनों collections से file_names निकालो
        file_names1 = [doc["file_name"] for doc in docs1 if doc.get("file_name")]
        file_names2 = [doc["file_name"] for doc in docs2 if doc.get("file_name")]
        
        # दोनों lists को जोड़ो
        all_file_names = file_names1 + file_names2
        
        logger.info(f"✅ {len(all_file_names)} file names loaded for fuzzy search")
        return all_file_names
        
    except Exception as e:
        logger.error(f"❌ Error in get_all_file_names: {e}")
        return []

async def get_fuzzy_suggestions(search_query: str, limit: int = 5, score_cutoff: int = 50):
    """
    सीधे Fuzzy Suggestions लौटाता है
    """
    try:
        # सारे file names लाओ
        all_names = await get_all_file_names()
        
        if not all_names:
            return []
        
        # RapidFuzz से suggestions निकालो
        suggestions = process.extract(
            search_query,
            all_names,
            scorer=fuzz.token_sort_ratio,
            limit=limit,
            score_cutoff=score_cutoff
        )
        
        # Results को format में बदलो
        result = []
        for match_string, score, index in suggestions:
            result.append({
                'name': match_string,
                'score': score,
                'display': f"{match_string} ({score}% match)"
            })
        
        logger.info(f"🔍 Found {len(result)} fuzzy suggestions for '{search_query}'")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in get_fuzzy_suggestions: {e}")
        return []