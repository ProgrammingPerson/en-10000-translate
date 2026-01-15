import csv

with open("phrase_translation.csv", "r", encoding='utf-8') as f:
    phrases = csv.DictReader(f)
    data = []
    i = 0
    for line in phrases:
        data.append(line)
        i += 1
        if i == 9999:
            break

    with open("phrases_mini.csv", "w", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=['text', 'language'])
        writer.writeheader()
        writer.writerows(data)

    output.close()