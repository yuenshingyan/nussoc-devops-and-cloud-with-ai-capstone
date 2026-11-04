# Final presentation refresh

The presentation now contains **10 landscape slides** and the design document **4 A4 pages**
covering actual automatic delivery, failed-test/security blocks, controlled rollback, GKE
observability and the advisory-only AI proposal. Earlier claims that cloud execution was
missing have been replaced with evidence-backed results and explicit remaining limitations.

Both PDFs were rendered from local HTML in an isolated Chrome profile. DOM overflow checks
passed for every page; native PDFKit checks confirmed the actual PDF page counts. An initial
design-page overflow was corrected and its diagnostic retained. PDF links use public repository
URLs; local-file/home-directory links were checked absent.

Actual authenticated Jenkins UI captures show retained normal build #39, successful delivery
#3, the deliberate failing test #37 and security-block run #38. No DOM text was fabricated or
replaced. Credentials were supplied through stdin, not command arguments or screenshots; the
isolated browser profile was removed. The first observer expected an outdated dashboard label;
that observation failure was corrected without changing Jenkins or replaying any job.

[Checksummed UI captures and rendering records](final-presentation/) ·
[Presentation](../../submission/presentation.pdf) · [Design](../../submission/design-document.pdf).

Existing divergent work on the older presentation branch was preserved. The reviewed follow-up
branch is `task-07/step-03-presentation-final`. The timed video is a separate deliverable;
silent-format acceptance remains unconfirmed.
