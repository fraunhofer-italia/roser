# ROSER :rose:

## Description :scroll:

**Roser** aims to help **users** and even more **developers** to **manage**, **use** and **create** applications. It creates a **simplified** command line architecture, thanks to the powerful and user friendly **shortcuts**, and allows smart handling of multiple terminals.\
To do so we based our approach on the modular logic coming from **Docker** containers and we created a **standardized way of developing** complex ROS software architectures into simplified interfaces for reconfigurable tools.\
This package complies with the **modular approach** and it allows to manage complex **ROS systems** in a user-friendly framework, composed by **Roses** and **Petals**. **Petals** are a general purpose or hardware related software tools that constitute the core functionalities (e.g. ROS workspaces); **Roses** are a higher level managers of different **Petals**, other **Roses** or a composition of them (e.g the [Concert Project](https://concertproject.eu/)).

## Installation :wrench:

Roser is a Python package and it requires at least Python 3.8. One of the Roser core libraries is Docker, and it has to be already installed on the PC with administrator privileges, as suggested by the [Docker installation guide](https://docs.docker.com/engine/install/). All other dependencies can be found [here](#dependencies), if not already on the system, Roser will ask for their installation.

To install the **last stable** version run the command:

```bash
pip install -U git+https://github.com/fraunhofer-italia/roser.git
```

### [Other Installation Solutions](doc/installation/other_installation_solutions.md#other_installation_solutions)

## Configuration :gear:

The Roser configuration, so Roses and Petals (respectively Projects and Tools) definitions are based on Yaml files. In particular, they both are defined by the presence of the ``roser.yaml`` file. \
You can find an example of a ``roser.yaml`` file for a **Rose** here ([doc/examples/rose.yaml](doc/examples/rose.yaml)), and an example of a ``roser.yaml`` file for a **Petal** here ([doc/examples/petal.yaml](doc/examples/petal.yaml)).

To work properly with the Roser system both Roses and Petals must comply with a predefined structure. Their required constraints and the suggestions for good use are listed here below.

### [Petal Structure](doc/configuration/petal_structure.md#petal-structure)

### [Rose Structure](doc/configuration/rose_structure.md#rose-structure)

## Usage :toolbox:

Roser offers a Python CLI composed by default and user defined commands.
To start Roser you need to navigate inside a Rose or Petal folder and then run the command ``roser``.

The startup will be followed by:

- turning the terminal where the command ``roser`` was launched into a Python CLI. This is the **Roser Bud**, here you have access to the Rose and Petal commands.
- opening of an always on top terminal, a **Roser Hip**. In particular, this one is called **Roser Petals**, the Petal commands outputs will be displayed here.

### [Roser Options](doc/usage/roser_options.md#roser-options)

### [About Roser Bud](doc/usage/about_roser_bud.md#about-roser-bud)

### [About Roser Hips](doc/usage/about_roser_hips.md#about-roser-hips)

### [User Settings](doc/usage/user_settings.md)

## Dependencies :white_check_mark:

Package Manager Dependencies:

- **Docker** (and Docker Compose) v20.10.22
- **Git** v2.34.1
- **Tmux** v3.2a
- **Code** latest-version(1.84.2) ([update](https://askubuntu.com/questions/833448/how-can-i-update-visual-studio-code-on-ubuntu))

Python Dependencies:

- **docker** v6.1.3
- **pyfiglet** v0.8.post1
- **libtmux** v0.22.1
- **colorlog** v6.7.0
- **vcstool** v0.3.0
- **pexpect** v4.8.0

--- 

### Licence

ROSER is licensed under the terms of the Apache License 2.0. The project has received financial support by the Horizon 2020 EU Project [CONCERT](https://concertproject.eu/).

**Authors**: 
  - Carlo Morganti
  - Marco Magri

**Maintainers**: 
  - [Carlo Morganti](carloski@live.it)
  - [Marco Magri](marco.magri.dev@gmail.com)
