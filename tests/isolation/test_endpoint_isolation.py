"""
Parametrised cross-tenant isolation across every tenant-scoped endpoint.

Every tenant resource has to answer the same three questions:
1. Can the wrong-org client *retrieve* a Bravo row? → 404 (ADR 005).
2. Can it *mutate* (PATCH/DELETE) a Bravo row? → 404.
3. Does its list exclude Bravo rows? → yes.

One parametrisation drives all of them. Adding a new tenant resource is one
new `EndpointSpec` in `conftest.ENDPOINT_SPECS`.
"""

from __future__ import annotations

import pytest

from .conftest import ENDPOINT_SPECS


def _detail_url(spec, resource) -> str:
    return spec.detail_url_tpl.format(public_id=resource.public_id)


@pytest.mark.django_db
@pytest.mark.parametrize("spec", ENDPOINT_SPECS, ids=lambda s: s.name)
class TestCrossTenantRetrieveReturns404:
    def test_retrieve(self, spec, two_orgs_with_rbac):
        if not spec.has_retrieve:
            pytest.skip(f"{spec.name} has no retrieve endpoint")
        client = two_orgs_with_rbac["client"]
        resource = two_orgs_with_rbac["bravo_fixtures"][spec.bravo_key]
        response = client.get(_detail_url(spec, resource))
        assert response.status_code == 404, (
            f"{spec.name} retrieve leaked a cross-tenant row: got {response.status_code}"
        )


@pytest.mark.django_db
@pytest.mark.parametrize("spec", ENDPOINT_SPECS, ids=lambda s: s.name)
class TestCrossTenantMutationReturns404:
    def test_update(self, spec, two_orgs_with_rbac):
        if not spec.has_update:
            pytest.skip(f"{spec.name} has no update endpoint")
        client = two_orgs_with_rbac["client"]
        resource = two_orgs_with_rbac["bravo_fixtures"][spec.bravo_key]
        response = client.patch(_detail_url(spec, resource), spec.update_payload, format="json")
        assert response.status_code == 404

    def test_delete(self, spec, two_orgs_with_rbac):
        if not spec.has_delete:
            pytest.skip(f"{spec.name} has no delete endpoint")
        client = two_orgs_with_rbac["client"]
        resource = two_orgs_with_rbac["bravo_fixtures"][spec.bravo_key]
        response = client.delete(_detail_url(spec, resource))
        assert response.status_code == 404

    def test_history(self, spec, two_orgs_with_rbac):
        if not spec.has_history:
            pytest.skip(f"{spec.name} has no history endpoint")
        client = two_orgs_with_rbac["client"]
        resource = two_orgs_with_rbac["bravo_fixtures"][spec.bravo_key]
        url = _detail_url(spec, resource).rstrip("/") + "/history/"
        response = client.get(url)
        assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize("spec", ENDPOINT_SPECS, ids=lambda s: s.name)
class TestCrossTenantListExclusion:
    def test_list(self, spec, two_orgs_with_rbac):
        if not spec.has_list:
            pytest.skip(f"{spec.name} has no list endpoint")
        client = two_orgs_with_rbac["client"]
        resource = two_orgs_with_rbac["bravo_fixtures"][spec.bravo_key]

        response = client.get(spec.list_url)
        assert response.status_code == 200

        payload = response.json()["data"]
        ids = {item["id"] for item in payload}
        assert str(resource.public_id) not in ids, f"{spec.name} list leaked a cross-tenant row {resource.public_id}"
