#!/usr/bin/env python3
import calendar_renderer

print("Fetching events...")
events = calendar_renderer.fetch_events()
print(f"Fetched {len(events)} events")

print("Rendering frame...")
calendar_renderer.render_frame('home', '2026-05-23', events, '/tmp/test.png')
print("Rendered successfully")
