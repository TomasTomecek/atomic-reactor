"""
Copyright (c) 2015 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.


Python API for atomic_reactor. This is the official way of interacting with atomic_reactor.
"""
from atomic_reactor.inner import DockerBuildWorkflow
from atomic_reactor.outer import PrivilegedBuildManager, DockerhostBuildManager


__all__ = (
    'build_image_in_privileged_container',
    'build_image_using_hosts_docker',
    'build_image_here',
)


def build_image_in_privileged_container(build_image, source, image,
        parent_registry=None, target_registries=None, push_buildroot_to=None,
        parent_registry_insecure=False, target_registries_insecure=False,
        dont_pull_base_image=False, **kwargs):
    """
    build image from provided dockerfile (specified by `source`) in privileged image

    :param build_image: str, image where target image should be built
    :param source: dict, where/how to get source code to put in image
    :param image: str, tag for built image ([registry/]image_name[:tag])
    :param parent_registry: str, registry to pull base image from
    :param target_registries: list of str, list of registries to push image to (might change in future)
    :param push_buildroot_to: str, repository where buildroot should be pushed
    :param parent_registry_insecure: bool, allow connecting to parent registry over plain http
    :param target_registries_insecure: bool, allow connecting to target registries over plain http
    :param dont_pull_base_image: bool, don't pull or update base image specified in dockerfile

    :return: BuildResults
    """
    build_json = {
        "image": image,
        "source": source,
        "parent_registry": parent_registry,
        "target_registries": target_registries,
        "parent_registry_insecure": parent_registry_insecure,
        "target_registries_insecure": target_registries_insecure,
        "dont_pull_base_image": dont_pull_base_image,
    }
    build_json.update(kwargs)
    m = PrivilegedBuildManager(build_image, build_json)
    build_response = m.build()
    if push_buildroot_to:
        m.commit_buildroot()
        m.push_buildroot(push_buildroot_to)
    return build_response


def build_image_using_hosts_docker(build_image, source, image,
        parent_registry=None, target_registries=None, push_buildroot_to=None,
        parent_registry_insecure=False, target_registries_insecure=False,
        dont_pull_base_image=False, **kwargs):
    """
    build image from provided dockerfile (specified by `source`) in container
    using docker from host

    :param build_image: str, image where target image should be built
    :param source: dict, where/how to get source code to put in image
    :param image: str, tag for built image ([registry/]image_name[:tag])
    :param parent_registry: str, registry to pull base image from
    :param target_registries: list of str, list of registries to push image to (might change in future)
    :param push_buildroot_to: str, repository where buildroot should be pushed
    :param parent_registry_insecure: bool, allow connecting to parent registry over plain http
    :param target_registries_insecure: bool, allow connecting to target registries over plain http
    :param dont_pull_base_image: bool, don't pull or update base image specified in dockerfile

    :return: BuildResults
    """
    build_json = {
        "image": image,
        "source": source,
        "parent_registry": parent_registry,
        "target_registries": target_registries,
        "parent_registry_insecure": parent_registry_insecure,
        "target_registries_insecure": target_registries_insecure,
        "dont_pull_base_image": dont_pull_base_image,
    }
    build_json.update(kwargs)
    m = DockerhostBuildManager(build_image, build_json)
    build_response = m.build()
    if push_buildroot_to:
        m.commit_buildroot()
        m.push_buildroot(push_buildroot_to)
    return build_response


def build_image_here(source, image,
        parent_registry=None, target_registries=None, parent_registry_insecure=False,
        target_registries_insecure=False, dont_pull_base_image=False, **kwargs):
    """
    build image from provided dockerfile (specified by `source`) in current environment

    :param source: dict, where/how to get source code to put in image
    :param image: str, tag for built image ([registry/]image_name[:tag])
    :param parent_registry: str, registry to pull base image from
    :param target_registries: list of str, list of registries to push image to (might change in future)
    :param parent_registry_insecure: bool, allow connecting to parent registry over plain http
    :param target_registries_insecure: bool, allow connecting to target registries over plain http
    :param dont_pull_base_image: bool, don't pull or update base image specified in dockerfile

    :return: BuildResults
    """
    build_json = {
        "image": image,
        "source": source,
        "parent_registry": parent_registry,
        "target_registries": target_registries,
        "parent_registry_insecure": parent_registry_insecure,
        "target_registries_insecure": target_registries_insecure,
        "dont_pull_base_image": dont_pull_base_image,
    }
    build_json.update(kwargs)
    m = DockerBuildWorkflow(**build_json)
    return m.build_docker_image()


def list_dockerfiles_in_git():
    """
    clone provided repo and return all dockerfiles found in the repo

    :return:
    """
