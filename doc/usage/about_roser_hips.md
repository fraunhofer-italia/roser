# About Roser Hips

A Roser Hip is a Roser process constitued by a tmux-session.
The Roser Hips are created by the Roser Bud and the most known one is the Roser Petals, created at startup with a terminal connected to it.\
However, Roser creates a Roser Hip every time a Rose Command is executed.

To see a Roser Hip you can connect a terminal by executing on the Roser Bud the command:

```text
spawn {{ Roser Hip name}}
```

The list of living Roser Hips is accessible through the autocompletion, double tab to print it.

It is important to know that a Roser Hip stays alive even if there are no terminal displaying it.\
Indeed a Roser Hip does not die unless it is killed. The only way to kill a Roser Hip is to call the Rose command that generated it with the ``-k`` option.\
Due to the fact that the Roser Petals is not created by any Rose Command, it cannot be killed, and so it will stay alive until Roser shuts down.

NB: When the Roser Command ``quit`` is called every Roser Hip will be killed.

## [Back](../../README.md#usage-:toolbox:)
