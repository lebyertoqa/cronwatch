"""Tests for cronwatch.job_routing."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from unittest.mock import MagicMock

import pytest

from cronwatch.job_routing import JobRouter, RoutingRule, build_router


@dataclass
class _FakeJob:
    name: str = "test-job"
    tags: List[str] = field(default_factory=list)
    labels: Dict[str, str] = field(default_factory=dict)


def _alerter(name: str):
    m = MagicMock()
    m.__repr__ = lambda s: f"<Alerter {name}>"
    return m


# ---------------------------------------------------------------------------
# RoutingRule.matches
# ---------------------------------------------------------------------------

def test_rule_matches_by_job_name():
    rule = RoutingRule(channel="ops", job_name="backup")
    assert rule.matches(_FakeJob(name="backup"))
    assert not rule.matches(_FakeJob(name="other"))


def test_rule_matches_by_tag():
    rule = RoutingRule(channel="critical", tag="pagerduty")
    assert rule.matches(_FakeJob(tags=["pagerduty", "infra"]))
    assert not rule.matches(_FakeJob(tags=["infra"]))


def test_rule_matches_by_label_key_only():
    rule = RoutingRule(channel="team-a", label_key="team")
    assert rule.matches(_FakeJob(labels={"team": "alpha"}))
    assert not rule.matches(_FakeJob(labels={"owner": "bob"}))


def test_rule_matches_by_label_key_and_value():
    rule = RoutingRule(channel="team-b", label_key="team", label_value="beta")
    assert rule.matches(_FakeJob(labels={"team": "beta"}))
    assert not rule.matches(_FakeJob(labels={"team": "alpha"}))


def test_rule_without_selector_never_matches():
    rule = RoutingRule(channel="nowhere")
    assert not rule.matches(_FakeJob())


# ---------------------------------------------------------------------------
# JobRouter.channels_for
# ---------------------------------------------------------------------------

def test_no_matching_rule_returns_default_channel():
    router = JobRouter(rules=[], default_channel="default")
    assert router.channels_for(_FakeJob()) == ["default"]


def test_single_matching_rule_returns_its_channel():
    rule = RoutingRule(channel="ops", tag="ops")
    router = JobRouter(rules=[rule], default_channel="default")
    job = _FakeJob(tags=["ops"])
    assert router.channels_for(job) == ["ops"]


def test_multiple_matching_rules_all_returned():
    rules = [
        RoutingRule(channel="ops", tag="ops"),
        RoutingRule(channel="security", tag="sec"),
    ]
    router = JobRouter(rules=rules, default_channel="default")
    job = _FakeJob(tags=["ops", "sec"])
    channels = router.channels_for(job)
    assert "ops" in channels
    assert "security" in channels


# ---------------------------------------------------------------------------
# JobRouter.alerters_for
# ---------------------------------------------------------------------------

def test_alerters_for_resolves_channels():
    ops = _alerter("ops")
    rule = RoutingRule(channel="ops", tag="ops")
    router = JobRouter(rules=[rule], default_channel="default", channels={"ops": ops})
    alerters = router.alerters_for(_FakeJob(tags=["ops"]))
    assert alerters == [ops]


def test_alerters_for_skips_unknown_channel():
    rule = RoutingRule(channel="ghost", tag="x")
    router = JobRouter(rules=[rule], default_channel="default", channels={})
    assert router.alerters_for(_FakeJob(tags=["x"])) == []


# ---------------------------------------------------------------------------
# build_router
# ---------------------------------------------------------------------------

def test_build_router_from_dicts():
    ops = _alerter("ops")
    cfg = [{"channel": "ops", "tag": "ops"}]
    router = build_router(cfg, channels={"ops": ops})
    assert len(router.rules) == 1
    assert router.rules[0].channel == "ops"
    assert router.rules[0].tag == "ops"


def test_build_router_default_channel_passed_through():
    router = build_router([], channels={}, default_channel="fallback")
    assert router.default_channel == "fallback"
    assert router.channels_for(_FakeJob()) == ["fallback"]
