# Cut a release

Releases use git flow branches and Commitizen versions. A release tag (`vX.Y.Z`) builds the images and is what Flux deploys ([ADR-0009](../adr/0009-deployment-mechanism.md)).

## Branch model

| Branch | Purpose |
|---|---|
| `main` | Released code only. Every commit on it is tagged. |
| `develop` | Integration branch. Features merge here. |
| `feature/<name>` | One piece of work, from `develop`. |
| `release/<version>` | Stabilise a release, from `develop`. |
| `hotfix/<version>` | Urgent fix, from `main`. |

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/). The `commit-msg` hook rejects anything else. Run `uv run cz commit` to write one interactively.

## Finish a feature

```bash
git flow feature finish <name>     # merges feature/<name> into develop
git push origin develop
```

## Cut the release

1. Preview the version Commitizen will choose from the commits since the last tag:

   ```bash
   uv run cz bump --dry-run
   ```

2. Start the release branch with that version:

   ```bash
   git flow release start 0.1.0
   ```

3. Bump the version files and the changelog, without tagging. Git flow creates the tag in step 5.

   ```bash
   uv run cz bump --files-only --yes
   ```

   This updates the version in `pyproject.toml`, the image tags in `deploy/overlays/demo/kustomization.yaml` and `CHANGELOG.md`.

4. Commit:

   ```bash
   git commit -am "bump: release 0.1.0"
   ```

5. Finish the release. Git flow merges into `main` and `develop` and tags `v0.1.0`:

   ```bash
   git flow release finish 0.1.0
   ```

6. Push the branches and the tag:

   ```bash
   git push origin main develop --follow-tags
   ```

## What happens next

1. The **Images** workflow builds the four images and pushes them to GHCR tagged `0.1.0`.
2. Flux sees tag `v0.1.0` and applies `deploy/overlays/demo`, which now points at `0.1.0`.
3. Check with `kubectl -n flux-system get kustomization healthcare-aiops`.

The image build takes a few minutes. Until it finishes, the new pods report `ImagePullBackOff` and recover on their own.
