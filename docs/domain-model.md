# Domain Model - afk

**Date:** 2025-12-09

This document captures the core domain entities and design decisions for afk, to inform architecture.

## Entities

- **Machine** - set of transitions, rules for which one fires given a revision
- **Transition** - prompt, conditions (when to fire based on revision)
- **Session** - sequence of turns
- **Turn** - sequential number, transition type, commit hash, log file
- **Revision** - repo at a specific commit; this is the state
- **Prompt** - content, location
- **Commit** - hash, message (universal schema), changes

## Key Design Decisions

- **Revision is the state.** No separate state tracking. The repo at a specific commit is the complete state of the system.
- **Commit message is structured data.** Universal schema across all transitions. Machine reads commit message to determine next transition.
- **Changes are just git diff.** Framework doesn't need to understand what changed - code, docs, images, deletions, renames. Git tracks it.
- **Transition-specific data goes in documents.** Committed alongside code changes, not in the message.
- **One turn, one commit.** The commit is the result. No commit = turn failed.

## Relationships

- A Machine defines which Transitions exist and when each fires
- A Session is a sequence of Turns
- A Turn executes one Transition and produces one Commit
- A Transition uses one Prompt
- A Revision is a Commit - the repo at that point
- The current Revision determines which Transition fires next
