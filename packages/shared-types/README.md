# shared-types

The contract both apps implement.

- `permissions.json` — the role × intent permission matrix, the intent list and the
  supported language codes. This is the **source of truth**.
- `index.ts` — TypeScript types plus an advisory `mayAttempt()` helper for the UI.

The Python backend keeps its own typed copy in `apps/xyz-ai/app/auth/permissions.py`
so that the authorization path has no runtime file dependency. `tests/test_shared_contract.py`
asserts the two agree, so they cannot drift silently.
