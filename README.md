# Libvirt Gitlab Cloudctl

A tiny wrapper meant to serve as an abstract layer over various cloud backends abstracting the individual backend Python API. It's supposed to run
from within a container as part of GitLab CI pipelines, so it relies on environment variables to expose the necessary backend data, like API tokens etc.
