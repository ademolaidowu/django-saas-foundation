"""Direct unit tests for accounts selectors."""

from __future__ import annotations

import pytest

from accounts.constants import AccountStatus
from accounts.selectors import AccountSelectors, UserSelectors


@pytest.mark.django_db
class TestUserSelectors:
    def test_get_by_email_is_case_insensitive(self, user_factory):
        user_factory(email="mixed@example.com")
        assert UserSelectors.get_by_email("MIXED@EXAMPLE.COM") is not None
        assert UserSelectors.get_by_email("  mixed@example.com ") is not None

    def test_get_by_email_miss(self):
        assert UserSelectors.get_by_email("nobody@example.com") is None

    def test_email_exists(self, user_factory):
        user_factory(email="hi@example.com")
        assert UserSelectors.email_exists("HI@example.com") is True
        assert UserSelectors.email_exists("other@example.com") is False


@pytest.mark.django_db
class TestAccountSelectors:
    def test_list_for_user_default_active(self, user_factory, account_factory, two_orgs):
        alpha, bravo = two_orgs
        user = user_factory(email="x@example.com")
        account_factory(user=user, organization=alpha)
        account_factory(user=user, organization=bravo, status=AccountStatus.SUSPENDED)

        results = AccountSelectors.list_for_user(user)
        assert [a.organization.slug for a in results] == ["alpha"]

    def test_list_for_user_status_none_returns_all(self, user_factory, account_factory, two_orgs):
        alpha, bravo = two_orgs
        user = user_factory(email="x@example.com")
        account_factory(user=user, organization=alpha)
        account_factory(user=user, organization=bravo, status=AccountStatus.SUSPENDED)
        results = AccountSelectors.list_for_user(user, status=None)
        assert len(list(results)) == 2

    def test_get_primary_or_first_active_prefers_primary(self, user_factory, account_factory, two_orgs):
        alpha, bravo = two_orgs
        user = user_factory(email="x@example.com")
        account_factory(user=user, organization=alpha, is_primary=False)
        primary = account_factory(user=user, organization=bravo, is_primary=True)
        assert AccountSelectors.get_primary_or_first_active(user) == primary

    def test_get_primary_or_first_active_falls_back_to_earliest(self, user_factory, account_factory, two_orgs):
        alpha, bravo = two_orgs
        user = user_factory(email="x@example.com")
        first = account_factory(user=user, organization=alpha, is_primary=False)
        account_factory(user=user, organization=bravo, is_primary=False)
        # Earliest joined_at wins (alpha was created first)
        assert AccountSelectors.get_primary_or_first_active(user) == first

    def test_get_by_user_and_organization_hit(self, user_factory, account_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        account = account_factory(user=user, organization=alpha)
        assert AccountSelectors.get_by_user_and_organization(user, alpha) == account

    def test_get_by_user_and_organization_miss_on_wrong_org(self, user_factory, account_factory, two_orgs):
        alpha, bravo = two_orgs
        user = user_factory(email="x@example.com")
        account_factory(user=user, organization=alpha)
        assert AccountSelectors.get_by_user_and_organization(user, bravo) is None

    def test_get_by_user_and_organization_skips_suspended(self, user_factory, account_factory, two_orgs):
        alpha, _ = two_orgs
        user = user_factory(email="x@example.com")
        account_factory(user=user, organization=alpha, status=AccountStatus.SUSPENDED)
        assert AccountSelectors.get_by_user_and_organization(user, alpha) is None
