#!/usr/bin/env python3
import requests
import json

API_URL = "http://192.168.10.7:8082/api/events"

events_to_update = [
    {"id": 12, "title": "数学作业", "importance": "important", "urgency": "urgent"},
    {"id": 13, "title": "科学课", "importance": "important", "urgency": "not_urgent"},
    {"id": 14, "title": "火花课程", "importance": "not_important", "urgency": "urgent"},
    {"id": 15, "title": "每日运动15分钟", "importance": "not_important", "urgency": "not_urgent"},
]

print("Updating events classification...")
print("-" * 50)

for event in events_to_update:
    event_id = event["id"]
    payload = {
        "importance": event["importance"],
        "urgency": event["urgency"]
    }
    
    try:
        response = requests.put(f"{API_URL}/{event_id}", json=payload)
        if response.status_code == 200:
            updated = response.json()
            print(f"✓ ID {event_id}: {event['title']}")
            print(f"  → {event['importance']} + {event['urgency']}")
        else:
            print(f"✗ ID {event_id}: Error {response.status_code}")
            print(f"  Response: {response.text}")
    except Exception as e:
        print(f"✗ ID {event_id}: Exception - {e}")

print("-" * 50)
print("Done!")

print("\nVerifying current events...")
response = requests.get(API_URL)
events = response.json()
print("\n分类结果:")
for e in events:
    quad = "重要紧急" if e["importance"]=="important" and e["urgency"]=="urgent" else \
           "重要不紧急" if e["importance"]=="important" and e["urgency"]=="not_urgent" else \
           "紧急不重要" if e["importance"]=="not_important" and e["urgency"]=="urgent" else \
           "不紧急不重要"
    print(f"  [{quad}] {e['title']}")