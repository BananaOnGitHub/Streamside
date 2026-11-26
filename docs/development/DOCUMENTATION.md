# Documentation maintenance

Streamside's documentation describes the maintained implementation and preserves the evidence behind it. Each document has a defined purpose, so readers can find a complete explanation without reconciling several competing versions.

## Document ownership

| Document | Owns |
| --- | --- |
| [README](../../README.md) | Current branch and development entry points. |
| [Development guides](../README.md#native-development-documentation) | Reusable build, testing, packaging and investigation methods. |
| [Investigations](../investigations/README.md) | Technical findings, per-build records and sanitized validation evidence. |
| [Previous implementation](https://github.com/BananaOnGitHub/Streamside/tree/eb4d30f761e75921913451293b76a92d39eaa2d5/docs) | Historical release guides, changelog and earlier investigations. |
| [Documentation index](../README.md) | Navigation between the current guides and historical records. |

Put each substantial explanation in its owning document and link to it from other layers. The README can summarize the branch without duplicating implementation records. Historical records provide evidence for a current explanation; they do not define current behavior.

## When to update

During active development, prioritize implementation, testing, and recording findings. Keep active investigation, implementation-trial, and per-build notes in `docs/investigations/`, not `docs/development/`. Records and commits should explain what changed, why, what was tested, what failed, and what remains unresolved. Include source revisions, build labels, and artifact identities when they are needed to interpret the result.

Do not continually rewrite public-facing guides around experiments or unfinished behavior. At feature freeze, review the completed implementation and update all affected documentation before publication. Finalize the release's changelog entry against the changes since the previous published version.

Correct inaccurate security or compatibility information immediately, even during active development. If support or safety is uncertain, narrow the claim and state the known limit while further investigation continues.

## Preserve development evidence

Never silently erase failed experiments, superseded approaches, or unique technical findings. At feature freeze, carry maintained implementation details into the owning feature documents. Preserve remaining investigation evidence in Git history or an identified archive revision when closing the work. Update links to the retained records.

Historical records should retain their original scope and outcome. Add a clearly separated correction or supersession note when later evidence changes the conclusion. Identify the relevant build, Twitch donor, source revision, successor document, and validation limits where available.

Keep recorded artifact hashes attached to the artifacts they originally described. A replacement asset gets its own identity and explanation. Do not rewrite an earlier result as though the replacement or corrected approach had always existed.

When moving records, update the investigation or archive index and affected links. Preserve distinct branch closure records and make their source revisions traceable.

## Writing standards

Write in a natural maintainer voice, with direct descriptions of behavior, decisions, and evidence. Keep references to prompts, conversations, and drafting instructions out of repository documentation.

Separate current behavior from proposals and historical observations. Explain limitations where they affect use or maintenance. Prefer source and test links over repeated explanations. Use anonymized channel and account references in device findings. Keep identifying profile URLs, handles and any raw evidence that contains them in the local archive.

Compatibility and validation claims must have supporting evidence. Distinguish host tests, donor inspection, package verification, CI, and device testing. Record failures and skips accurately; a skipped check is not a pass. Successful packaging does not establish device compatibility, and clean playback alone does not establish ad suppression.

Use exact version and build identities when the distinction matters. Do not infer a Twitch package's supported iOS floor from Streamside's framework metadata, or extend one tested configuration to other devices, signers, or jailbreak installations without evidence.

## Mechanical validation

Run `make docs-check` when changing documentation, moving linked files, or updating current version metadata. The separate Documentation CI check validates local links, anchors, assets, and the native framework metadata. It includes retained investigation Markdown and does not generate or rewrite documentation. [Testing](TESTING.md#documentation-integrity) defines its rules and exclusions.

Passing this check does not establish implementation accuracy, compatibility, device acceptance, feature readiness, or changelog completeness. Public documentation is still reconciled with completed work at feature freeze.

## Review at feature freeze

Compare affected documents with the final source, tests, candidate artifacts, and supported Twitch versions. Check that:

- Feature descriptions match the retained implementation, including fallback behavior and known limits.
- Test and validation claims match actual results and identify their scope.
- Version labels, artifact identities, installation instructions, and compatibility information agree.
- The changelog describes changes since the previous published release and uses the correct publication status.
- Development findings have been incorporated or preserved with traceable references.
- Links, source paths, archive navigation, attribution, and documentation included in packages remain correct.

Resolve contradictions before publication. Document unresolved limits explicitly rather than treating missing evidence as successful validation.

## Updating this guide

When the documentation structure changes, update this policy in the same change. Revise the ownership table, links, and timing or review guidance affected by the new structure. Update the documentation index and other references alongside it.

For a split or merged guide, assign each subject a clear owner and preserve unique content before removing the old location. Explain the change in the commit so the new organization remains traceable. Keep this guide aligned with the maintained structure without turning it into a record of every past layout.
