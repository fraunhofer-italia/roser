#!/bin/sh

# Copyright 2023 Khalifah K. Shabazz
#
# Permission is hereby granted, free of charge, to any person obtaining a 
# copy of this software and associated documentation files (the “Software”),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

# Modified by: marco.magri@fraunhofer.it

apt install -y curl
set -e

# Auto-Get the latest commit sha via command line.
get_latest_release() {
    tag=$(curl --silent "https://api.github.com/repos/${1}/releases/latest" | # Get latest release from GitHub API
          grep '"tag_name":'                                              | # Get tag line
          sed -E 's/.*"([^"]+)".*/\1/'                                    ) # Pluck JSON value

    tag_data=$(curl --silent "https://api.github.com/repos/${1}/git/ref/tags/${tag}")

    sha=$(echo "${tag_data}"           | # Get latest release from GitHub API
          grep '"sha":'                | # Get tag line
          sed -E 's/.*"([^"]+)".*/\1/' ) # Pluck JSON value

    sha_type=$(echo "${tag_data}"           | # Get latest release from GitHub API
          grep '"type":'                    | # Get tag line
          sed -E 's/.*"([^"]+)".*/\1/'      ) # Pluck JSON value

    if [ "${sha_type}" != "commit" ]; then
        combo_sha=$(curl -s "https://api.github.com/repos/${1}/git/tags/${sha}" | # Get latest release from GitHub API
              grep '"sha":'                                                     | # Get tag line
              sed -E 's/.*"([^"]+)".*/\1/'                                      ) # Pluck JSON value

        # Remove the tag sha, leaving only the commit sha;
        # this won't work if there are ever more than 2 sha,
        # and use xargs to remove whitespace/newline.
        sha=$(echo "${combo_sha}" | sed -E "s/${sha}//" | xargs)
    fi

    printf "${sha}"
}

ARCH="x64"
U_NAME=$(uname -m)

if [ "${U_NAME}" = "aarch64" ]; then
    ARCH="arm64"
elif [ "${U_NAME}" = "x86_64" ]; then
    ARCH="x64"
elif [ "${U_NAME}" = "armv7l" ]; then
    ARCH="armhf"
fi

archive="vscode-server-linux-${ARCH}.tar.gz"
owner='microsoft'
repo='vscode'

get_subdirectory() {
    local directory="$1"
    
    if [ -d "$directory" ]; then
        # Change to the target directory
        cd "$directory"
    
        # List directories and capture the first one
        local subdirectory=$(ls -d -1 */ | head -n 1)
    
        if [ -n "$subdirectory" ]; then
            # Set an environment variable with the subdirectory name
            printf "${subdirectory%?}"
        else
            echo "No subdirectories found in $directory"
        fi
    else
        echo "Directory does not exist: $directory"
    fi
}

directory="/root/.vscode-server/bin/"

if [ -d "$directory" ]; then
    echo "code-server already exists, not installing"
    commit_sha=$(get_subdirectory "$directory")
else
    commit_sha=$(get_latest_release "${owner}/${repo}")
    if [ -n "${commit_sha}" ]; then
        echo "will attempt to download VS Code Server version = '${commit_sha}'"

        # Download VS Code Server tarball to tmp directory.
        curl -L "https://update.code.visualstudio.com/commit:${commit_sha}/server-linux-${ARCH}/stable" -o "/tmp/${archive}"

        # Make the parent directory where the server should live.
        # NOTE: Ensure VS Code will have read/write access; namely the user running VScode or container user.
        mkdir -vp ~/.vscode-server/bin/"${commit_sha}"

        # Extract the tarball to the right location.
        tar --no-same-owner -xzv --strip-components=1 -C ~/.vscode-server/bin/"${commit_sha}" -f "/tmp/${archive}"
    else
        echo "could not pre install vscode server"
    fi
fi
