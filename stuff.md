Kiro

read the prd.md document and start to work from it. ask questions if aspects of the document are not clearly formulated.

I've updated the prd.md, it should now answer your questions.
---

Cursor & claude code (Opus-4.5)

Work with me on a spec-driven approach. read the prd.md document and start to work from it. ask questions if aspects of the document are not clearly formulated.


now that I've merged all upstream changes, verify that a) all the requirements are met and that everysing that was specified is implemented. if tests are missing add them. make sure that all tests till pass after the merge.

---

Read the issues in the repo, that are open and have the label "enhancement". For each found, create a simple requirements, design and task document on how to implement the issue. Before you start implementing anything, create a local feature branch in git. Once you are done with the implementation, create a pull request and link it to the issue for manual review.


Add all new files to git and commit them with a meaningfull but not to overly verbose commit message. Do not push the commit.

--

I can see you have GitHub MCP tools available. Let me check what operations are possible by examining the available GitHub functions and understanding the scope of your Personal Access Token (PAT).

Based on the GitHub MCP tools I have access to, here are the operations I can perform:

## Repository Operations
- **Search repositories** - Find repos by query
- **Create repository** - Create new repos in your account
- **Fork repository** - Fork repos to your account or organization
- **Get file contents** - Read files/directories from repos
- **Create/update files** - Modify single files with commits
- **Push multiple files** - Batch commit multiple files at once

## Branch Operations
- **Create branch** - Create new branches from existing ones
- **List commits** - View commit history for branches

## Issue Operations
- **Search issues** - Find issues across GitHub
- **List issues** - Get issues from a specific repo
- **Get issue details** - View specific issue information
- **Create issue** - Open new issues
- **Update issue** - Modify existing issues (title, body, state, labels, assignees)
- **Add issue comment** - Comment on issues

## Pull Request Operations
- **Search PRs** - Find pull requests across GitHub
- **List PRs** - Get PRs from a specific repo with filters
- **Get PR details** - View specific PR information
- **Create PR** - Open new pull requests
- **Get PR files** - See changed files in a PR
- **Get PR status** - Check CI/CD status
- **Get PR comments** - View review comments
- **Get PR reviews** - View submitted reviews
- **Create PR review** - Submit reviews (approve/request changes/comment)
- **Merge PR** - Merge pull requests (merge/squash/rebase)
- **Update PR branch** - Sync PR with base branch

## Code & User Search
- **Search code** - Find code across repositories
- **Search users** - Find GitHub users

## What I **Cannot** Determine Without Testing

The actual scope depends on your PAT's permissions. Common limitations include:
- **Private repo access** - Depends on `repo` scope
- **Organization operations** - Depends on org permissions
- **Admin operations** - Deleting repos, managing webhooks, etc. (not available in these tools anyway)
- **Actions/Packages** - Not exposed through these MCP tools

Would you like me to test any specific operation, or would you like to know what you can do with your podtext repository specifically?