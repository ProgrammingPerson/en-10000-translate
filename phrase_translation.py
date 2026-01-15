import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from deep_translator import GoogleTranslator

# Import cache functions and settings from translation module
from translation import (
    LANG_CODES,
    CACHE_FILE,
    LOG_INTERVAL,
    cache_lock,
    rate_limit_lock,
    last_request_time,
    load_cache,
    save_cache,
    rate_limit,
    init_state,
)

# Language code to name mapping (module-level constant for efficiency)
LANG_CODE_TO_NAME = {
    'es': 'Spanish', 'fr': 'French', 'ar': 'Arabic', 'el': 'Greek',
    'de': 'German', 'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian',
    'zh': 'Chinese', 'ja': 'Japanese', 'id': 'Indonesian', 'hi': 'Hindi', 'bn': 'Bengali'
}

# Pre-create translator instances for each language (reusable)
TRANSLATORS = {lang_code: GoogleTranslator(source='en', target=LANG_CODES[lang_code]) 
               for lang_code in LANG_CODES.keys()}

# Lock for CSV writing (thread-safe)
csv_write_lock = Lock()

# Initialize shared state
init_state()
# translation_cache and translation_count are created in translation.init_state
from translation import translation_cache, translation_count  # type: ignore

def translate_phrase(phrase, lang_code):
    """Translate phrase using GoogleTranslator with rate limiting."""
    global translation_count, translation_cache
    
    # Check cache first (read-only, no lock needed)
    cache_key = f"{phrase}_{lang_code}"
    if cache_key in translation_cache:
        return translation_cache[cache_key]
    
    # Rate limit
    rate_limit(0.1)
    
    # Translate using pre-created translator
    try:
        translator = TRANSLATORS[lang_code]
        result = translator.translate(phrase)
        
        # Thread-safe increment and cache update
        with cache_lock:
            translation_count += 1
            translation_cache[cache_key] = result
    except Exception as e:
        print(f"Error translating '{phrase[:50]}...' to {lang_code}: {e}", flush=True)
        result = phrase  # Fallback to original phrase
        # Cache the fallback to avoid retrying failed translations
        with cache_lock:
            translation_cache[cache_key] = result
    
    return result

def translate_all_languages(phrase, phrase_index, output_file, writer, total_phrases, start_time):
    """Translate a phrase to all languages and write to CSV incrementally."""
    phrase = phrase.strip()
    
    # Batch check cache for all languages upfront
    cache_keys = {lang_code: f"{phrase}_{lang_code}" for lang_code in LANG_CODES.keys()}
    cached_results = {}
    uncached_langs = []
    
    for lang_code, cache_key in cache_keys.items():
        if cache_key in translation_cache:
            cached_results[lang_code] = translation_cache[cache_key]
        else:
            uncached_langs.append(lang_code)
    
    # Build data array starting with English
    data = [{'text': phrase, 'language': 'English'}]
    
    # Translate only uncached languages
    for lang_code in LANG_CODES.keys():
        if lang_code in cached_results:
            translated = cached_results[lang_code]
        else:
            translated = translate_phrase(phrase, lang_code)
        
        lang_name = LANG_CODE_TO_NAME[lang_code]
        # Strip result (cached results should already be clean, but safe to strip again)
        data.append({'text': translated.strip(), 'language': lang_name})
    
    # Write to CSV immediately (thread-safe)
    with csv_write_lock:
        writer.writerows(data)
        output_file.flush()
    
    # Log progress and save cache periodically
    if (phrase_index + 1) % LOG_INTERVAL == 0:
        elapsed = time.time() - start_time
        if elapsed > 0:
            rate = (phrase_index + 1) / elapsed
            remaining = (total_phrases - phrase_index - 1) / rate
        else:
            remaining = 0
        progress_msg = (
            f"Progress: {phrase_index + 1:,}/{total_phrases:,} phrases | "
            f"{translation_count:,} translated | "
            f"ETA: {int(remaining/60)}m {int(remaining%60)}s"
        )
        print(progress_msg, flush=True)
        save_cache(translation_cache)
    
    return data

# Read phrases from input CSV
phrases = []
with open("everyday_language_corpus.csv", "r", encoding="utf-8") as data_file:
    reader = csv.DictReader(data_file)
    for row in reader:
        if row['language'] == 'en':  # Only process English phrases
            phrases.append(row['text'])

start_time = time.time()
total_phrases = len(phrases)
total_translations_needed = total_phrases * len(LANG_CODES)  # Excluding English

print(f"Starting translation of {total_phrases:,} phrases...")
cached_count = len(translation_cache)
if cached_count > 0:
    print(f"*** RESUMING FROM PREVIOUS SESSION ***")
    print(f"Cache loaded with {cached_count:,} existing translations")
    remaining = (total_phrases * (len(LANG_CODES) + 1)) - cached_count  # +1 for English
    print(f"Remaining translations: {remaining:,}\n")
else:
    print(f"Cache is empty, starting fresh")

print(f"Using Google Translate API with parallel processing (~5 phrases at a time)")
print(f"Rate limit: 0.1s between requests\n")
print(f"Progress is saved to cache every {LOG_INTERVAL} phrases\n")
print("Progress will update every 50 phrases...\n")

# Open output CSV file for writing
with open("phrase_translation.csv", "w", encoding="utf-8", newline='') as output:
    fieldnames = ['text', 'language']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    output.flush()
    
    # Process multiple phrases in parallel
    with ThreadPoolExecutor(max_workers=5) as phrase_executor:
        futures = {
            phrase_executor.submit(
                translate_all_languages, phrase, i, output, writer, total_phrases, start_time
            ): phrase 
            for i, phrase in enumerate(phrases)
        }
        for future in as_completed(futures):
            future.result()  # Results are already written to CSV

# Final save
save_cache(translation_cache)
elapsed = time.time() - start_time
print(f"\nDone! Total translations: {translation_count:,}/{total_translations_needed:,}")
print(f"Time taken: {int(elapsed/60)}m {int(elapsed%60)}s")
print(f"Cache saved to {CACHE_FILE} with {len(translation_cache):,} translations")
