# Git utilities reference

-----

::: dda.tools.git.Git
    options:
      members:
      - author_name
      - author_email
      - get_changes
      - get_commit
      - get_remote
      - add
      - commit
      - commit_file

::: dda.utils.git.commit.Commit
    options:
      members:
      - sha1
      - author
      - committer
      - message
      - committer_datetime
      - author_datetime

::: dda.utils.git.commit.GitPersonDetails
    options:
      members:
      - name
      - email
      - timestamp

::: dda.utils.git.changeset.ChangeSet
    options:
      members:
      - files
      - paths
      - added
      - modified
      - deleted
      - digest
      - from_patches

::: dda.utils.git.changeset.ChangedFile
    options:
      members:
      - path
      - type
      - binary
      - patch

::: dda.utils.git.changeset.ChangeType

::: dda.utils.git.remote.Remote
    options:
      members:
      - url
      - protocol
      - hostname
      - port
      - username
      - org
      - repo
      - full_repo
