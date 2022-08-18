

# Please invoke from WNTR directory 
# create image 
# podman build -t ubuntu-python-wntr -f ./container/ubuntu .
# docker 
# create container / run image
# podman run --rm -it localhost/ubuntu-python-wntr /bin/bash

FROM docker.io/ubuntu:latest
RUN apt-get update && apt-get install -y python3 
RUN apt-get install -y python3-pip

COPY . /home/WNTR

WORKDIR /home/WNTR
RUN pip3 install .


WORKDIR /home
CMD ["echo" ""]





