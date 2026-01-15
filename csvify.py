import json

LANG_CODES = {
    'es': 'spanish',
    'fr': 'french',
    'ar': 'arabic',
    'el': 'greek',
    'de': 'german',
    'it': 'italian',
    'pt': 'portuguese',
    'ru': 'russian',
    'zh': 'chinese',
    'ja': 'japanese',
    'id': 'indonesian',
    'hi': 'hindi',
    'bn': 'bengali'
}

with open("translation_cache.json", "r", encoding="utf-8") as f:
    translation_cache = json.load(f)

with open("full_words.csv", "w", encoding="utf-8") as output:
    for word_dest, translation in translation_cache.items():
        words = {}
        word, dest = tuple(word_dest.split("_"))
        if word not in words:
            words[word] = [word] + [0]*len(LANG_CODES)
        lang_name = LANG_CODES.get(dest, dest)
        words[word][list(LANG_CODES.values()).index(lang_name)+1] = translation
        
    for row in words.values():
        print(row)
        output.write(",".join(row) + "\n")

output.close()
            