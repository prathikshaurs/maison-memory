# As built: what changed since the design

`design.md` was written before the build. These are the differences and the assumptions worth knowing.

## Differences from the design

- **Notebook folders and names.** Notebooks sit in `notebooks/bronze`, `silver`, `gold`, `eval` and `orchestration`. Silver has an extra notebook for history and retention (nb_21b) and one for identity matching (nb_22).
- **File log.** `ctl_file_log` replaces the watermark table. Files are tracked by name and batch, which is what makes reruns safe.
- **Identity evaluation.** Matching accuracy is measured in a separate notebook (nb_29) against a truth file kept in `Files/eval`. The pipeline never reads that file.
- **Retention limits are illustrative.** Months per region and the Korea override are settings in nb_21b, chosen for the demo. They are not legal advice and not a claim about any real company.
- **Region views.** Visibility rules are enforced by Warehouse views per region, and the global profile table contains only fully consenting people.
- **Failure classes.** The driver uses five classes: processing, infrastructure, source, integration and unknown. The design's "orchestration" and "consumption" classes are covered by infrastructure and integration.

## Assumptions

- Whether a luxury house shares client profiles across regions is unknown. Public statements point both ways, so this project treats sharing as a consent-gated design choice, not a description of any real company.
- Name rarity (how many clients share a name) lowers the confidence of name-only matches. These go to a review list and are never linked automatically.
- Some repairs happen in a region other than the client's, with no sharing consent. This comes from how the generator creates data. In a real system it would be a finding to investigate.

## Not done or not tested

- Role enforcement with separate users.
- Vacuum schedule for Delta time travel.
- Automated refresh of the Power BI copies of the control tables.
- Performance at real data volumes. Tests used 5,000 people.
