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
from __future__ import annotations

import copy
import os
from typing import Any, Dict, List, Optional, Union

import jinja2
from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    field_validator,
    model_validator,
)

from ...utils import convert_bools, LOGGER


class KeepUndefined(jinja2.Undefined):
    def __str__(self) -> str:
        return "{{ " + self._undefined_name + " }}"


JINJA_ENV = jinja2.Environment(undefined=KeepUndefined)


class InvalidArgument(BaseException):
    def __init__(self, arg_name, arg_value, options) -> None:
        super().__init__(
            f"Provided value `{arg_value}` not valid for argument `{arg_name}`. Valid options are {options}"
        )


class ArgumentException(Exception):
    def __init__(self, key):
        error = f"The key {key} is wrongly defined"
        super().__init__(error)
        self.message = error

    def __str__(self):
        return self.message


class FromFolderOptionsHandler(BaseModel):
    folder: str
    recursive: Optional[bool] = False
    consider_files: Optional[bool] = True
    consider_folders: Optional[bool] = True

    def get_options(self):
        options = []
        if not os.path.isdir(self.folder):
            return []
        for root, dirs, files in os.walk(self.folder):
            relpath = lambda path: os.path.relpath(path, self.folder)
            if self.consider_files:
                options.extend([relpath(os.path.join(root, file)) for file in files])
            if self.consider_folders:
                options.extend([relpath(os.path.join(root, dir)) for dir in dirs])
            if not self.recursive:
                break
        return options


class Argument(BaseModel):
    name: str
    value: str
    options: Optional[Union[List[str], FromFolderOptionsHandler]] = Field(
        default_factory=list
    )
    allow_undeclared: Optional[bool] = False
    _original_value: str = PrivateAttr(default=None)

    def __init__(
        __pydantic_self__,
        dict: Optional[Dict[str, Any]] = None,
        dict_file_path: str = "",
        *,
        name: Optional[str] = None,
        value: Optional[str] = None,
        options: Optional[Union[List[str], "FromFolderOptionsHandler"]] = None,
        allow_undeclared: Optional[bool] = False,
    ):
        if dict is not None:
            # Initialize from dict parameter
            super().__init__(**dict)
            value = dict.get("value")
        else:
            # Initialize from individual arguments
            super().__init__(
                name=name,
                value=value,
                options=options or [],
                allow_undeclared=allow_undeclared,
            )

        # Custom initialization logic
        __pydantic_self__._original_value = convert_bools(copy.deepcopy(value))
        if isinstance(__pydantic_self__.options, FromFolderOptionsHandler):
            full_dict_path = os.path.realpath(
                os.path.join(
                    os.path.dirname(dict_file_path), __pydantic_self__.options.folder
                )
            ).strip()
            __pydantic_self__.options.folder = full_dict_path

    @property
    def resolved_options(self) -> List[str]:
        if isinstance(self.options, FromFolderOptionsHandler):
            if not os.path.isdir(self.options.folder):
                LOGGER.warning(f"Folder {self.options.folder} does not exist")
            return self.options.get_options()
        return self.options

    def update(self, value: Union[str, Argument]) -> Argument:
        checked_value = value.value if isinstance(value, Argument) else value
        if (
            self.resolved_options
            and not self.allow_undeclared
            and not (checked_value in self.resolved_options)
        ):
            raise InvalidArgument(self.name, checked_value, self.resolved_options)

        return (
            value
            if isinstance(value, Argument)
            else Argument(
                name=self.name,
                value=value,
                options=self.options,
                allow_undeclared=self.allow_undeclared,
            )
        )

    def evaluate_jinja(self, jinja_dict: Dict[str, str]) -> Argument:
        rendered_value = JINJA_ENV.from_string(self._original_value).render(jinja_dict)
        return Argument(
            name=self.name,
            value=rendered_value,
            options=self.options,
            allow_undeclared=self.allow_undeclared,
        )

    def __str__(self) -> str:
        return self.value


class Arguments(Dict[str, Argument]):
    _original_arguments: Dict[str, Argument] = None

    def __init__(self, dict: Dict[str, Dict[str, Any]] = {}, dict_file_path: str = ""):
        for key, value in dict.items():
            if isinstance(value, str):
                value = {"name": key, "value": value}
            else:
                value["name"] = key
            dict[key] = Argument(dict=value, dict_file_path=dict_file_path)
        super().__init__(dict)

    def copy(self) -> Arguments:
        return Arguments(
            {key: copy.deepcopy(value._original_value) for key, value in self.items()}
        )

    def update(self, arguments: Dict[str, str], override_default: bool = False) -> None:
        if self._original_arguments is None:
            self._original_arguments = copy.deepcopy(self)

        for key, value in arguments.items():
            if key in self.keys():
                self[key] = self[key].update(value)
            else:
                self[key] = Argument(name=key, value=value._original_value, options=[])

        if override_default:
            self._original_arguments = copy.deepcopy(self)

    def delete(self, keys: List[str]):
        for key in keys:
            if key in self.keys():
                del self[key]

    def evaluate_jinja(self, jinja_dict: Dict[str, str]):
        for key, arg in self.items():
            self[key] = arg.evaluate_jinja(jinja_dict)
