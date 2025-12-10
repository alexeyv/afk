#!/usr/bin/env python3
"""
Audio Summary Hook - Extracts and speaks audio summary messages
Triggered by Claude Code when "## Audio Summary" appears in output
"""

import json
import sys
import subprocess
import os
from pathlib import Path


def get_transcript_path():
  """Get transcript path from stdin JSON"""
  try:
    data = json.load(sys.stdin)
    return data.get('transcript_path', '')
  except:
    return ''


def extract_audio_message(transcript_path):
  """Extract audio message from the last assistant response"""
  try:
    # Use tail to get only the last 20 lines instead of reading entire file
    result = subprocess.run(['tail', '-n', '20', transcript_path],
                            capture_output=True, text=True, timeout=5)
    if result.returncode != 0:
      return ''

    lines = result.stdout.strip().split('\n')

    # Find last assistant message
    for line in reversed(lines):
      try:
        entry = json.loads(line.strip())
        if (entry.get('type') == 'assistant' and
            entry.get('message', {}).get('content')):

          # Get text content
          for item in entry['message']['content']:
            if item.get('type') == 'text':
              text = item['text']

              # Extract audio summary
              if '## Audio Summary' in text:
                text_lines = text.split('\n')
                in_audio = False
                for text_line in text_lines:
                  if text_line.strip() == '## Audio Summary':
                    in_audio = True
                    continue
                  if in_audio and text_line.strip() and not text_line.startswith('#'):
                    return text_line.strip()
              return ''
      except:
        continue
  except:
    pass
  return ''


def get_username():
  """Get username from .env file with fallback"""
  try:
    # Look for .env in project directory or hook directory
    env_paths = []
    if 'CLAUDE_PROJECT_DIR' in os.environ:
      env_paths.append(Path(os.environ['CLAUDE_PROJECT_DIR']) / '.claude' / '.env')

    hook_dir = Path(__file__).parent.parent
    env_paths.append(hook_dir / '.env')

    for env_path in env_paths:
      if env_path.exists():
        with open(env_path, 'r') as f:
          for line in f:
            line = line.strip()
            if line.startswith('USER_NAME='):
              return line.split('=', 1)[1]
    return 'there'
  except:
    return 'there'


def speak_message(message):
  """Speak the message using macOS say in background"""
  if not message:
    return

  # Username substitution
  username = get_username()
  processed_message = message.replace('[Username]', username)

  # Use macOS say in background (non-blocking)
  subprocess.Popen(['say', processed_message],
                   stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL)


def main():
  transcript_path = get_transcript_path()
  if not transcript_path or not os.path.exists(transcript_path):
    return

  audio_message = extract_audio_message(transcript_path)
  speak_message(audio_message)


if __name__ == '__main__':
  main()