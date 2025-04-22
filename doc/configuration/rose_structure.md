# Rose Structure

 The Petals of a Rose are defined by the Rose file ``roser.yaml`` with the dictionary under the key ``petals``, an example can be found [doc/examples/rose.yaml](../examples/rose.yaml).

The Rose constraints are:

- **Folder Tree**: the Rose must contain:
  - a ``roser.yaml`` file inside a ``docker`` folder (an example at [doc/examples/rose.yaml](../examples/rose.yaml))
  - a ``workspaces`` folder for all Petals
- **Rose and Rose Folder Names**: the Rose folder name must be the Rose name plus the suffix ``_ws``

## Rose Tips for Good Use

- **Folder Tree**: have a ``config`` folder for the all the configuration volumes. Inside the ``config`` folder have a folder with the Petal name for all the configurations files and folder of the relative Petal of the Rose.

## [Back](../../README.md#configuration-:gear:)
