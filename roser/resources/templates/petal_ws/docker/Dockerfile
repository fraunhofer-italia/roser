# FROM select an image to inherit from
ENV DEBIAN_FRONTEND noninteractive
ENV DEBIAN_FRONTEND teletype

RUN apt-get -y update && apt-get -y install gdb xterm terminator python3-pip tmux
RUN pip install black 

RUN apt-get -y update && apt-get -y install \
    ros-${ROS_DISTRO}-rmw-cyclonedds-cpp

ENV ROS_WS_DIR="/{{ name }}_ws"
WORKDIR ${ROS_WS_DIR}

RUN echo "source ${ROS_WS_DIR}/environment.sh" >> ~/.bashrc && \
    echo "export RCUTILS_COLORIZED_OUTPUT=1" >> ~/.bashrc && \
    echo "source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash" >> ~/.bashrc && \
    echo "alias rbuild='(cd ${ROS_WS_DIR} && colcon build --cmake-args -DBUILD_TESTING=OFF && source install/setup.sh)'" >> ~/.bash_aliases && \
    echo "alias rclean='(cd ${ROS_WS_DIR} && rm -rf install/ log/ build/)'"  >> ~/.bash_aliases

# ADD YOUR ADDITIONAL COMMANDS HERE