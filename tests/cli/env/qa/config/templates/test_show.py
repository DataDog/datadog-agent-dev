# SPDX-FileCopyrightText: 2025-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import pytest

from dda.utils.process import EnvVars

pytestmark = [pytest.mark.usefixtures("private_storage")]


@pytest.fixture(scope="module", autouse=True)
def _terminal_width():
    with EnvVars({"COLUMNS": "200"}):
        yield


def test_all_no_templates(dda, helpers, temp_dir):
    templates_dir = temp_dir / "data" / "env" / "config" / "templates"
    assert not templates_dir.exists()

    with EnvVars({"DD_API_KEY": "foo"}):
        result = dda("env", "qa", "config", "templates", "show")

    result.check(
        exit_code=0,
        output=helpers.dedent(
            """
            ┌─────────┬──────────────────────────────────┐
            │ default │ ┌────────┬─────────────────────┐ │
            │         │ │ Config │ ┌─────────┬───────┐ │ │
            │         │ │        │ │ api_key │ ***** │ │ │
            │         │ │        │ └─────────┴───────┘ │ │
            │         │ └────────┴─────────────────────┘ │
            └─────────┴──────────────────────────────────┘
            """
        ),
    )
    assert templates_dir.is_dir()
    existing_templates = [p.name for p in templates_dir.iterdir()]
    assert existing_templates == ["default"]


def test_all_existing_non_default(dda, helpers, temp_dir):
    templates_dir = temp_dir / "data" / "env" / "config" / "templates"
    template_dir = templates_dir / "foo"
    template_dir.ensure_dir()
    (template_dir / "datadog.yaml").write_text(
        helpers.dedent(
            """
            app_key: foo
            bar: baz
            """
        )
    )

    with EnvVars({"DD_API_KEY": "foo"}):
        result = dda("env", "qa", "config", "templates", "show")

    result.check(
        exit_code=0,
        output=helpers.dedent(
            """
            ┌─────┬──────────────────────────────────┐
            │ foo │ ┌────────┬─────────────────────┐ │
            │     │ │ Config │ ┌─────────┬───────┐ │ │
            │     │ │        │ │ api_key │ ***** │ │ │
            │     │ │        │ │ app_key │ ***** │ │ │
            │     │ │        │ │ bar     │ baz   │ │ │
            │     │ │        │ └─────────┴───────┘ │ │
            │     │ └────────┴─────────────────────┘ │
            └─────┴──────────────────────────────────┘
            """
        ),
    )

    assert templates_dir.is_dir()
    existing_templates = [p.name for p in templates_dir.iterdir()]
    assert existing_templates == ["foo"]


def test_selection_not_found(dda, helpers):
    result = dda("env", "qa", "config", "templates", "show", "foo")
    result.check(
        exit_code=1,
        output=helpers.dedent(
            """
            Template not found: foo
            """
        ),
    )


def test_selection_empty(dda, helpers, temp_dir):
    templates_dir = temp_dir / "data" / "env" / "config" / "templates"
    template_dir = templates_dir / "foo"
    template_dir.ensure_dir()
    (template_dir / "datadog.yaml").touch()

    result = dda("env", "qa", "config", "templates", "show", "foo")
    result.check(
        exit_code=0,
        output=helpers.dedent(
            """
            ┌────────┬────┐
            │ Config │ {} │
            └────────┴────┘
            """
        ),
    )

    assert templates_dir.is_dir()
    existing_templates = [p.name for p in templates_dir.iterdir()]
    assert existing_templates == ["foo"]


def test_org_inheritance(dda, helpers, temp_dir, config_file):
    config_file.data["orgs"]["foo"] = {
        "api_key": "bar",
        "app_key": "baz",
        "site": "datadoghq.com",
        "dd_url": "https://app.datadoghq.com",
        "logs_url": "agent-intake.logs.datadoghq.com:10516",
    }
    config_file.save()

    templates_dir = temp_dir / "data" / "env" / "config" / "templates"
    template_dir = templates_dir / "foo"
    template_dir.ensure_dir()
    (template_dir / "datadog.yaml").write_text(
        helpers.dedent(
            """
            inherit_org: foo
            site: datadog.com
            """
        )
    )

    result = dda("env", "qa", "config", "templates", "show", "foo")
    result.check(
        exit_code=0,
        output=helpers.dedent(
            """
            ┌────────┬───────────────────────────────────────────────────────────────────────────┐
            │ Config │ ┌─────────────┬─────────────────────────────────────────────────────────┐ │
            │        │ │ api_key     │ *****                                                   │ │
            │        │ │ app_key     │ *****                                                   │ │
            │        │ │ dd_url      │ https://app.datadoghq.com                               │ │
            │        │ │ logs_config │ ┌─────────────┬───────────────────────────────────────┐ │ │
            │        │ │             │ │ logs_dd_url │ agent-intake.logs.datadoghq.com:10516 │ │ │
            │        │ │             │ └─────────────┴───────────────────────────────────────┘ │ │
            │        │ │ site        │ datadog.com                                             │ │
            │        │ └─────────────┴─────────────────────────────────────────────────────────┘ │
            └────────┴───────────────────────────────────────────────────────────────────────────┘
            """
        ),
    )

    assert templates_dir.is_dir()
    existing_templates = [p.name for p in templates_dir.iterdir()]
    assert existing_templates == ["foo"]


def test_integrations(dda, helpers, temp_dir):
    templates_dir = temp_dir / "data" / "env" / "config" / "templates"
    template_dir = templates_dir / "test"
    template_dir.ensure_dir()
    (template_dir / "datadog.yaml").write_text(
        helpers.dedent(
            """
            api_key: foo
            bar: baz
            """
        )
    )
    integrations_dir = template_dir / "integrations"
    integrations_dir.ensure_dir()
    integration_no_files_dir = integrations_dir / "no_files"
    integration_no_files_dir.ensure_dir()
    (integration_no_files_dir / "config.yaml.example").touch()
    integration_misconfigured_dir = integrations_dir / "misconfigured"
    integration_misconfigured_dir.ensure_dir()
    (integration_misconfigured_dir / "config.yaml").touch()
    integration_only_instances_dir = integrations_dir / "only_instances"
    integration_only_instances_dir.ensure_dir()
    (integration_only_instances_dir / "config.yaml").write_text(
        helpers.dedent(
            """
            instances:
            - name: foo
            - name: bar
            """
        )
    )
    integration_only_logs_dir = integrations_dir / "only_logs"
    integration_only_logs_dir.ensure_dir()
    (integration_only_logs_dir / "config.yaml").write_text(
        helpers.dedent(
            """
            logs:
            - service: foo
              source: foo
            """
        )
    )
    integration_only_ad_dir = integrations_dir / "only_ad"
    integration_only_ad_dir.ensure_dir()
    (integration_only_ad_dir / "auto_conf.yaml").write_text(
        helpers.dedent(
            """
            ad_identifiers:
            - foo
            - bar
            instances:
            - name: foo
            """
        )
    )
    integration_ad_misconfigured_dir = integrations_dir / "ad_misconfigured"
    integration_ad_misconfigured_dir.ensure_dir()
    (integration_ad_misconfigured_dir / "auto_conf.yaml").write_text(
        helpers.dedent(
            """
            ad_identifiers:
            - foo
            """
        )
    )
    integration_multiple_files_dir = integrations_dir / "multiple_files"
    integration_multiple_files_dir.ensure_dir()
    (integration_multiple_files_dir / "config1.yaml").write_text(
        helpers.dedent(
            """
            instances:
            - name: foo
            """
        )
    )
    (integration_multiple_files_dir / "config2.yaml").touch()
    integration_config_with_ad_dir = integrations_dir / "config_with_ad"
    integration_config_with_ad_dir.ensure_dir()
    (integration_config_with_ad_dir / "config.yaml").write_text(
        helpers.dedent(
            """
            instances:
            - name: foo
            """
        )
    )
    (integration_config_with_ad_dir / "auto_conf.yaml").write_text(
        helpers.dedent(
            """
            ad_identifiers:
            - foo
            - bar
            instances:
            - name: foo
            """
        )
    )

    result = dda("env", "qa", "config", "templates", "show", "test")
    result.check(
        exit_code=0,
        output=helpers.dedent(
            """
            ┌──────────────┬──────────────────────────────────────────────────────────────────────────┐
            │ Config       │ ┌─────────┬───────┐                                                      │
            │              │ │ api_key │ ***** │                                                      │
            │              │ │ bar     │ baz   │                                                      │
            │              │ └─────────┴───────┘                                                      │
            │ Integrations │ ┌──────────────────┬───────────────────────────────────────────────────┐ │
            │              │ │ ad_misconfigured │ ┌───────────────┬─────────────────┐               │ │
            │              │ │                  │ │ Autodiscovery │ <misconfigured> │               │ │
            │              │ │                  │ └───────────────┴─────────────────┘               │ │
            │              │ │ config_with_ad   │ ┌───────────────┬───────────────────────────────┐ │ │
            │              │ │                  │ │ Autodiscovery │ ┌─────────────┬─────────────┐ │ │ │
            │              │ │                  │ │               │ │ Identifiers │ ┌───┬─────┐ │ │ │ │
            │              │ │                  │ │               │ │             │ │ 1 │ foo │ │ │ │ │
            │              │ │                  │ │               │ │             │ │ 2 │ bar │ │ │ │ │
            │              │ │                  │ │               │ │             │ └───┴─────┘ │ │ │ │
            │              │ │                  │ │               │ │ Instances   │ 1           │ │ │ │
            │              │ │                  │ │               │ └─────────────┴─────────────┘ │ │ │
            │              │ │                  │ │ Config        │ ┌───────────┬───┐             │ │ │
            │              │ │                  │ │               │ │ Instances │ 1 │             │ │ │
            │              │ │                  │ │               │ └───────────┴───┘             │ │ │
            │              │ │                  │ └───────────────┴───────────────────────────────┘ │ │
            │              │ │ misconfigured    │ ┌────────┬─────────────────┐                      │ │
            │              │ │                  │ │ Config │ <misconfigured> │                      │ │
            │              │ │                  │ └────────┴─────────────────┘                      │ │
            │              │ │ multiple_files   │ ┌──────────────┬───────────────────────────┐      │ │
            │              │ │                  │ │ Config files │ ┌───┬───────────────────┐ │      │ │
            │              │ │                  │ │              │ │ 1 │ ┌───────────┬───┐ │ │      │ │
            │              │ │                  │ │              │ │   │ │ Instances │ 1 │ │ │      │ │
            │              │ │                  │ │              │ │   │ └───────────┴───┘ │ │      │ │
            │              │ │                  │ │              │ │ 2 │ <misconfigured>   │ │      │ │
            │              │ │                  │ │              │ └───┴───────────────────┘ │      │ │
            │              │ │                  │ └──────────────┴───────────────────────────┘      │ │
            │              │ │ only_ad          │ ┌───────────────┬───────────────────────────────┐ │ │
            │              │ │                  │ │ Autodiscovery │ ┌─────────────┬─────────────┐ │ │ │
            │              │ │                  │ │               │ │ Identifiers │ ┌───┬─────┐ │ │ │ │
            │              │ │                  │ │               │ │             │ │ 1 │ foo │ │ │ │ │
            │              │ │                  │ │               │ │             │ │ 2 │ bar │ │ │ │ │
            │              │ │                  │ │               │ │             │ └───┴─────┘ │ │ │ │
            │              │ │                  │ │               │ │ Instances   │ 1           │ │ │ │
            │              │ │                  │ │               │ └─────────────┴─────────────┘ │ │ │
            │              │ │                  │ └───────────────┴───────────────────────────────┘ │ │
            │              │ │ only_instances   │ ┌────────┬───────────────────┐                    │ │
            │              │ │                  │ │ Config │ ┌───────────┬───┐ │                    │ │
            │              │ │                  │ │        │ │ Instances │ 2 │ │                    │ │
            │              │ │                  │ │        │ └───────────┴───┘ │                    │ │
            │              │ │                  │ └────────┴───────────────────┘                    │ │
            │              │ │ only_logs        │ ┌────────┬──────────────┐                         │ │
            │              │ │                  │ │ Config │ ┌──────┬───┐ │                         │ │
            │              │ │                  │ │        │ │ Logs │ 1 │ │                         │ │
            │              │ │                  │ │        │ └──────┴───┘ │                         │ │
            │              │ │                  │ └────────┴──────────────┘                         │ │
            │              │ └──────────────────┴───────────────────────────────────────────────────┘ │
            └──────────────┴──────────────────────────────────────────────────────────────────────────┘
            """
        ),
    )
