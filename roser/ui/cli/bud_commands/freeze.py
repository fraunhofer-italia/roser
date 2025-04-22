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

from typing import List, Union
import git
import os

from .bud_command import BudCommand, complete_recursion
from ....utils import (
    LOGGER,
    has_flag,
    split_line,
    user_question,
    user_input,
    Docker,
    Git,
    Vcs,
)
from ....entities import Rose, Petal


class FreezeBudCommand(BudCommand):
    @property
    def flags(self):
        return [
            ("-od", "--only-docker"),
        ]

    def complete(self, text, line, begidx, endidx) -> List[str]:
        return complete_recursion(split_line(line)[1:], self.get_entities(), self.flags)

    def execute(self, text: str):
        FreezeBudCommand.freeze_entity(self.get_entity(text))

    def is_git_repo(entity: Union[Petal, Rose]):
        _git = git.Repo(entity.structure.path, search_parent_directories=True)
        return os.path.dirname(_git.git_dir).strip() == entity.structure.path.strip()

    def freeze_entity(entity: Union[Petal, Rose], tag: str = "") -> bool:
        error_string = f"Failed to freeze {entity.__class__.__name__} {entity.name}"
        create_new_version = not tag
        is_git_repo = FreezeBudCommand.is_git_repo(entity)
        if not is_git_repo and create_new_version:
            LOGGER.error(
                f"{error_string}. Unable to freeze Petals embedded in rose. Please run freeze on Rose instead."
            )
            return
        LOGGER.info("-" * 20)
        LOGGER.info(f"Running freeze on {entity.__class__.__name__} {entity.name}")
        LOGGER.info(f"Already present tags: {Git.get_tags(entity.structure.path)}")
        # check on tag is None to be retro-compatible.
        # this will ask to create a new version of the petal with an image_tag: key inside stable.repos
        stable_tag = (
            entity.structure.get_stable_image_tag()
            if isinstance(entity, Petal)
            else None
        )
        if create_new_version or (stable_tag is None and is_git_repo):
            tag = FreezeBudCommand._create_unified_tag()
            create_new_version = True
            if tag in Git.get_tags(entity.structure.path):
                if not user_question(
                    "Same tag already exists. Do you want to override it?"
                ):
                    LOGGER.error(f"{error_string}. Same tag already exists.")
                    return False
        else:
            tag = stable_tag if is_git_repo else tag

        if isinstance(entity, Petal):
            if create_new_version or not is_git_repo:
                latest_tag = None
                if not is_git_repo:
                    tag = entity.name + "-" + tag
                    latest_tag = entity.name + "-latest"
                if not FreezeBudCommand._freeze_docker(entity, tag=tag):
                    LOGGER.error(f"{error_string}. Unable to freeze docker.")
                    return False
                # Creates also stable image
                if not FreezeBudCommand._freeze_docker(entity, tag=latest_tag):
                    LOGGER.error(f"{error_string}. Unable to freeze docker.")
                    return False
            if not FreezeBudCommand._freeze_code(
                entity, tag=tag, create_new_version=create_new_version
            ):
                LOGGER.error(f"{error_string}. Unable to freeze code.")
                return False

        if isinstance(entity, Rose):
            all_petals_frozen = True
            for p in entity.petals.values():
                all_petals_frozen = (
                    all_petals_frozen and FreezeBudCommand.freeze_entity(p, tag=tag)
                )
            if not all_petals_frozen:
                LOGGER.error(f"{error_string}")
                return False

            if not FreezeBudCommand._freeze_code(entity, tag=tag):
                LOGGER.error(f"{error_string}. Unable to freeze code.")
                return False

        LOGGER.info(f"Done.")
        LOGGER.info("-" * 20 + "\n")
        return True

    def _freeze_code(
        entity: Union[Petal, Rose], tag: str = None, create_new_version: bool = True
    ) -> bool:
        LOGGER.info(f"Freezing code ... ")
        if isinstance(entity, Rose):
            rose_vcs_file = Vcs.search_files(entity.structure.path, stable=False)
            if not rose_vcs_file:
                LOGGER.error(
                    f"Failed to freeze {entity.__class__.__name__} {entity.name}. No VCS file found."
                )
                return
            if len(rose_vcs_file) > 1:
                LOGGER.warning("Multiple VCS files found. Using the first one.")
            rose_vcs_file = rose_vcs_file[0]
            exclude_from_vcs = [
                p.structure.path.replace(os.path.dirname(rose_vcs_file), "").lstrip("/")
                for p in entity.petals.values()
                if not FreezeBudCommand.is_git_repo(p)
            ]
        else:
            exclude_from_vcs = []

        if not entity.structure.freeze(
            tag=tag,
            do_tag=create_new_version,
            add_image_tag=isinstance(entity, Petal),
            exclude_from_vcs=exclude_from_vcs,
        ):
            LOGGER.error(f"Failed to freeze {entity.__class__.__name__} {entity.name}")
            return False
        return True

    # def freeze_entity_old(
    #     entity: Union[Petal, Rose], only_docker: bool = False, from_rose: bool = False
    # ):
    #     LOGGER.info(f"Running freeze on {entity.__class__.__name__} {entity.name}")
    #     LOGGER.info(f"Already present tags: {Git.get_tags(entity.structure.path)}")
    #     tag = (
    #         entity.structure.get_stable_image_tag()
    #         if isinstance(entity, Petal)
    #         else None
    #     )
    #     # check on tag is None to be retro-compatible.
    #     # this will ask to create a new version of the petal with an image_tag: key inside stable.repos
    #     if not from_rose or tag is None:
    #         tag = FreezeBudCommand._create_unified_tag()
    #         from_rose = False
    #         if tag in Git.get_tags(entity.structure.path):
    #             LOGGER.error(
    #                 f"Failed to freeze {entity.__class__.__name__} {entity.name}. Same tag already exists."
    #             )
    #             return False

    #     if not only_docker:
    #         if isinstance(entity, Rose):
    #             all_petals_frozen = True
    #             for p in entity.petals.values():
    #                 _git = git.Repo(p.structure.path, search_parent_directories=True)
    #                 # Do not freeze petals that belongs to rose repository
    #                 if (
    #                     os.path.dirname(_git.git_dir).strip()
    #                     != entity.structure.path.strip()
    #                 ):
    #                     continue
    #                 all_petals_frozen = (
    #                     all_petals_frozen
    #                     and FreezeBudCommand.freeze_entity(p, from_rose=True)
    #                 )
    #                 if not all_petals_frozen:
    #                     break

    #             if not all_petals_frozen:
    #                 LOGGER.error(
    #                     f"Failed to freeze {entity.__class__.__name__} {entity.name}"
    #                 )
    #                 return False

    #         if not entity.structure.freeze(
    #             tag=tag,
    #             do_tag=(not from_rose),
    #         ):
    #             LOGGER.error(
    #                 f"Failed to freeze {entity.__class__.__name__} {entity.name}"
    #             )
    #             return False

    #     # Freezes docker images by default
    #     if isinstance(entity, Petal) and not from_rose:
    #         FreezeBudCommand._freeze_docker(entity, tag=tag)
    #         if user_question(
    #             "Do you want also to push the image as the latest version?"
    #         ):
    #             FreezeBudCommand._freeze_docker(entity, tag=None)
    #     return True

    def _create_unified_tag():
        tag_created = False
        while not tag_created:
            tag = user_input(f"Insert the desired tag: ")
            tag_created = True
            tag.strip()
            if not Git.check_tag(tag):
                LOGGER.error("Git does not accept this tag.")
                tag_created = False
            if not Docker.check_tag(tag):
                LOGGER.error("Docker does not accept this tag.")
                tag_created = False
        LOGGER.info(f"Tag created '{tag}'")
        return tag

    def _freeze_docker(entity: Petal, tag: str = None) -> bool:
        LOGGER.info(f"Freezing image ... ")
        if entity.docker is None:
            LOGGER.info(f"Petal '{entity.name}' is an Host Petal, nothing to freeze.")
            return

        success = True
        if not entity.docker.push_routine(tag=tag):
            success = False
            LOGGER.error(f"Failed to freeze Docker Petal '{entity.name}'.")

        return success

    def help(self):
        LOGGER.info("Create a stable version of the specified Rose or Petal")
