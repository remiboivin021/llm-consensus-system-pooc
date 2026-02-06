# Git Workflow

This document describes the Git workflow for contributing to the llm-consensus-system project.

## Table of Contents

- [Overview](#overview)
- [Branch Structure](#branch-structure)
- [Fork Workflow](#fork-workflow)
- [Branch Naming Convention](#branch-naming-convention)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Keeping Your Fork Updated](#keeping-your-fork-updated)
- [Common Git Commands](#common-git-commands)

## Overview

We use a **fork-based workflow** with feature branches. This means:

1. Contributors fork the repository to their own GitHub account
2. Create feature/bug/hotfix branches on their fork
3. Submit Pull Requests from their fork to the `develop` branch of the organization repository
4. Maintainers review and merge into `develop`
5. Periodically, `develop` is merged into `main` for releases

## Branch Structure

### Main Branches

- **`main`**: Production-ready code. This branch should always be stable and deployable.
- **`develop`**: Integration branch for features. All Pull Requests should target this branch.

### Supporting Branches

Developers work on temporary branches on their forks:

- **`feat/*`**: New features
- **`bug/*`**: Bug fixes
- **`hotfix/*`**: Critical fixes that need to go directly to production

## Fork Workflow

### Step 1: Fork the Repository

1. Go to https://github.com/remiboivin021/llm-consensus-system
2. Click the "Fork" button in the top right
3. This creates a copy of the repository in your GitHub account

### Step 2: Clone Your Fork

```bash
# Clone your fork to your local machine
git clone https://github.com/YOUR_USERNAME/llm-consensus-system.git
cd llm-consensus-system
```

### Step 3: Add Upstream Remote

Add the original repository as a remote called "upstream":

```bash
git remote add upstream https://github.com/remiboivin021/llm-consensus-system.git
```

Verify your remotes:

```bash
git remote -v
origin    https://github.com/YOUR_USERNAME/llm-consensus-system.git (fetch)
origin    https://github.com/YOUR_USERNAME/llm-consensus-system.git (push)
upstream  https://github.com/remiboivin021/llm-consensus-system.git (fetch)upstream  https://github.com/remiboivin021/llm-consensus-system.git (push)
```

### Step 4: Create a Branch

Always create a new branch from `develop` for your work:

```bash
# Ensure you're on develop and it's up to date
git checkout develop
git pull upstream develop

# Create and switch to a new branch
git checkout -b feat/your-feature-name
```

### Step 5: Make Your Changes

Work on your feature, making commits as you go:

```bash
# Stage your changes
git add .

# Commit with a meaningful message
git commit -m "feat: add user authentication"
```

### Step 6: Push to Your Fork

```bash
git push origin feat/your-feature-name
```

### Step 7: Create a Pull Request

1. Go to your fork on GitHub
2. Click "Compare & pull request"
3. **Important**: Ensure the base repository is `remiboivin021/llm-consensus-system` and the base branch is `develop`
4. Fill in the PR description (see [Pull Request Process](#pull-request-process))
5. Submit the PR

## Branch Naming Convention

Use the following naming convention for your branches:

### Feature Branches

For new features or enhancements:

```
feat/<short-description>
```

**Examples:**
- `feat/user-authentication`
- `feat/dashboard-ui`
- `feat/api-rate-limiting`
- `feat/dark-mode`

### Bug Fix Branches

For bug fixes:

```
bug/<short-description>
```

**Examples:**
- `bug/login-validation`
- `bug/memory-leak`
- `bug/cors-issue`
- `bug/responsive-layout`

### Hotfix Branches

For critical fixes that need immediate attention:

```
hotfix/<short-description>
```

**Examples:**
- `hotfix/security-vulnerability`
- `hotfix/production-crash`
- `hotfix/data-loss`

### Branch Naming Rules

- Use lowercase letters
- Use hyphens to separate words
- Be descriptive but concise
- No spaces or special characters
- Maximum 50 characters

## Commit Guidelines

We use a structured commit message format that provides context and reasoning for changes.

### Commit Message Format

We support two commit message formats:
- **Short format** for day-to-day commits
- **Release format** for release commits (e.g., merge to `main` or version tags)

```
<type>(<scope>): <subject> [<code>]

WHY:
<explanation of why this change is needed>

WHAT:
- <list of changes>
- <another change>
- <more changes>

Web Impact:
<description of user-facing or application impact>

Failure Mode:
- <what to do if something goes wrong>
- <troubleshooting steps>
```

### Short Commit Message Format

Use this for regular work (features, fixes, docs, refactors). Keep it concise,
but still include WHY and WHAT:

```
<type>(<scope>): <subject> [<code>]

WHY:
<one sentence>

WHAT:
- <1-3 bullets>
```

### Release Commit Message Format

Use this format only for release commits (e.g., when merging to `main` or
creating a version tag). It captures broader impact and troubleshooting:

```
<type>(<scope>): <subject> [<code>]

WHY:
<explanation of why this change is needed>

WHAT:
- <list of changes>
- <another change>
- <more changes>

Web Impact:
<description of user-facing or application impact>

Failure Mode:
- <what to do if something goes wrong>
- <troubleshooting steps>
```

### Commit Types

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Code style changes (formatting, missing semicolons, etc.)
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **perf**: Performance improvements
- **test**: Adding or updating tests
- **chore**: Changes to build process, tools, or dependencies
- **ci**: Changes to CI/CD configuration

### Commit Code Reference

The `[<code>]` part is optional and can be used to reference:
- Work item codes (e.g., `[WRC1]`, `[WRC2]`)
- Ticket numbers (e.g., `[PROJ-123]`)
- Issue numbers (e.g., `[#42]`)

### Commit Message Examples

**Example 1: Documentation**

```bash
git commit -m "chore(docs): add baseline docs [WRC1]

WHY:
Provide the minimum docs to onboard contributors and define core policies.

WHAT:
- Added README.md, CONTRIBUTING.md, SECURITY.md, CODE_OF_CONDUCT.md
- Added GIT.md and DEV.md
- Added initial docs/ structure"
```

**Example 2: Feature**

```bash
git commit -m "feat(auth): implement JWT authentication [WRC5]

WHY:
Users need secure authentication to access protected resources and maintain sessions across the application.

WHAT:
- Added JWT token generation and validation
- Implemented login and logout endpoints
- Created authentication middleware for protected routes
- Added refresh token mechanism
- Configured token expiration times

Web Impact:
- Users can now securely log in and access their accounts
- Session management improves user experience
- Protected routes ensure data security

Failure Mode:
- If login fails, check user credentials and database connection
- If token validation fails, user will be redirected to login page
- If refresh token expired, user needs to log in again
- Check JWT_SECRET environment variable is properly set"
```

**Example 3: Bug Fix**

```bash
git commit -m "fix(api): resolve CORS issue [#42]

WHY:
Client application was unable to make API requests due to CORS policy blocking cross-origin requests from the frontend.

WHAT:
- Configured CORS middleware with proper origin settings
- Added allowed headers for authentication
- Enabled credentials in CORS configuration
- Updated environment variables for allowed origins

Web Impact:
- Frontend can now successfully communicate with the API
- Users will no longer see network errors
- All API endpoints are accessible from the client

Failure Mode:
- If CORS errors persist, verify ALLOWED_ORIGINS in .env
- Check that frontend URL matches the configured origin
- Ensure browser cache is cleared after update"
```

**Example 4: Test**

```bash
git commit -m "test(user): add unit tests for user service

WHY:
Ensure user service functions correctly and catch regressions before they reach production.

WHAT:
- Added unit tests for user creation
- Added tests for user validation logic
- Added tests for password hashing
- Added tests for user lookup functions
- Achieved 95% code coverage for user service

Web Impact:
- Improved code reliability and confidence in user management features
- Prevents regressions in user-related functionality

Failure Mode:
- If tests fail, review the specific test output
- Check that test database is properly configured
- Ensure test fixtures are up to date"
```

### Commit Rules

- **Subject line**: Use present tense and imperative mood (e.g., "add feature" not "added feature")
- **Subject line**: Don't capitalize the first letter
- **Subject line**: No period at the end
- **Subject line**: Keep under 72 characters
- **WHY section**: Explain the motivation and context for the change
- **WHAT section**: Use bullet points to list concrete changes
- **Web Impact**: Describe user-facing or application-level impact
- **Failure Mode**: Provide troubleshooting guidance
- **Blank lines**: Separate each section with a blank line
- **Line wrapping**: Wrap body text at 72 characters for readability

## Pull Request Process

### Before Creating a PR

1. **Ensure your code is up to date with `develop`:**

```bash
git fetch upstream
git checkout develop
git merge upstream/develop
git checkout feat/your-feature
git rebase develop
```

2. **Run tests:**

```bash
# In client directory
cd client && npm test

# In server directory
cd server && npm test
```

3. **Verify your changes:**

```bash
# Check what files changed
git diff develop

# Check commit history
git log develop..HEAD --oneline
```

### Creating the PR

1. Push your latest changes:

```bash
git push origin feat/your-feature-name
```

2. Go to GitHub and create a Pull Request
3. **Set base repository to**: `remiboivin021/llm-consensus-system`
4. **Set base branch to**: `develop`
5. Fill in the PR template:

### Review Process

1. **Automated Checks**: CI/CD will run automatically
2. **Code Review**: At least one maintainer must approve
3. **Address Feedback**: Make requested changes
4. **Final Approval**: Once approved, a maintainer will merge

### After Your PR is Merged

1. Delete your feature branch (GitHub will prompt you)
2. Update your local repository:

```bash
git checkout develop
git pull upstream develop
git push origin develop
```

## Keeping Your Fork Updated

### Sync Your Fork Regularly

```bash
# Fetch upstream changes
git fetch upstream

# Switch to develop
git checkout develop

# Merge upstream changes
git merge upstream/develop

# Push to your fork
git push origin develop
```

### Sync Your Feature Branch

If `develop` has moved forward while you're working:

```bash
# Fetch latest changes
git fetch upstream

# Switch to your feature branch
git checkout feat/your-feature

# Rebase on top of develop
git rebase upstream/develop

# If conflicts, resolve them and continue
git add .
git rebase --continue

# Force push to your fork (use with caution)
git push origin feat/your-feature --force
```

## Common Git Commands

### Viewing Changes

```bash
# View status
git status

# View changes
git diff

# View staged changes
git diff --staged

# View commit history
git log --oneline --graph

# View changes in a specific file
git log -p filename
```

### Undoing Changes

```bash
# Discard changes in working directory
git checkout -- filename

# Unstage a file
git reset HEAD filename

# Amend last commit
git commit --amend

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1
```

### Stashing

```bash
# Save changes temporarily
git stash

# List stashes
git stash list

# Apply last stash
git stash pop

# Apply specific stash
git stash apply stash@{0}
```

### Branching

```bash
# List branches
git branch

# List all branches (including remote)
git branch -a

# Create new branch
git branch feat/new-feature

# Switch to branch
git checkout feat/new-feature

# Create and switch in one command
git checkout -b feat/new-feature

# Delete branch
git branch -d feat/old-feature

# Delete remote branch
git push origin --delete feat/old-feature
```

### Remote Operations

```bash
# List remotes
git remote -v

# Add remote
git remote add upstream <url>

# Remove remote
git remote remove upstream

# Fetch from remote
git fetch upstream

# Pull from remote
git pull upstream develop

# Push to remote
git push origin feat/new-feature
```

## Hotfix Workflow

For critical bugs in production:

1. **Create hotfix branch from `main`:**

```bash
git checkout main
git pull upstream main
git checkout -b hotfix/critical-bug
```

2. **Fix the bug and commit:**

```bash
git add .
git commit -m "hotfix: fix critical security vulnerability"
```

3. **Push and create PR to `main`:**

```bash
git push origin hotfix/critical-bug
# Create PR to main (not develop)
```

4. **After merge, the maintainers will:**
   - Merge `main` back into `develop`
   - Deploy the fix
   - Tag a new release

## Best Practices

### Do's ✅

- Keep commits small and focused
- Write clear commit messages
- Sync your fork regularly
- Test before pushing
- Rebase instead of merge for cleaner history
- Delete branches after they're merged
- Communicate with maintainers

### Don'ts ❌

- Don't commit directly to `main` or `develop`
- Don't force push to shared branches
- Don't include unrelated changes in a PR
- Don't commit secrets or credentials
- Don't use generic commit messages ("fix", "update", etc.)
- Don't merge `develop` into your feature branch (use rebase)
- Don't create PRs with merge conflicts

## Troubleshooting

### Merge Conflicts

If you encounter merge conflicts during rebase:

```bash
# 1. View conflicted files
git status

# 2. Open and resolve conflicts in your editor
# Look for conflict markers: <<<<<<<, =======, >>>>>>>

# 3. Stage resolved files
git add filename

# 4. Continue rebase
git rebase --continue

# 5. If you want to abort
git rebase --abort
```

### Accidentally Committed to Wrong Branch

```bash
# Move commit to a new branch
git branch feat/new-feature
git reset --hard HEAD~1
git checkout feat/new-feature
```

### Need to Change Last Commit Message

```bash
# Amend the commit message
git commit --amend -m "new commit message"

# If already pushed (use with caution)
git push origin feat/branch-name --force
```

## Questions?

If you have questions about the Git workflow:

- Check the [Contributing Guide](CONTRIBUTING.md)
- Check the [Development Guide](DEV.md)
- Open an issue for discussion
- Contact the maintainers

Happy contributing! 🚀
