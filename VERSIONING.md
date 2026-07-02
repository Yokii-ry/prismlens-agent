# Versioning and Branch Workflow

This project uses semantic versioning and a lightweight Git flow.

## Branches

- `main`: stable production-ready code only.
- `develop`: integration branch for the next version.
- `feature/<name>`: new features or non-urgent changes, branched from `develop`.
- `fix/<name>`: bug fixes for the next version, branched from `develop`.
- `release/<version>`: release stabilization branch, branched from `develop`.
- `hotfix/<version>`: urgent production fixes, branched from `main`.

## Versions

Use semantic versioning:

- `MAJOR`: breaking changes.
- `MINOR`: backward-compatible features.
- `PATCH`: backward-compatible fixes.

Current stable version:

- `v1.0.0`

## Normal Iteration

1. Start work from `develop`.
2. Create a task branch:

   ```bash
   git switch develop
   git switch -c feature/<name>
   ```

3. Commit changes on the task branch.
4. Merge the task branch back into `develop`.
5. When ready to release, create a release branch:

   ```bash
   git switch develop
   git switch -c release/1.1.0
   ```

6. Test and fix only release-blocking issues on the release branch.
7. Merge the release branch into `main`.
8. Tag the release:

   ```bash
   git switch main
   git tag -a v1.1.0 -m "Release v1.1.0"
   ```

9. Merge `main` back into `develop`.

## Hotfix Flow

For urgent fixes to the current stable version:

```bash
git switch main
git switch -c hotfix/1.0.1
```

After fixing and testing:

```bash
git switch main
git merge hotfix/1.0.1
git tag -a v1.0.1 -m "Release v1.0.1"
git switch develop
git merge main
```

## Push

Push branches and tags to the remote:

```bash
git push -u origin main
git push -u origin develop
git push origin --tags
```
