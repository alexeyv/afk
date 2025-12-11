#!/usr/bin/env python3
import sys
import time

print("Starting slow task...")
sys.stdout.flush()
for i in range(10):
    print(f"Working... {i}")
    sys.stdout.flush()
    time.sleep(0.5)
print("Done.")
sys.exit(0)
