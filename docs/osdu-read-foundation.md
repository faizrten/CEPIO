# OSDU versioned-read foundation

Status: development-only, not registered in a hosted runtime; no live qualification.

`cepio.integrations.osdu_read.OSDURecordReader` implements the shared OSDU
Storage v2 exact-version GET prerequisite for Wellbore and RAFS evidence.
It reuses `ExternalRecordReference`; it is not a DDMS bulk-data adapter.

The trusted host configures the HTTPS endpoint and partition, authorizes every
read, and supplies a source token scoped to the calling actor. Do not expose the
reader, token provider, endpoint configuration or raw records as agent tools.
Source authorization remains enforced by OSDU. A partition is a source boundary,
not proof of CEPIO tenant authorization. No automatic runtime registration occurs.

Reads require exact record id, full OSDU kind, version and partition. Short kind
patterns from the experimental mapping are not valid resolved references.
Responses must match identity/version and include data, ACL and legal objects.
ACL/legal objects are preserved, not independently interpreted as permission grants.
The client blocks redirects, bounds response size, uses timeouts, has no cache or
write interface, and sanitizes source HTTP errors. Host endpoint allowlisting and
network restrictions remain deployment responsibilities.

## Qualification stages

1. Shared exact-version record reads (this change): mocked positive/negative tests.
2. Provider-specific Wellbore log and RAFS sample/analysis hydration using verified
   provider API/schema versions, unit/time mappings and bounded payload access.
3. Bind hydrated evidence to the existing petrophysics input contract and run the
   frozen core/log question without changing its expected reasoning.
4. Authorized live proof: source endpoint, partition, host identity configuration,
   known authorized record IDs/versions and negative-access test records.
5. Review source-use rights, tenant isolation, dependency resilience and promotion
   evidence before registering a production binding.

No new dependencies, infrastructure, paid inference or customer data are added.
The OSDU capability remains unqualified for production. Rollback removes this
optional reader with no database migration; source unavailability must block,
never substitute synthetic evidence. Source records remain authoritative in OSDU.

Reference API: https://osdu.pages.opengroup.org/platform/system/storage/api/

Validation: `python -m pytest -q tests/test_osdu_read.py tests/test_domain_bindings.py tests/test_osdu_subsurface_boundary.py`
