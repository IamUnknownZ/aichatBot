# Push the latest Sorty version

Target repository: https://github.com/IamUnknownZ/aichatBot

App entry point: `app.py`. Dependency file: `requirements.txt`.

## Push from your authenticated terminal

The GitHub remote is named `github`. The original local `origin` is preserved.

```bash
git status
git fetch github
git log --oneline --left-right ready-to-push...github/main
git push github ready-to-push:main
```

The prepared branch starts from GitHub's `main`, because the local `main` has unrelated history. Your local branch is unchanged. You do not need to switch branches to run this push command.

Check the comparison before pushing. If the remote has newer commits, stop and reconcile them before pushing. Do not force-push. If the Cloud app uses another branch, select that branch deliberately instead.

For HTTPS authentication, use your GitHub credential manager or a personal access token when prompted. Do not put a token in the remote URL or commit it.

## Streamlit deployment checklist

Confirm the existing Cloud app uses this repository, the intended branch, and `app.py`.

Keep `GEMINI_API_KEY` and `DATABASE_URL` in Streamlit Secrets, never in Git. Use the database configured for that Cloud app.

New approved documents and manifest changes also require a database refresh. A Git push alone does not update PostgreSQL:

```bash
source venv/bin/activate
python -m scripts.ingest_pdf --force
```

Run ingestion only after checking your private environment points to the intended deployment database. This command calls the embedding API and updates the index; it was not run during push preparation.

Keep `RAG_AUTO_INGEST=false` and `RAG_ALLOW_MEMORY_FALLBACK=false`. See [DEPLOYMENT.md](DEPLOYMENT.md) for the complete setup.

After deploying, test Thai and English answers, Bubble versus Selection comparisons, curriculum boundaries, and images persisting through reruns. Passing local tests does not establish remote database or model availability.

Generated presentation exports are excluded because their visual verification is unfinished. Research Markdown remains included. Existing deletions in the unrelated legacy `workaw_chatbot` files are left outside this app-update commit.
