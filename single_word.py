import csv

languages = ["English","Spanish","French","Arabic","Greek","German","Italian","Portuguese","Russian","Chinese","Japanese","Indonesian","Hindi","Bengali"]

with open("words.csv", "r", encoding="utf-8") as file:
    words = file.readlines()

single_words = []

for word in words:
    if "English" in word:
        continue
    if len(single_words) >= 9999:
        break
    parts = word.split(",")
    for i in range(1, len(parts)):
        if len(single_words) >= 9999:
            break
        single_words.append({'text':parts[i].strip(), 'language':languages[i]})

with open ("single_words.csv", "w", encoding="utf-8") as output:
    fieldnames = ['text', 'language']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(single_words)

output.close()