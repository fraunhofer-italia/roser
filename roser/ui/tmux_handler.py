#
# Copyright 2024 Fraunhofer Italia Research scarl.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Marco Magri <marco.magri@fraunhofer.it>
# Author: Carlo Morganti <carlo.morganti@fraunhofer.it>
#
import math
import os
from dataclasses import dataclass, field
from typing import Dict, List

import libtmux

from ..utils import run_subprocess, append_to_bash_file, RoserENV, LOGGER

TERMS = {
    "gnome-terminal": "gnome-terminal -t {} -- tmux attach-session -t {}",
    "konsole": "konsole -p tabtitle=' {}: %w' -e \"tmux attach-session -t {}\" > /dev/null 2>&1 &",
}


@dataclass
class PanelOptions:
    ctrlc_on_exit: bool = True


@dataclass
class Window:
    name: str
    session: libtmux.Session
    commands: List[str] = field(default_factory=list)
    _window: libtmux.Window = None
    _panels: List[libtmux.Pane] = field(default_factory=list)
    _panel_options: List[PanelOptions] = field(default_factory=list)
    save_path: str = None

    def __post_init__(self) -> None:
        if not self.save_path is None:
            append_to_bash_file(
                self.save_path,
                [
                    f"! tmux has-session -t {self.session.name} 2>/dev/null && tmux new-session -d -s {self.session.name}",
                    f"tmux new-window -t {self.session.name}:{len(self.session.windows)} -n {self.name}",
                ],
            )
        self._window = self.session.new_window(self.name)
        self._panels = [self._window.panes[0]]
        if len(self.commands) > 1:
            # vertical split
            for _ in range(math.ceil(len(self.commands) / 2) - 1):
                self._panels += [self._panels[0].split_window()]
                if not self.save_path is None:
                    append_to_bash_file(
                        self.save_path,
                        f"tmux split-window -v -t {self.session.name}:{self.name}.0",
                    )
            # horizontal split
            new_panels = []
            for i, p in enumerate(self._panels):
                if i != 0:
                    i += 1
                if not self.save_path is None:
                    append_to_bash_file(
                        self.save_path,
                        f"tmux split-window -h -t {self.session.name}:{self.name}.{i}",
                    )
                new_panels += [p.split_window(vertical=False)]
            self._panels += new_panels

        for i, command in enumerate(self.commands):
            substituted_command = command.replace('"', '\\"').replace("$", "\$")
            if not self.save_path is None:
                append_to_bash_file(
                    self.save_path,
                    f"tmux send-keys -t {self.session.name}:{self.name}.{i} \"{' ' + substituted_command}\" C-m",
                )
            self._panel_options.append(
                PanelOptions(
                    ctrlc_on_exit=not (
                        "ssh" in substituted_command and "tmux" in substituted_command
                    )
                )
            )
            self._panels[i].send_keys(" " + command)

    def kill(self, save_path: str = None):
        if not save_path is None and os.path.isfile(save_path):
            append_to_bash_file(
                save_path,
                [
                    f"tmux send-keys -t {self.session.name}:{self.name} C-c >/dev/null 2>&1",
                    f"tmux kill-window -t {self.session.name}:{self.name} >/dev/null 2>&1",
                ],
            )
        try:
            for pane, options in zip(self._panels, self._panel_options):
                if options.ctrlc_on_exit:
                    pane.send_keys("C-c")
            self._window.kill_window()
        except libtmux.exc.LibTmuxException as e:
            pass


class Session:
    name: str
    windows: Dict[str, Window]
    server: libtmux.Server
    main_window: libtmux.Window
    session: libtmux.Session

    def __init__(
        self,
        name: str,
        server: libtmux.Server,
        spawn_terminal: bool = True,
        save_path: str = None,
    ):
        self.name = name
        self.server = server
        if not save_path is None:
            append_to_bash_file(
                save_path,
                [
                    f"tmux new-session -d -s {self.name} -n {self.name}",
                    f"tmux set-option -t {self.name} mouse 1",
                    f"tmux send-keys -t {self.name}:{self.name}.0 \"echo 'Created from Roser'\" C-m",
                ],
            )
        self.session = self.server.new_session(
            self.name, kill_session=True, window_name=self.name
        )
        self.session.set_option("mouse", "1")
        self.main_window = self.session.windows[0]
        self.main_window.panes[0].send_keys(
            f" python3 {os.path.dirname(__file__)}/header.py"
        )

        if spawn_terminal:
            self.spawn()
        self.windows = {}

    def launch_window(self, name: str, commands: List[str], save_path: str = None):
        try:
            self.windows[name].kill(save_path)
        except (KeyError, libtmux.exc.LibTmuxException):
            pass
        self.windows.update(
            {name: Window(name, self.session, commands, save_path=save_path)}
        )

    def spawn(self):
        if RoserENV.TERMINAL_PROVIDER:
            if RoserENV.TERMINAL_PROVIDER in TERMS.keys():
                os.system(
                    f" unset GTK_PATH;"
                    + TERMS[RoserENV.TERMINAL_PROVIDER].format(self.name, self.name)
                )
            else:
                LOGGER.error(
                    f"Unknown terminal provider: {RoserENV.TERMINAL_PROVIDER} known providers are {TERMS.keys()}. "
                    "Tying to use one of them."
                )
        else:
            for terminal_name, terminal_command in TERMS.items():
                if run_subprocess(f"{terminal_name} --version")[0]:
                    os.system(
                        f" unset GTK_PATH;"
                        + terminal_command.format(self.name, self.name)
                    )
                    break

        if RoserENV.ALWAYS_ON_TOP:
            os.system(
                f" wmctrl -i -r $(wmctrl -l | grep '{self.name}' | awk '{{print $1}}') -b add,above"
            )

    def kill(self, save_path: str = None):
        for _, w in self.windows.items():
            if not save_path is None and os.path.isfile(save_path):
                append_to_bash_file(
                    save_path,
                    [
                        f"tmux send-keys -t {self.name}:{w.name} C-c >/dev/null 2>&1",
                        f"tmux kill-window -t {self.name}:{w.name} >/dev/null 2>&1",
                    ],
                )
            w.kill()
        try:
            if not save_path is None and os.path.isfile(save_path):
                append_to_bash_file(
                    save_path,
                    f"tmux kill-window -t {self.name}:{self.main_window.name} >/dev/null 2>&1",
                )
            self.main_window.kill_window()
        except libtmux.exc.LibTmuxException as e:
            pass

        if not save_path is None:
            append_to_bash_file(
                save_path, f"tmux kill-session -t {self.name} >/dev/null 2>&1"
            )


class TMuxHandler:
    sessions: Dict[str, Session]
    hidden_mode: bool = False

    def __init__(self) -> None:
        self.server = libtmux.Server()
        os.environ["HISTCONTROL"] = "ignorespace"
        self.sessions = {}

    def exist_session(self, name: str) -> bool:
        return name in self.sessions.keys()

    def add_session(
        self, name: str, spawn_terminal: bool = True, save_path: str = None
    ):
        if self.exist_session(name):
            LOGGER.info("Killing already existing session.")
            self.kill_session(name, save_path=save_path)
        self.sessions[name] = Session(
            name,
            self.server,
            spawn_terminal and not self.hidden_mode,
            save_path=save_path,
        )

    def kill(self, keep_core_alive: bool = False):
        for _, session in self.sessions.items():
            session.kill()
        self.sessions = {}
        if not keep_core_alive:
            os.environ.pop("HISTCONTROL")
            if self.server.has_session("roser/bud"):
                self.server.kill_session("roser/bud")

    def kill_session(self, name: str, save_path: str = None) -> bool:
        try:
            self.sessions[name].kill(save_path)
            del self.sessions[name]
            return True
        except KeyError:
            return False

    def kill_window(
        self, session_name: str, window_name: str, save_path: str = None
    ) -> bool:
        try:
            self.sessions[session_name].windows[window_name].kill(save_path=save_path)
            return True
        except KeyError:
            return False

    def get_windows(self, session_name: str) -> List[str]:
        if self.exist_session(session_name):
            return list(self.sessions[session_name].windows.keys())
        return []


TMUX_HANDLER = TMuxHandler()
