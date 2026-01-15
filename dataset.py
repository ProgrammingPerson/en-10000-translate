from datasets import load_dataset
import csv

ds = load_dataset("MultivexAI/Everyday-Language-Corpus")
data = {}
for item in range(len(ds['train'])):
    data[item] = {}
    data[item]['text'] = ds['train'][item]['text'].replace(',', '').replace('[S]', '').replace('[E]', '').strip()
    data[item]['language'] = 'en'

fieldnames = data[0].keys()
with open("everyday_language_corpus.csv", "w", encoding="utf-8") as output:
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data.values())

output.close()