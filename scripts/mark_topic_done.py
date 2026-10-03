import csv
import os
import shutil
from datetime import datetime, timezone

TOPICS_FILE = "topics.csv"
TOPIC_FILE = "output/topic.txt"

if not os.path.exists(TOPICS_FILE):
    raise RuntimeError("topics.csv tidak ditemukan.")

if not os.path.exists(TOPIC_FILE):
    raise RuntimeError("output/topic.txt tidak ditemukan.")

topic = open(TOPIC_FILE, "r", encoding="utf-8").read().strip()

if not topic:
    raise RuntimeError("Topic kosong.")

# Backup sebelum mengubah database
backup_file = "topics.csv.backup"

shutil.copy2(TOPICS_FILE, backup_file)

rows = []
found = False

with open(TOPICS_FILE, "r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:
        if (
            not found
            and row["topic"].strip() == topic
            and row["status"].strip().upper() == "READY"
        ):
            row["status"] = "DONE"

            # Tambahkan waktu selesai jika kolom tersedia
            if "completed_at" in row:
                row["completed_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

            found = True

        rows.append(row)

if not found:
    raise RuntimeError(
        f"Topic READY tidak ditemukan untuk ditandai DONE: {topic}"
    )

fieldnames = rows[0].keys()

with open(TOPICS_FILE, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print("======================================")
print("TOPIC BERHASIL DITANDAI DONE")
print("======================================")
print(f"Topic: {topic}")
print("Status: DONE")
print("======================================")
