# Roser Options

The available ``roser`` command options are:

- **-h, --help**: displays all the ``roser`` command options and the related documentations

- **-i, --import**: searches for all the Git submodules and Vcs files and clones/imports/updates everything. In case of Git repository the procedure is not executed in case of uncommitted changes.

- **-is, --import-stable**: searches for all the ``stable.repos`` files and executes the ``--import`` option on them. In the following sections will be explained how to make versioning with Roser, search for ``freeze`` command.

- **--hidden**: starts Roser CLI in hidden mode. No terminal will be shown.

- **-c COMMAND, --command COMMAND**: sends a Roser command to an existing Roser Bud. If it does not exist, one is launched with the ``roser --hidden`` command.

- **-q, --quit**: closes the started Roser and all related active processes.

- **-a, --attach**: connects the terminal to the Roser Bud or to the specified Roser Hip. (REVIEW REQUIRED)

- **--prefix**: adds the specified prefix to the Roser Bud.

- **--ssh**: starts Roser on a remote PC on a specific folder and by linking it with the actual PC. Requires a second argument of the form ``user@ip:path_to_folder``

## [Back](../../README.md#usage-:toolbox:)
