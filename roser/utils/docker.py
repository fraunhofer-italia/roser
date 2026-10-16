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
from dataclasses import dataclass
import os
from typing import Any, Dict, List, Tuple, Union
import yaml
import subprocess

from .logger import LOGGER
from .utils import (
    get_dict_value,
    ConfigurationException,
    user_question,
    bash_command,
)
from .git import Git
import docker
from urllib.parse import urlparse
import re

MANIFEST_INSPECT_COMMAND = """
docker manifest inspect {} | grep '"digest":' | head -n 1
"""


class Docker:
    @staticmethod
    def split_image_name(image_name: str) -> Tuple[str, str, str, str]:
        tag_pattern = r"^(.*):([^:\/]+)$"
        port_pattern = r"^(.*?):(\d+)/(.*)$"

        tag_match = re.match(tag_pattern, image_name)
        if tag_match:
            tag = tag_match.group(2)
            rest = tag_match.group(1)
        else:
            tag = "latest"
            rest = image_name

        # Split port from the path
        port_match = re.match(port_pattern, rest)
        if port_match:
            host = port_match.group(1)
            port = port_match.group(2)
            path = port_match.group(3)
        else:
            host = rest
            port = None
            path = None

        return host, port, path, tag

    @staticmethod
    def check_tag(tag: str) -> bool:
        # Check if the tag name starts with a letter or number
        if not tag[0].isalnum():
            return False

        # Check if the tag name contains only allowed characters
        if not re.match(r"^[a-zA-Z0-9_.-]+$", tag):
            return False

        # Check if the tag name does not contain a backslash
        if "\\" in tag:
            return False

        # Check if the tag name does not exceed 128 characters
        if len(tag) > 128:
            return False

        return True

    @staticmethod
    def remote_already_exist(remote: str) -> bool:
        try:
            docker.from_env().api.inspect_distribution(remote)
        except docker.errors.APIError as e:
            return False
        return True

    @staticmethod
    def push_image(remote: str, original_image: str, remote_image: str) -> bool:
        try:
            # TODO: do it only if remote is not already accessible
            # success, result = bash_command(f"docker login {remote}")
            # if not success:
            #     LOGGER.error(f"Failed to login to remote '{remote}'")
            #     return False
            # client.login(registry=remote)

            if Docker.remote_already_exist(remote_image):
                if not user_question(
                    f"Docker image '{remote_image}' already exist in remote, do you want to override it?"
                ):
                    return False

            client = docker.from_env()
            if original_image != remote_image:
                LOGGER.info(
                    f"Tagging actual image {original_image} with the new name {remote_image} ..."
                )
                client.images.get(original_image).tag(remote_image)

            LOGGER.info(f"Pushing image to remote ...")
            success, result = bash_command(f"docker push {remote_image}")
            if not success:
                LOGGER.error(f"Failed to login to remote '{remote}',. Error: {result}")
                return False
            # client.images.push(remote_image, stream=True)
        except (docker.errors.ImageNotFound, docker.errors.APIError) as e:
            LOGGER.error(f"Failed to push image. Error: {e}")
            return False

        LOGGER.info(f"Push completed.")
        return True


class DockerException(Exception):
    def __init__(self, message):
        error = message
        super().__init__(error)
        self.message = error

    def __str__(self):
        return f"DockerException: {self.message}"


@dataclass
class DockerComposeService:
    container_name: str
    image: str = None
    dockerfile_context: str = None
    dockerfile: str = None

    def parse(name: str, path: str, info: Dict[str, Any]):
        context = f"Parsing Service '{name}'"
        info = DockerComposeService.add_extension(
            name,
            path,
            info,
            get_dict_value(
                context=context,
                dictionary=info,
                key="extends",
                default={},
                value_types=dict,
            ),
        )

        (
            dockerfile_context,
            dockerfile,
        ) = DockerComposeService.get_dockerfile_from_build_parsing(
            path,
            get_dict_value(
                context=context,
                dictionary=info,
                key="build",
                default={},
                value_types=dict,
            ),
        )

        try:
            return DockerComposeService(
                image=get_dict_value(
                    context=info,
                    dictionary=info,
                    key="image",
                    default=name,
                    value_types=str,
                ),
                # TODO: remove -1 suffix
                container_name=get_dict_value(
                    context=context,
                    dictionary=info,
                    key="container_name",
                    default=f"docker-{name}-1",
                    value_types=str,
                ),
                dockerfile_context=dockerfile_context,
                dockerfile=dockerfile,
            )
        except ConfigurationException as e:
            raise ConfigurationException(f"Service {name}", e.message)

    def get_dockerfile_from_build_parsing(
        path: str, build: Dict[str, Any]
    ) -> Tuple[str, str]:
        if len(build) == 0:
            return None, None
        context = "Parsing 'build' field"
        dockerfile_context = get_dict_value(
            context=context,
            dictionary=build,
            key="context",
            default="",
            value_types=str,
        )
        dockerfile = os.path.join(
            path,
            dockerfile_context,
            get_dict_value(
                context=context,
                dictionary=build,
                key="dockerfile",
                default="Dockerfile",
                value_types=str,
            ),
        )
        if not os.path.isfile(dockerfile):
            LOGGER.error(
                f"In context {context}: No dockerfile found at path {os.path.normpath(dockerfile)}"
            )
            return None, None

        return dockerfile_context, os.path.normpath(dockerfile)

    def add_extension(
        service: str, path: str, info: Dict[str, Any], extends: Dict[str, str] = {}
    ) -> Dict[str, Any]:
        if len(extends.keys()) == 0:
            return info
        else:
            context = "Parsing 'extends' field"
            file = os.path.normpath(
                os.path.join(
                    path,
                    get_dict_value(
                        context=context,
                        dictionary=extends,
                        key="file",
                        default="",
                        value_types=str,
                    ),
                )
            )
            service = get_dict_value(
                context=context,
                dictionary=extends,
                key="service",
                default=service,
                value_types=str,
            )
            if os.path.isfile(file):
                with open(file, "r") as f:
                    content = yaml.load(
                        f.read(),
                        Loader=yaml.BaseLoader,  # Allow to interpret bool values as string in yaml
                    )
                services = get_dict_value(
                    context=context,
                    dictionary=content,
                    key="services",
                    default={},
                    value_types=dict,
                )
                extension_content = get_dict_value(
                    context=context,
                    dictionary=services,
                    key=service,
                    default={},
                    value_types=dict,
                )
                common_keys = list(set(info.keys()) & set(extension_content.keys()))
                if common_keys:
                    LOGGER.debug(
                        f"Pay attention the docker compose extension of service '{service}' overwrites keys '{common_keys}'"
                    )
                info.update(extension_content)
            else:
                raise ConfigurationException(
                    context, f"Extension file not found, {file}"
                )

        return info


class DockerComposeHandler:
    file: str
    version: float
    services: Dict[str, DockerComposeService]

    def __init__(self, file: str):
        self.file = file
        self.version, self.services = DockerComposeHandler.parse_file(file)
        return

    @staticmethod
    def parse_file(file: str) -> Tuple[str, Dict[str, Any]]:
        context = f"Docker Compose '{file}'"
        content = {}
        try:
            with open(file, "r") as f:
                content = yaml.load(
                    f.read(),
                    Loader=yaml.BaseLoader,  # Allow to interpret bool values as string in yaml
                )
        except (yaml.YAMLError, FileNotFoundError) as e:
            raise ConfigurationException(context, f"{e}")

        version = float(
            get_dict_value(
                context=context,
                dictionary=content,
                key="version",
                default=3.9,
                value_types=[str, float],
            )
        )
        services: Dict[str, DockerComposeService] = {}
        for service_name, service_content in get_dict_value(
            context=context,
            dictionary=content,
            key="services",
            value_types=dict,
        ).items():
            try:
                services[service_name] = DockerComposeService.parse(
                    service_name, os.path.dirname(file), service_content
                )
            except ConfigurationException as e:
                raise ConfigurationException(context, e.message)

        if not services:
            raise ConfigurationException(context, "No services defined.")

        for service_name, service in services.items():
            if not ":" in service.image:
                LOGGER.warning(
                    f"'image' tag in docker compose '{file}' in service '{service_name}' seems to not contain a link. This may create issue in freezing operations."
                )
                continue
            # try:
            #     (
            #         local_image_hash,
            #         remote_image_hash,
            #     ) = DockerComposeHandler.get_image_hashes(service.image)
            #     if not local_image_hash == remote_image_hash:
            #         LOGGER.outdated_image(
            #             f"Found outdated image {service.image}. \n \
            #                 Current hash {local_image_hash} \n \
            #                 Remote hash {remote_image_hash} \n \
            #                 To update run 'pull {service.container_name}'"
            #         )
            # except subprocess.CalledProcessError as e:
            #     msg = f"Unable to get hash of {e.cmd} image {service.image}."
            #     if e.cmd == "local":
            #         msg += "It will be automatically pulled during first build."
            #     elif e.cmd == "remote":
            #         msg += "It will be automatically generated during first freeze."
            #     LOGGER.warning(msg)

        return version, services

    @staticmethod
    def get_image_hashes(image_name: str):
        try:
            local_image_hash = docker.from_env().images.get(image_name).id
        except docker.errors.ImageNotFound:
            raise subprocess.CalledProcessError(returncode=1, cmd="local")
        # Run the command and capture its output
        remote_image_hash = subprocess.check_output(
            MANIFEST_INSPECT_COMMAND.format(image_name),
            shell=True,
            text=True,
            stderr=subprocess.DEVNULL,  # Suppress error output
        ).strip()
        if remote_image_hash == "":
            raise subprocess.CalledProcessError(returncode=1, cmd="remote")
        remote_image_hash = remote_image_hash[remote_image_hash.index(":") + 3 : -1]
        return local_image_hash.strip(), remote_image_hash.strip()

    def update(self):
        try:
            self.version, self.services = DockerComposeHandler.parse_file(self.file)
        except ConfigurationException as e:
            LOGGER.error(f"Docker Compose '{self.file}' wrongly defined. {e}")
            raise DockerException("Unable to parse Docker Compose file")

    @property
    def start(self) -> List[str]:
        return [
            f"docker start {' '.join([service.container_name for service in self.services.values()])}"
        ]

    @property
    def stop(self) -> List[str]:
        return [
            f"docker stop {' '.join([service.container_name for service in self.services.values()])} >/dev/null 2>&1"
        ]

    @property
    def kill(self) -> List[str]:
        return [
            f"docker kill {' '.join([service.container_name for service in self.services.values()])} >/dev/null 2>&1"
        ]

    @property
    def rm(self) -> List[str]:
        return self.kill + [
            f"docker container rm {' '.join([service.container_name for service in self.services.values()])} >/dev/null 2>&1"
        ]

    @property
    def up(self) -> List[str]:
        self.update()
        return [f"docker compose -f '{self.file}' up -d"]

    def pull(self, tag: str = None) -> List[str]:
        commands = []
        for service in self.services.values():
            if service.image is None:
                continue

            if not ":" in service.image:
                continue

            if tag is None:
                commands.append(f"docker pull {service.image}")
                continue

            link, original_tag = service.image.rsplit(":", 1)
            commands.append(f"docker pull {link}:{tag}")
            commands.append(f"docker tag {link}:{tag} {link}:{original_tag}")

        return self.rm + commands

    def build(
        self, use_dockerfile: bool = False, use_nocache: bool = False
    ) -> List[str]:
        update = self.up
        images = []
        for image in docker.from_env().images.list():
            images += image.tags
        # if not use_dockerfile:
        #     # TODO: check if I have a difference on my docker file
        #     if diff and user_question(f"Found a difference in Dockerfile: {diff}. \n \
        #                               Do you want to use docker file instead of remote image?"):
        #         use_dockerfile = True
        if use_nocache:
            update[0] = (
                f"docker compose -f '{self.file}' build --no-cache && " + update[0]
            )
        elif use_dockerfile:
            update[0] = f"docker compose -f '{self.file}' build && " + update[0]
        return self.rm + update

    def execute(self, service: str, command: str, hide: bool = False) -> List[str]:
        space = ""
        if service in self.services.keys():
            if hide:
                space = " "
            return [
                f"{space}docker exec -it {self.services[service].container_name} bash -ic '{command}'"
            ]
        else:
            raise DockerException(
                f"Service '{service}' do not exist. Failed to get execute call."
            )

    def compute_remotes(
        self, images: List[str], tag: str = None
    ) -> List[Tuple[str, str]]:
        remote_urls = [
            (urlparse(url).netloc + "/" + (urlparse(url).path).lstrip("/"))[:-4]
            for url in Git.get_remotes_url(os.path.dirname(self.file))
        ]
        result: List[Tuple[str, str]] = []
        for image in images:
            prefix = image + "-" if len(images) > 1 else ""
            host, port, path, _tag = Docker.split_image_name(image)
            tag = tag if not tag is None and not tag == "" else _tag
            if not None in [port, path] and f"{host}/{path}" in remote_urls:
                result += [(f"{host}:{port}", f"{host}:{port}/{path}:{prefix}{tag}")]
            else:
                if not remote_urls:
                    LOGGER.error(f"Unable to find Git remote for image '{image}'.")
                    continue
                if len(remote_urls) > 1:
                    LOGGER.error(f"Too many Git remotes for image '{image}'.")
                    continue
                index = remote_urls[0].index("/")
                host = remote_urls[0][:index]
                path = remote_urls[0][index:]
                # fill result
                result += [(f"{host}:{5050}", f"{host}:{5050}{path}:{prefix}{tag}")]

        return result

    def push_routine(self, tag: str = None) -> bool:
        self.update()
        images = [service.image for service in self.services.values()]
        remotes = self.compute_remotes(images, tag=tag)
        if not len(images) == len(remotes):
            LOGGER.error("Unable to generate remotes from images")
            return False

        success = True
        for image, remote in zip(images, remotes):
            remote_url = remote[0]
            remote_image = remote[1]
            if not Docker.push_image(remote_url, image, remote_image):
                success = False

        return success
