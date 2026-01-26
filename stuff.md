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

---
Credits used ca. 250 for the initial build, another 100 for enhancements and bug-fixes.

---

If you run "make test", you'll notice that some tests fail. Create a list of the failed test, then create a GitHub issue that notes all the failing test, with label "bug" added to the  issue.

Read the issues in the repo, that are open and have the label "bug". For each found, analyze the description of the issue. Next, analyze the codebase and find the root-cause of the issue. Before you make any changes to the repo, create a feature branch. Fix the issue, make sure that all tests pass, or add new tests if needed. Once you are done with the implementation, create a pull request and link it to the issue for manual review.

---
There are open issues in GitHub, that have the label "enhancement". For each found, I want you to one-shot an implementation. Do not bother with creating requirements, design and task documents on how to implement the issue, but don't be lazy in your implementation either. Apply all the good work you usually do. Before you make any changes to the repo, create a feature branch. Fix the issue, make sure that all tests pass, or add new tests if needed. Once you are done with the implementation, create a pull request and link it to the issue for manual review.