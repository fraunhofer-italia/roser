
# About Roser Bud

As explained above, this terminal allows to launch the default Roser commands and any Rose and Petal default and custom command.\
Remember, here the autocompletion is your friend and is always available.

## Bud Commands

Here are listed all the default functionalities:

- **help**: displays all the documented and undocumented commands. Furthermore:
  - If followed by a command displays the command documentation.
  - If followed by a Rose or Petal name displays the list of default and user defined commands and the relative documentation
- **quit**: closes Roser and all related active processes. It also removes the Rose configurations from the Petals.
- **clear**: clears the console screen.
- **spawn**: opens and connects a new terminal to an existing Roser Hip.
- **update**: tries to update all the Roser files, if everything is correctly configured, it runs the ``quit`` command above and opens again Roser.
- **pull**: updates (or downloads) all the sub-repositories. It uses Vcs and the related ``.repos`` file, and Git.
- **freeze**: creates a ``stable.repos`` file that points to the actual commit of all the sub-repositories
- **edit**: opens with one of the available text editor the ``roser.yaml`` of the specified Rose or Petal. Roser will check for one of the following listed text editors, order matters:
  - Visual Studio Code
  - Gedit
  - Nano
  - Vim
- **code**: available only if Visual Studio Code is installed. It uses VsCode to open the specified Rose or Petal. In case of a non host Petal by adding the option ``--container`` it allows to open the specified Rose or Petal container.

## Rose/Petal Commands

On the other hand, Rose and Petal commands have the following syntax:

```text
{{ rose/petal name }} {{ command name }} {{ arguments }} {{ options }}
```

Every non Host Petal has the following default commands:

- **build**: builds the Petal Docker image and creates a container by following the ``docker-compose.yml`` (``docker-compose-nvidia.yml`` in case of nvidia settings) file.
  - NB: this command has the option ``--docker--args`` to pass the ``docker compose build`` options.
  - NB: if Visual Studio Code is installed it also installs its extensions by using the [Dev Container](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) plugin settings. When this procedure ends VsCode Dev Container global and local workspace settings will be available inside the container. Wait until this procedure finishes to open a VsCode session inside the container.
- **start**: starts the Petal Docker Container.
- **stop**: kills the Petal Docker Container.
- **attach**: attaches to the running Petal Docker Container, in case of not yet started, start is executed.

These commands (except for  `attach` command) can be found also for every Rose, indeed a Rose default command executes the same command for each Petal that composes the Rose.

Custom Rose and Petal commands are defined by the ``roser.yaml``, see examples [doc/examples/rose.yaml](../examples/rose.yaml) and [doc/examples/petal.yaml](../examples/petal.yaml), and can be executed by simply running it by following the command structure explained above.

### Arguments

Rose/Petal Commands can also have arguments, these must be declared in the command definition and they can be passed to the command call.
Even in this case, autocompletion is available.

To see an example of how arguments are declared by a Petal and then used by a Rose go to the examples [doc/examples/petal.yaml](../examples/petal.yaml) and [doc/examples/rose.yaml](../examples/rose.yaml).

### Options

As shown above, each command (except start and stop command) has the possibility to add Roser options.
The list of options is shown here below.

- **-k, --kill** : kills and closes all the terminals of the specified Rose or Petal command.\
  NB: In case of Petal command, it kills the relative part inside the Roser Petals. Instead, in case of Rose command, it kills the relative Roser Hip (see [About Roser Hips](#about-roser-hips)).\
  NB: In the particular case of the Petal ``attach`` command, the target terminal to be killed can be selected with a second argument that identifies the attach terminal number.

## [Back](../../README.md#usage-:toolbox:)
