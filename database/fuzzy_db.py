import logging
from rapidfuzz import process, fuzz
from .ia_filterdb import Media, Media2

logger = logging.getLogger(__name__)

async def get_all_file_names(limit: int = 10000):
    """
    डेटाबेस से सभी फाइल नाम लाकर लौटाता है
    """
    try:
        # Count check
        count1 = await Media.count_documents({})
        count2 = await Media2.count_documents({})
        logger.info(f"📊 Total documents: Media={count1}, Media2={count2}")
        
        if count1 == 0 and count2 == 0:
            logger.warning("⚠️ No files in database!")
            return []
        
        # Media collection
        file_names = []
        
        if count1 > 0:
            cursor1 = Media.find({}, {"file_name": 1})
            docs1 = await cursor1.to_list(length=limit)
            for doc in docs1:
                if doc.get("file_name"):
                    file_names.append(doc["file_name"])
            logger.info(f"📁 Got {len(docs1)} from Media")
        
        # Media2 collection
        if count2 > 0:
            cursor2 = Media2.find({}, {"file_name": 1})
            docs2 = await cursor2.to_list(length=limit)
            for doc in docs2:
                if doc.get("file_name"):
                    file_names.append(doc["file_name"])
            logger.info(f"📁 Got {len(docs2)} from Media2")
        
        # Remove duplicates
        unique_names = list(set(file_names))
        
        logger.info(f"✅ Total unique file names: {len(unique_names)}")
        return unique_names
        
    except Exception as e:
        logger.error(f"❌ Error in get_all_file_names: {e}")
        return []

async def get_fuzzy_suggestions(search_query: str, limit: int = 5, score_cutoff: int = 50):
    """
    Fuzzy Suggestions with movie years
    """
    try:
        if not search_query or len(search_query) < 2:
            return []
        
        logger.info(f"🔍 Getting fuzzy suggestions for: '{search_query}'")
        
        # Get all file names
        all_names = await get_all_file_names()
        
        if not all_names:
            logger.warning("⚠️ No file names to search")
            return []
        
        # RapidFuzz suggestions
        suggestions = process.extract(
            search_query,
            all_names,
            scorer=fuzz.token_sort_ratio,
            limit=limit,
            score_cutoff=score_cutoff
        )
        
        # Format results with years
        result = []
        import re
        
        for match_string, score, index in suggestions:
            # Extract year if present (like 2009, 2022 etc)
            year_match = re.search(r'\b(19|20)\d{2}\b', match_string)
            year = f" ({year_match.group()})" if year_match else ""
            
            # Clean up name
            clean_name = match_string.replace('_', ' ').replace('.', ' ')
            
            result.append({
                'name': match_string,
                'display': f"{clean_name}{year}",
                'score': score
            })
            logger.info(f"  → {clean_name}{year} ({score}%)")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in get_fuzzy_suggestions: {e}")
        return []