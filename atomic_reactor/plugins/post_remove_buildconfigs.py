"""
Copyright (c) 2015 Red Hat, Inc
All rights reserved.

This software may be modified and distributed under the terms
of the BSD license. See the LICENSE file for details.
"""

from __future__ import unicode_literals

import json
import os

from osbs.api import OSBS
from osbs.conf import Configuration

from atomic_reactor.plugin import PostBuildPlugin


class RemoveBuildConfigsPlugin(PostBuildPlugin):
    """
    Remove BuildConfigs no longer required.

    If this build is failing, remove the BuildConfig for it.

    Otherwise, remove any other BuildConfigs for this component.
    """

    key = "remove_buildconfigs"
    can_fail = False

    def __init__(self, tasker, workflow, url, verify_ssl=True, use_auth=True):
        """
        constructor

        :param tasker: DockerTasker instance
        :param workflow: DockerBuildWorkflow instance
        :param url: str, URL to OSv3 instance
        :param verify_ssl: bool, verify SSL certificate?
        :param use_auth: bool, initiate authentication with openshift?
        """
        # call parent constructor
        super(RemoveBuildConfigsPlugin, self).__init__(tasker, workflow)
        self.url = url
        self.verify_ssl = verify_ssl
        self.use_auth = use_auth

    def run(self):
        try:
            build_json = json.loads(os.environ["BUILD"])
        except KeyError:
            self.log.error("No $BUILD env variable. "
                           "Probably not running in build container.")
            return

        labels = build_json.get("metadata", {}).get("labels", {})
        try:
            my_buildconfig = labels["buildconfig"]
        except KeyError:
            self.log.error("No BuildConfig for this Build")
            return

        # initial setup will use host based auth: apache will be set
        # to accept everything from specific IP and will set specific
        # X-Remote-User for such requests
        osbs_conf = Configuration(conf_file=None, openshift_uri=self.url,
                                  use_auth=self.use_auth,
                                  verify_ssl=self.verify_ssl)
        osbs = OSBS(osbs_conf, osbs_conf)

        if self.workflow.build_is_failing:
            self.log.debug("Deleting my BuildConfig (%s)", my_buildconfig)
            osbs.delete_buildconfig(my_buildconfig)
        else:
            try:
                product_component = labels["product-component"]
            except KeyError:
                self.log.error("No product-component label set for this Build")
                return

            label = "product-component=%s" % product_component
            buildconfigs = osbs.list_buildconfigs(label=label)

            last_exc = None
            for buildconfig in buildconfigs:
                name = buildconfig.get_buildconfig_name()
                if name == my_buildconfig:
                    continue

                self.log.debug("Deleting old BuildConfig (%s)", name)
                try:
                    osbs.delete_buildconfig(name)
                except Exception as exc:
                    last_exc = exc
                    self.log.error("Caught exception: %r", exc)

            if last_exc is not None:
                raise last_exc
