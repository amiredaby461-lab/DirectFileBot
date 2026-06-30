# Workflow notes

This repository is designed to run on GitHub Actions only.

- The scheduled workflow polls Telegram updates.
- The workflow persists state in JSON files inside the repository.
- User files are stored only in `temp/` during the run and are deleted afterward.
- No artifacts are used for user files.
