# Project development rules

## Rule #1 — Beginner-first UI/UX

Treat every user-facing change as a UI/UX task first, not only a coding task.

Assume a user may have **zero IT knowledge**. The normal workflow must therefore:

- Use very small, numbered, in-order baby steps.
- Always make the next action obvious.
- Use plain language before technical terms.
- Never require the user to understand Unity, packages, file numbers, hashes, QuickBMS, UABEA, paths, or similar implementation details for the normal path.
- Keep technical/advanced controls hidden behind progressive disclosure.
- Prefer safe defaults and automatic detection, with manual fallback only when needed.
- Explain errors as: what happened → what the user should click/do next.
- Prevent dangerous or contradictory actions instead of relying on warnings alone.
- Preserve the user’s previous state where possible and provide a clear recovery/restore path.
- Review every release at common Windows scaling/display sizes for clipping, overflow, disabled-state clarity, and readable text.

## Safety and correctness

This application temporarily modifies a BPSR client file. Safety beats convenience:

- Never overwrite the only verified clean backup based on a guess.
- Never restore an old backup over an unknown/newer live game file.
- Validate rebuilt data before replacing the live file.
- Keep writes transactional/atomic where practical and recover safely after interruption.
- Do not claim the method is guaranteed ban-safe.

## Release quality

Before release, compile/test the source, run the Windows frozen self-test, keep generated binaries out of source control, and publish checksums with release artifacts.
