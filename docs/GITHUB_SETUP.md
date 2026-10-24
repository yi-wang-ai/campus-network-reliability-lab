# Publish to GitHub

1. Create a public repository named `campus-network-reliability-lab` at https://github.com/new. Leave README/license/gitignore unchecked; this ZIP already contains them.
2. Extract this ZIP and open a terminal in `campus-network-reliability-lab`.
3. Run the commands below, replacing `YOUR-USERNAME` with your own GitHub login.

```bash
git init
git add .
git commit -m "feat: add OSPF resilience lab and automated failover checks"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/campus-network-reliability-lab.git
git push -u origin main
```

4. Confirm the GitHub Actions checks run. After a genuine lab demo, add real evidence, update the test report, and pin the repository to your profile.

Do not upload `.env`, VM keys, real network credentials, or generated `clab-*/` artifacts.
