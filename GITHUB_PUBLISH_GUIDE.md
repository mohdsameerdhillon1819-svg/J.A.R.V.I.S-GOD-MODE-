# Publish Mark-LVII as a GitHub repository (VS Code on Windows)

## Before publishing

1. This is a **community integration edition** built from FatihMakes' original Mark-LVII (CC BY-NC 4.0). Preserve the upstream attribution and `LICENSE`.
2. Rotate API keys that have been shared in chats or screenshots. Do not add them to Git.
3. Inspect `INTEGRATIONS_AND_LICENSES.md`, `SECURITY.md`, `readme.md`, and `.gitignore`.
4. Test on your Windows PC; webcam and live connections were not verified during ZIP preparation.

## Publish from VS Code

1. Extract this ZIP. In VS Code, click **File > Open Folder** and choose the `Mark-LVII` folder.
2. Sign into your GitHub account in VS Code (Accounts menu). Install Git for Windows if prompted.
3. Open the **Source Control** icon on the left (Ctrl+Shift+G), click **Initialize Repository** if shown.
4. Review all changed files carefully. **Make sure no `.env`, OAuth JSON, saved memory, logs, keys, tokens, or `external/` appear in changes.**
5. Add a commit message such as `Initial public community integration edition` and select **Commit**.
6. Click **Publish to GitHub** and choose **Public** only when ready. If you used GitHub Fork, push to your fork instead.
7. Suggested repo name: `mark-lvii-community-integrations`.
8. On GitHub, verify the license, credits, README and absence of secrets. Enable GitHub secret scanning where available.

### Optional Git terminal alternative

After creating an empty GitHub repository that has **no added README/license**:

```powershell
git init
git add .
git status
git commit -m "Initial community integration edition"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/mark-lvii-community-integrations.git
git push -u origin main
```

If publishing as a fork, keep its relationship to the original repository visible. Never force-push over an unrelated repo.

## Test locally

```powershell
py -3.12 -m unittest discover -s tests -v
```

This command checks offline tests; passing does not confirm live traffic, Gmail OAuth, or physical gesture detection.
