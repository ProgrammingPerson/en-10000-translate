import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from deep_translator import GoogleTranslator

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

# Save cache to disk (thread-safe, durable)
def save_cache(cache):
    """
    Persist the cache safely.
    We write to a temp file first and then replace to avoid corrupting the cache
    if the process is interrupted while writing.
    """
    with cache_lock:
        tmp_file = CACHE_FILE + ".tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(dict(cache), f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, CACHE_FILE)

def rate_limit(delay=0.1):
    """Enforce minimum delay between API requests."""
    global last_request_time
    with rate_limit_lock:
        elapsed = time.time() - last_request_time
        if elapsed < delay:
            time.sleep(delay - elapsed)
        last_request_time = time.time()

def init_state():
    """
    Initialize mutable global state.
    Kept in a helper so that importing this module for utilities doesn't
    immediately do file I/O or reset counters.
    """
    global translation_cache, translation_count, start_time, words
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
    for lang in LANG_CODES.keys():
        results[lang] = translate_word(word, lang)
    
    # Append in language order
    for lang in LANG_CODES.keys():
        row.append(results[lang])
    
    # Log progress and save cache periodically
    if (word_index + 1) % LOG_INTERVAL == 0:
        elapsed = time.time() - start_time
        rate = (word_index + 1) / elapsed if elapsed > 0 else 0
        total = len(words)
        remaining = (total - word_index - 1) / rate if rate > 0 else 0
        progress_msg = (
            f"Progress: {word_index + 1:,}/{total:,} words | "
            f"{translation_count:,} translated | "
            f"ETA: {int(remaining/60)}m {int(remaining%60)}s"
        )
        print(progress_msg, flush=True)
        save_cache(translation_cache)
    
    return row

if __name__ == "__main__":
    init_state()

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

    with open("words.csv", "w", encoding="utf-8", newline="") as output:
        # Process multiple words in parallel
        with ThreadPoolExecutor(max_workers=5) as word_executor:
            futures = {word_executor.submit(translate_all_languages, word, i): word for i, word in enumerate(words)}
            for future in as_completed(futures):
                row = future.result()
                output.write(",".join(row) + "\n")

    # Final save
    save_cache(translation_cache)
    elapsed = time.time() - start_time
    print(f"\nDone! Total translations: {translation_count:,}/{len(words) * len(LANG_CODES):,}")
    print(f"Time taken: {int(elapsed/60)}m {int(elapsed%60)}s")
    print(f"Cache saved to {CACHE_FILE} with {len(translation_cache):,} translations")