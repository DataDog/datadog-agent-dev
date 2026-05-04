# SPDX-FileCopyrightText: 2024-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest

from dda.config.model import construct_model
from dda.config.model.repos import RepoConfig, default_repos, resolve_clone_url


class TestDefaultRepos:
    def test_contains_datadog_and_ddoghq(self):
        repos = default_repos()
        assert "DataDog" in repos
        assert "ddoghq" in repos

    def test_datadog_url_prefix(self):
        assert default_repos()["DataDog"].url == "git@github.com:DataDog"

    def test_ddoghq_url_prefix(self):
        assert default_repos()["ddoghq"].url == "git@github.com:ddoghq"


class TestRepoConfig:
    def test_round_trip_defaults(self):
        config = construct_model({})
        assert config.repos == default_repos()

    def test_round_trip_with_per_repo_url(self):
        data = {"repos": {"datadog-agent": {"url": "git@github.com:MyFork/datadog-agent.git"}}}
        config = construct_model(data)
        assert config.repos["datadog-agent"] == RepoConfig(url="git@github.com:MyFork/datadog-agent.git")

    def test_round_trip_org_url_override(self):
        data = {"repos": {"DataDog": {"url": "git@mygitlab.example.com:DataDog"}}}
        config = construct_model(data)
        assert config.repos["DataDog"].url == "git@mygitlab.example.com:DataDog"


class TestResolveCloneUrl:
    def test_default_org(self, app):
        assert resolve_clone_url(app, "datadog-agent") == "git@github.com:DataDog/datadog-agent.git"

    def test_ddoghq_org(self, app):
        assert resolve_clone_url(app, "datadog-agent", org="ddoghq") == "git@github.com:ddoghq/datadog-agent.git"

    def test_per_repo_url_override(self, app, config_file):
        config_file.data.setdefault("repos", {})["datadog-agent"] = {"url": "git@github.com:MyFork/datadog-agent.git"}
        config_file.save()
        assert resolve_clone_url(app, "datadog-agent") == "git@github.com:MyFork/datadog-agent.git"

    def test_custom_org_url(self, app, config_file):
        config_file.data.setdefault("repos", {})["DataDog"] = {"url": "git@mygitlab.example.com:DataDog"}
        config_file.save()
        assert resolve_clone_url(app, "datadog-agent") == "git@mygitlab.example.com:DataDog/datadog-agent.git"

    def test_missing_org_raises(self, app, config_file):
        config_file.data["repos"] = {}
        config_file.save()
        with pytest.raises(KeyError, match="DataDog"):
            resolve_clone_url(app, "datadog-agent")
