# Git Commands Reference – MiniMart Kubernetes Project

A complete log of all Git commands used in this project, in order of use.
Use this as a quick cheatsheet for your own projects.

---

## 🔧 Initial Setup & Status

```bash
# Check what files have changed and their current state
git status

# See all remotes (fetch + push URLs)
git remote -v

# See which branch you are on
git branch

# See last N commits (one line each)
git log -n 3 --oneline

# See commits that are local but NOT yet pushed to remote
git log origin/main..HEAD --oneline
```

---

## 🔗 Remote Configuration

```bash
# Set (or change) the remote origin URL
git remote set-url origin https://github.com/<username>/<repo>.git

# Set origin URL with username embedded (avoids credential prompt)
git remote set-url origin https://<username>@github.com/<username>/<repo>.git
```

---

## 📤 Pushing to GitHub

```bash
# Push current branch to origin and set it as upstream (-u flag)
git push -u origin main

# Push using a Personal Access Token (PAT) inline – secure, no stored creds
git push https://<username>:<PAT>@github.com/<username>/<repo>.git main

# Set the local branch to track origin/main (after pushing with PAT)
git update-ref refs/remotes/origin/main HEAD
git branch --set-upstream-to=origin/main main
```

---

## 📦 Staging & Committing

```bash
# Stage specific files
git add backend/app.py backend/Dockerfile k8s/backend-deployment.yaml

# Stage all changed files in the repo
git add .

# Commit with a message (follow Conventional Commits format: feat/fix/docs/chore)
git commit -m "feat: add SQLite database to backend (emptyDir volume)"

# One-liner: stage all + commit
git add . && git commit -m "your message here"
```

---

## 🔍 Inspecting the Repo

```bash
# Check local git config (name, email, remotes, tracking branches)
git config --list

# Check only local repo config (excludes global)
git config --local -l

# List credentials stored in Windows Credential Manager
cmdkey /list | Select-String "git:"
```

---

## 🛡️ Security Note – Personal Access Token

When you push using a PAT inline, Git Credential Manager may store the PAT
in the tracking branch config. Always check and clean it after:

```bash
# After pushing with PAT, make sure the token isn't saved in .git/config
git config --local -l | grep "https://"

# Fix: reset the tracking branch to point to "origin" instead of the token URL
git config branch.main.remote origin
```

---

## 📋 Conventional Commit Format Used in This Project

| Prefix | Meaning | Example |
|--------|---------|---------|
| `feat:` | New feature | `feat: add SQLite database` |
| `fix:` | Bug fix | `fix: proxy not forwarding POST requests` |
| `chore:` | Maintenance | `chore: update .gitignore` |
| `docs:` | Documentation | `docs: add git commands reference` |
| `refactor:` | Code restructure | `refactor: replace in-memory PRODUCTS list with DB` |

---

## 📌 Full Command History (Chronological)

```bash
# 1. Checked status before first push
git status
git remote -v
git branch

# 2. Checked unpushed commits
git log -n 3 --oneline
git log origin/main..HEAD --oneline

# 3. First push attempt failed (403 – wrong GitHub account in Credential Manager)
git push -u origin main

# 4. Updated remote URL to include username
git remote set-url origin https://Chinmay077@github.com/Chinmay077/kubernetes_project.git

# 5. Pushed using PAT (Personal Access Token)
git push https://Chinmay077:<PAT>@github.com/Chinmay077/kubernetes_project.git main:main -u

# 6. Cleaned up: PAT was saved in branch config → reset to "origin"
git config branch.main.remote origin

# 7. Fixed tracking reference
git update-ref refs/remotes/origin/main HEAD
git branch --set-upstream-to=origin/main main

# 8. Reset remote URL back to clean form (no embedded username)
git remote set-url origin https://github.com/Chinmay077/kubernetes_project.git

# 9. Committed and pushed SQLite feature
git add backend/app.py backend/Dockerfile k8s/backend-deployment.yaml
git commit -m "feat: add SQLite database to backend (emptyDir volume)"
git push https://Chinmay077:<PAT>@github.com/Chinmay077/kubernetes_project.git main

# 10. Committed and pushed async messaging + protocol comparison feature
git add .
git commit -m "feat: add notification service, async messaging, and protocol comparison experiments"
git push https://Chinmay077:<PAT>@github.com/Chinmay077/kubernetes_project.git main
```

---

## 🚀 Quick Reference Card

| Task | Command |
|------|---------|
| Stage all | `git add .` |
| Commit | `git commit -m "message"` |
| Push | `git push` |
| Check status | `git status` |
| See history | `git log --oneline` |
| Undo last commit (keep changes) | `git reset HEAD~1` |
| Discard all local changes | `git checkout .` |
| Create new branch | `git checkout -b branch-name` |
| Switch branch | `git checkout main` |
| Pull latest | `git pull origin main` |
