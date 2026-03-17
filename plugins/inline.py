# सबसे ऊपर imports में ये line add करो
from database.fuzzy_db import get_fuzzy_suggestions

# और answer function ke end mein "No results" वाला part ऐसे बदलो:
else:
    # Fuzzy suggestions लो
    suggestions = await get_fuzzy_suggestions(string, limit=5, score_cutoff=50)
    
    if suggestions:
        # Suggestions मिलीं
        suggestion_text = f"❌ No exact results for '{string}'\n\n"
        suggestion_text += "🔎 Did you mean one of these?\n\n"
        
        for sug in suggestions:
            suggestion_text += f"• {sug['display']}\n"
        
        await query.answer(results=[],
                          is_personal=True,
                          cache_time=0,
                          switch_pm_text=suggestion_text[:50] + "...",
                          switch_pm_parameter="fuzzy")
    else:
        # No suggestions
        switch_pm_text = f'❌ No results'
        if string:
            switch_pm_text += f' for "{string}"'

        await query.answer(results=[],
                          is_personal=True,
                          cache_time=cache_time,
                          switch_pm_text=switch_pm_text,
                          switch_pm_parameter="okay")