"""
Copyright (c) 2015 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

from __future__ import unicode_literals

import json
import os

from atomic_reactor.core import DockerTasker
from atomic_reactor.inner import DockerBuildWorkflow
from atomic_reactor.plugin import PostBuildPluginsRunner, PluginFailedException
from atomic_reactor.util import ImageName
from tests.constants import INPUT_IMAGE, SOURCE
from atomic_reactor.plugins.post_remove_buildconfigs import RemoveBuildConfigsPlugin

from osbs.api import OSBS
from flexmock import flexmock
import pytest


class X(object):
    image_id = INPUT_IMAGE
    git_dockerfile_path = None
    git_path = None
    base_image = ImageName(repo="qwe", tag="asd")


def prepare():
    """
    Boiler-plate test set-up
    """

    tasker = DockerTasker()
    workflow = DockerBuildWorkflow(SOURCE, "test-image")
    setattr(workflow, 'builder', X())
    setattr(workflow.builder, 'image_id', 'asd123')
    setattr(workflow.builder, 'source', X())
    setattr(workflow.builder.source, 'dockerfile_path', None)
    setattr(workflow.builder.source, 'path', None)

    flexmock(OSBS)

    # No-op implementations until these are implemented in osbs-client
    setattr(OSBS, 'delete_buildconfig', lambda **kwargs: None)
    setattr(OSBS, 'list_buildconfigs', lambda **kwargs: None)

    flexmock(OSBS, delete_buildconfig=lambda name: None)
    flexmock(OSBS, list_buildconfigs=lambda **kwargs: [])

    runner = PostBuildPluginsRunner(tasker, workflow, [{
        'name': RemoveBuildConfigsPlugin.key,
        'args': {
            'url': '',
            'verify_ssl': False,
            'use_auth': False
        }}])

    return workflow, runner


def must_not_be_called(*_):
    """
    Set as implementation for methods than must not be called
    """

    assert False


def test_bad_setup():
    """
    Try all the early-fail paths.
    """

    workflow, runner = prepare()

    flexmock(OSBS, delete_buildconfig=must_not_be_called)
    flexmock(OSBS, list_buildconfigs=must_not_be_called)

    # No build JSON
    runner.run()

    # No metadata
    os.environ["BUILD"] = json.dumps({})
    runner.run()

    # No product-component label
    workflow.build_is_failing = False
    os.environ["BUILD"] = json.dumps({
        "metadata": {
            "labels": {
                "buildconfig": "my-buildconfig-id"
            }
        }
    })
    runner.run()


class Collect(object):
    """
    Collect the values a method is called with.
    """

    def __init__(self):
        self.called_with = []

    def called(self, value):
        """
        Set this as the implementation for the method to watch.
        """
        self.called_with.append(value)

    def raise_if(self, value, trigger):
        """
        Like called() but will also raise RuntimeError when value matches
        trigger.
        """
        self.called(value)
        if value == trigger:
            raise RuntimeError


def test_failing():
    """
    Test what happens when Build is failing.
    """

    workflow, runner = prepare()

    my_buildconfig_id = 'my-buildconfig-id'

    collect = Collect()
    flexmock(OSBS, delete_buildconfig=collect.called)
    flexmock(OSBS, list_buildconfigs=must_not_be_called)

    os.environ["BUILD"] = json.dumps({
        "metadata": {
            "labels": {
                "buildconfig": my_buildconfig_id
            }
        }
    })

    # Build failing
    workflow.build_is_failing = True
    runner.run()

    # Our own BuildConfig is deleted
    assert collect.called_with == [my_buildconfig_id]


class MockBuildConfigResponse(object):
    """
    OSBS.list_buildconfigs() will return a list of these.
    """

    def __init__(self, name):
        self.name = name

    def get_buildconfig_name(self):
        """
        Return the name for this BuildConfig
        """

        return self.name


def test_succeeding():
    """
    Test what happens when the Build is succeeding.
    """

    workflow, runner = prepare()

    my_buildconfig_id = 'my-buildconfig-id'
    buildconfigs = ['buildconfig1',
                    'buildconfig2']

    flexmock(OSBS,
             list_buildconfigs=lambda label: [MockBuildConfigResponse(x)
                                              for x in [my_buildconfig_id] +
                                              buildconfigs])
    collect = Collect()
    flexmock(OSBS, delete_buildconfig=collect.called)

    # Build succeeding
    workflow.build_is_failing = False
    os.environ["BUILD"] = json.dumps({
        "metadata": {
            "labels": {
                "buildconfig": "my-buildconfig-id",
                "product-component": "prod-comp"
            }
        }
    })
    runner.run()

    # All BuildConfigs other than our own are deleted
    assert set(collect.called_with) == set(buildconfigs)


def test_exception_while_removing():
    """
    Verify that delete_buildconfig() is called for all BuildConfigs it
    is supposed to be, even when it raises an exception for one of
    them.
    """

    workflow, runner = prepare()

    my_buildconfig_id = 'my-buildconfig-id'
    buildconfigs = ['buildconfig1',
                    'buildconfig2']

    flexmock(OSBS,
             list_buildconfigs=lambda label: [MockBuildConfigResponse(x)
                                              for x in [my_buildconfig_id] +
                                              buildconfigs])
    collect = Collect()
    flexmock(OSBS,
             delete_buildconfig=lambda name: collect.raise_if(name,
                                                              buildconfigs[0]))

    # Build succeeding
    workflow.build_is_failing = False
    os.environ["BUILD"] = json.dumps({
        "metadata": {
            "labels": {
                "buildconfig": "my-buildconfig-id",
                "product-component": "prod-comp"
            }
        }
    })

    with pytest.raises(PluginFailedException):
        runner.run()

    # All BuildConfigs other than our own should be deleted or
    # attempted to be deleted.
    assert set(collect.called_with) == set(buildconfigs)
