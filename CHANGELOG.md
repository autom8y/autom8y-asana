# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Bumped `autom8y-auth` dependency to `>=0.4.0` for SDK-provided `CredentialVaultAuthProvider`

### Deprecated

- `autom8_asana._defaults.vault_auth.CredentialVaultAuthProvider` is deprecated
  - Use `from autom8y_auth import CredentialVaultAuthProvider` instead
  - The deprecated module emits a `DeprecationWarning` on import
  - Will be removed in autom8_asana 0.6.0

### Migration Guide

Replace imports from the satellite module with the SDK:

```python
# Before (deprecated)
from autom8_asana._defaults.vault_auth import CredentialVaultAuthProvider

provider = CredentialVaultAuthProvider(
    credential_client=cred_client,
    business_id="...",
    identity_type="bot",
)

# After (SDK import)
from autom8y_auth import CredentialVaultAuthProvider

provider = CredentialVaultAuthProvider(
    credential_client=cred_client,
    business_id="...",
    provider="asana",  # Explicit provider parameter required
    identity_type="bot",
)
```

Key differences:
- Import from `autom8y_auth` instead of `autom8_asana._defaults.vault_auth`
- Add explicit `provider="asana"` parameter (the deprecated wrapper set this automatically)
