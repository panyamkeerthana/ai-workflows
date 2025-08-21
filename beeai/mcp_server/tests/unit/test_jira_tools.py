import os
import datetime

import pytest
import requests
from flexmock import flexmock

from jira_tools import Severity, PreliminaryTesting, get_jira_details, set_jira_fields, add_jira_comment


@pytest.fixture(autouse=True)
def mocked_env():
    flexmock(os).should_receive("getenv").with_args("JIRA_URL").and_return("http://jira")
    flexmock(os).should_receive("getenv").with_args("JIRA_TOKEN").and_return("12345")
    flexmock(os).should_receive("getenv").with_args(key="DRY_RUN", default="False").and_return("false")


def test_get_jira_details():
    issue_key = "RHEL-12345"
    issue_data = {
        "key": issue_key,
        "id": "12345",
        "fields": {"summary": "Test issue"},
        "comment": {"comments": [{"body": "Test comment"}], "total": 1},
    }
    remote_links_data = [
        {
            "id": 10000,
            "object": {
                "url": "https://github.com/example/repo/pull/123",
                "title": "Fix issue RHEL-12345"
            }
        }
    ]

    def get(url, params=None, headers=None):
        if url.endswith(f"rest/api/2/issue/{issue_key}"):
            assert params.get("expand") == "comments"
            return flexmock(json=lambda: issue_data, raise_for_status=lambda: None)
        elif url.endswith(f"rest/api/2/issue/{issue_key}/remotelink"):
            return flexmock(json=lambda: remote_links_data, raise_for_status=lambda: None)
        else:
            raise AssertionError(f"Unexpected URL: {url}")

    flexmock(requests).should_receive("get").replace_with(get)

    result = get_jira_details(issue_key)
    expected_result = issue_data.copy()
    expected_result["remote_links"] = remote_links_data

    assert result == expected_result


@pytest.mark.parametrize(
    "args, current_fields, expected_fields",
    [
        (
            dict(fix_versions=["rhel-1.2.3"]),
            {"fields": {"fixVersions": []}},
            {"fixVersions": [{"name": "rhel-1.2.3"}]},
        ),
        (
            dict(severity=Severity.LOW),
            {"fields": {"customfield_12316142": {"value": None}}},
            {"customfield_12316142": {"value": Severity.LOW.value}},
        ),
        (
            dict(target_end=datetime.date(2024, 12, 31)),
            {"fields": {"customfield_12313942": {"value": None}}},
            {"customfield_12313942": "2024-12-31"},
        ),
        (
            dict(fix_versions=["rhel-1.2.3"], severity=Severity.CRITICAL),
            {"fields": {"fixVersions": [], "customfield_12316142": {"value": None}}},
            {"fixVersions": [{"name": "rhel-1.2.3"}], "customfield_12316142": {"value": Severity.CRITICAL.value}},
        ),
    ],
)
def test_set_jira_fields(args, current_fields, expected_fields):
    issue_key = "RHEL-12345"

    def get(url, headers=None):
        if url.endswith(f"rest/api/2/issue/{issue_key}"):
            return flexmock(json=lambda: current_fields, raise_for_status=lambda: None)
        else:
            raise AssertionError(f"Unexpected URL: {url}")

    def put(url, json, headers):
        assert url.endswith(f"rest/api/2/issue/{issue_key}")
        assert json.get("fields") == expected_fields
        return flexmock(raise_for_status=lambda: None)

    flexmock(requests).should_receive("get").replace_with(get)
    flexmock(requests).should_receive("put").replace_with(put)
    result = set_jira_fields(issue_key, **args)
    assert result.startswith("Successfully")


@pytest.mark.parametrize(
    "private", [False, True],
)
def test_add_jira_comment(private):
    issue_key = "RHEL-12345"
    comment = "Test comment"

    def post(url, json, headers):
        assert url.endswith(f"rest/api/2/issue/{issue_key}/comment")
        assert json.get("body") == comment
        if private:
            assert json.get("visibility") == {"type": "group", "value": "Red Hat Employee"}
        return flexmock(raise_for_status=lambda: None)

    flexmock(requests).should_receive("post").replace_with(post)
    result = add_jira_comment(issue_key, comment, private)
    assert result.startswith("Successfully")
