# Petal Structure

By default a Petal is a Docker Container and its structure must be comply with the following rules:

- **Folder Tree**: the Petal must contain the ``docker`` folder with inside:
  - a ``docker-compose.yml`` file (and a ``docker-compose-nvidia.yml`` file in case of nvidia settings)
  - a ``roser.yaml`` file (an example at [doc/examples/petal.yaml](../examples/petal.yaml))
- **Docker Names**: the container name must be equal to the Petal name
- **Petal and Petal Folder Names**: the Petal folder name must be the Petal name plus the suffix ``_ws``
- **Petal Volumes**: to create a Petal volume the destination folder or file must be mounted in the Docker container
  
However a Petal may not even be constrained to Docker, in this case the ``host`` key, defined inside the ``roser.yaml``, must be set to ``true`` and no constraints are present. These types of Petals will be called **Host Petals**.

## Petal Tips for Good Use

- **Folder Tree**: to be consistent with ROS folder structure:
  - have a ``src`` folder with all the packages inside
  - have a ``config`` folder for the all the configuration volumes
  - have a ``config`` folder inside the ``src`` folder for all the configuration packages
  - have an ``output`` folder for all the outputs, files or folders
- **Versioning**: use git for Petal components allows to better versioning

## [Back](../../README.md#configuration-:gear:)
