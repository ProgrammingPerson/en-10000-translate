import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from deep_translator import GoogleTranslator

language_codes = {
    'es': 'Spanish',
    'fr': 'French',
    'ar': 'Arabic',
    'el': 'Greek',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian',
    'zh': 'Chinese',
    'ja': 'Japanese',
    'id': 'Indonesian',
    'hi': 'Hindi',
    'bn': 'Bengali'
}

# Language code mapping for GoogleTranslator (use full names supported by Google Translate)
LANG_CODES = {
    'es': 'spanish',
    'fr': 'french',
    'ar': 'arabic',
    'el': 'greek',
    'de': 'german',
    'it': 'italian',
    'pt': 'portuguese',
    'ru': 'russian',
    'zh': 'chinese (simplified)',  # Use full name for Google Translate
    'ja': 'japanese',
    'id': 'indonesian',
    'hi': 'hindi',
    'bn': 'bengali'
}

CACHE_FILE = "translation_cache.json"
LOG_INTERVAL = 50  # Save progress every 50 words
PROGRESS_FILE = "translation_progress.txt"
cache_lock = Lock()
rate_limit_lock = Lock()
last_request_time = 0.0

# Load cache from disk
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

# Save cache to disk (thread-safe)
def save_cache(cache):
    with cache_lock:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(dict(cache), f, ensure_ascii=False, indent=2)

def rate_limit(delay=0.1):
    """Enforce minimum delay between API requests."""
    global last_request_time
    with rate_limit_lock:
        elapsed = time.time() - last_request_time
        if elapsed < delay:
            time.sleep(delay - elapsed)
        last_request_time = time.time()

# Load or initialize cache
translation_cache = load_cache()
translation_count = 0

def translate_word(word, lang_code):
    """Translate word using GoogleTranslator with rate limiting."""
    global translation_count
    
    # Check cache first
    cache_key = f"{word}_{lang_code}"
    if cache_key in translation_cache:
        return translation_cache[cache_key]
    
    # Rate limit
    rate_limit(0.1)
    
    # Translate using GoogleTranslator
    try:
        translator = GoogleTranslator(source='en', target=LANG_CODES[lang_code])
        result = translator.translate(word)
        translation_count += 1
    except Exception as e:
        print(f"Error translating '{word}' to {lang_code}: {e}")
        result = word  # Fallback to original word
    
    with cache_lock:
        translation_cache[cache_key] = result
    return result

def translate_all_languages(word, word_index):
    """Translate a word to all languages and return ordered row."""
    row = [word]
    results = {}
    
    # Translate sequentially through languages (but multiple words in parallel)
    for lang in language_codes.keys():
        results[lang] = translate_word(word, lang)
    
    # Append in language order
    for lang in language_codes.keys():
        row.append(results[lang])
    
    # Log progress and save cache periodically
    if (word_index + 1) % LOG_INTERVAL == 0:
        elapsed = time.time() - start_time
        rate = (word_index + 1) / elapsed
        remaining = (len(words) - word_index - 1) / rate if rate > 0 else 0
        progress_msg = f"Progress: {word_index + 1:,}/{len(words):,} words | {translation_count:,} translated | ETA: {int(remaining/60)}m {int(remaining%60)}s"
        print(progress_msg)
        save_cache(translation_cache)
        # Save progress to file for reference
        with open(PROGRESS_FILE, "w") as f:
            f.write(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Words processed: {word_index + 1:,}/{len(words):,}\n")
            f.write(f"Total translations: {translation_count:,}\n")
            f.write(f"Elapsed time: {int(elapsed/60)}m {int(elapsed%60)}s\n")
            f.write(f"Estimated remaining: {int(remaining/60)}m {int(remaining%60)}s\n")
    
    return row

with open("google-10000-english.txt", "r", encoding="utf-8") as f:
    words = f.read().splitlines()

start_time = time.time()

print(f"Starting translation of {len(words):,} words...")
cached_count = len(translation_cache)
if cached_count > 0:
    print(f"*** RESUMING FROM PREVIOUS SESSION ***")
    print(f"Cache loaded with {cached_count:,} existing translations")
    print(f"Remaining words to translate: {len(words) * 13 - cached_count:,}\n")
else:
    print(f"Cache is empty, starting fresh")
    
print(f"Using Google Translate API with parallel processing (~5 words at a time)")
print(f"Rate limit: 0.1s between requests\n")
print("This will take approximately 5-8 hours to complete")
print(f"Progress is saved to cache every 50 words\n")
print("Progress will update every 50 words...\n")

with open("words.csv", "w", encoding="utf-8") as output:
    # Process multiple words in parallel
    with ThreadPoolExecutor(max_workers=5) as word_executor:
        futures = {word_executor.submit(translate_all_languages, word, i): word for i, word in enumerate(words)}
        for future in as_completed(futures):
            row = future.result()
            output.write(",".join(row) + "\n")

# Final save
save_cache(translation_cache)
elapsed = time.time() - start_time
print(f"\nDone! Total translations: {translation_count:,}/130,000")
print(f"Time taken: {int(elapsed/60)}m {int(elapsed%60)}s")
print(f"Cache saved to {CACHE_FILE} with {len(translation_cache):,} translations")