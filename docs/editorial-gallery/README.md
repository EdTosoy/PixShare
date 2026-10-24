# Explore screenshot index

Captured with real local FastAPI/PostgreSQL records in Chromium. See the [refinement report](../EDITORIAL_GALLERY_REFINEMENT.md) for setup, fixture limitations and verification.

## Three-image gallery and states

Landscape, portrait and square are present together in every Explore capture. Each viewport has light and dark evidence for all five states.

| Layout | State | Before | After |
| --- | --- | --- | --- |
| desktop, light | explore | [Before](before/desktop-light-explore.jpg) | [After](after/desktop-light-explore.jpg) |
| desktop, light | filtered | [Before](before/desktop-light-filtered.jpg) | [After](after/desktop-light-filtered.jpg) |
| desktop, light | empty | [Before](before/desktop-light-empty.jpg) | [After](after/desktop-light-empty.jpg) |
| desktop, light | loading | [Before](before/desktop-light-loading.jpg) | [After](after/desktop-light-loading.jpg) |
| desktop, light | error | [Before](before/desktop-light-error.jpg) | [After](after/desktop-light-error.jpg) |
| desktop, dark | explore | [Before](before/desktop-dark-explore.jpg) | [After](after/desktop-dark-explore.jpg) |
| desktop, dark | filtered | [Before](before/desktop-dark-filtered.jpg) | [After](after/desktop-dark-filtered.jpg) |
| desktop, dark | empty | [Before](before/desktop-dark-empty.jpg) | [After](after/desktop-dark-empty.jpg) |
| desktop, dark | loading | [Before](before/desktop-dark-loading.jpg) | [After](after/desktop-dark-loading.jpg) |
| desktop, dark | error | [Before](before/desktop-dark-error.jpg) | [After](after/desktop-dark-error.jpg) |
| tablet, light | explore | [Before](before/tablet-light-explore.jpg) | [After](after/tablet-light-explore.jpg) |
| tablet, light | filtered | [Before](before/tablet-light-filtered.jpg) | [After](after/tablet-light-filtered.jpg) |
| tablet, light | empty | [Before](before/tablet-light-empty.jpg) | [After](after/tablet-light-empty.jpg) |
| tablet, light | loading | [Before](before/tablet-light-loading.jpg) | [After](after/tablet-light-loading.jpg) |
| tablet, light | error | [Before](before/tablet-light-error.jpg) | [After](after/tablet-light-error.jpg) |
| tablet, dark | explore | [Before](before/tablet-dark-explore.jpg) | [After](after/tablet-dark-explore.jpg) |
| tablet, dark | filtered | [Before](before/tablet-dark-filtered.jpg) | [After](after/tablet-dark-filtered.jpg) |
| tablet, dark | empty | [Before](before/tablet-dark-empty.jpg) | [After](after/tablet-dark-empty.jpg) |
| tablet, dark | loading | [Before](before/tablet-dark-loading.jpg) | [After](after/tablet-dark-loading.jpg) |
| tablet, dark | error | [Before](before/tablet-dark-error.jpg) | [After](after/tablet-dark-error.jpg) |
| mobile, light | explore | [Before](before/mobile-light-explore.jpg) | [After](after/mobile-light-explore.jpg) |
| mobile, light | filtered | [Before](before/mobile-light-filtered.jpg) | [After](after/mobile-light-filtered.jpg) |
| mobile, light | empty | [Before](before/mobile-light-empty.jpg) | [After](after/mobile-light-empty.jpg) |
| mobile, light | loading | [Before](before/mobile-light-loading.jpg) | [After](after/mobile-light-loading.jpg) |
| mobile, light | error | [Before](before/mobile-light-error.jpg) | [After](after/mobile-light-error.jpg) |
| mobile, dark | explore | [Before](before/mobile-dark-explore.jpg) | [After](after/mobile-dark-explore.jpg) |
| mobile, dark | filtered | [Before](before/mobile-dark-filtered.jpg) | [After](after/mobile-dark-filtered.jpg) |
| mobile, dark | empty | [Before](before/mobile-dark-empty.jpg) | [After](after/mobile-dark-empty.jpg) |
| mobile, dark | loading | [Before](before/mobile-dark-loading.jpg) | [After](after/mobile-dark-loading.jpg) |
| mobile, dark | error | [Before](before/mobile-dark-error.jpg) | [After](after/mobile-dark-error.jpg) |

## Larger real-data collection

Twelve additional isolated copies provide 15 records, two pages, long captions and a legacy original. These are repeated real photos, not extra unique photographs.

| Layout | Before | After |
| --- | --- | --- |
| desktop, light | [Before](before-dense/desktop-light-explore.jpg) | [After](after-dense/desktop-light-explore.jpg) |
| desktop, dark | [Before](before-dense/desktop-dark-explore.jpg) | [After](after-dense/desktop-dark-explore.jpg) |
| tablet, light | [Before](before-dense/tablet-light-explore.jpg) | [After](after-dense/tablet-light-explore.jpg) |
| tablet, dark | [Before](before-dense/tablet-dark-explore.jpg) | [After](after-dense/tablet-dark-explore.jpg) |
| mobile, light | [Before](before-dense/mobile-light-explore.jpg) | [After](after-dense/mobile-light-explore.jpg) |
| mobile, dark | [Before](before-dense/mobile-dark-explore.jpg) | [After](after-dense/mobile-dark-explore.jpg) |
| Desktop page two, light | [Before](before-dense/desktop-light-page-two.jpg) | [After](after-dense/desktop-light-page-two.jpg) |
| Desktop page two, dark | [Before](before-dense/desktop-dark-page-two.jpg) | [After](after-dense/desktop-dark-page-two.jpg) |

## Layout alternatives, identical data

The alternatives are temporary CSS probes against the unchanged build. The shipped rows retain flat DOM and visual reading order.

| Dataset/layout | Original uniform grid | Native-ratio grid | Column masonry | Selected rows |
| --- | --- | --- | --- | --- |
| 3 records, desktop | [Original](before/desktop-light-explore.jpg) | [Grid](before/desktop-light-alternative-natural-grid.jpg) | [Columns](before/desktop-light-alternative-columns.jpg) | [Rows](after/desktop-light-explore.jpg) |
| 3 records, tablet | [Original](before/tablet-light-explore.jpg) | [Grid](before/tablet-light-alternative-natural-grid.jpg) | [Columns](before/tablet-light-alternative-columns.jpg) | [Rows](after/tablet-light-explore.jpg) |
| 15 records, desktop | [Original](before-dense/desktop-light-explore.jpg) | [Grid](before-dense/desktop-light-alternative-natural-grid.jpg) | [Columns](before-dense/desktop-light-alternative-columns.jpg) | [Rows](after-dense/desktop-light-explore.jpg) |
| 15 records, tablet | [Original](before-dense/tablet-light-explore.jpg) | [Grid](before-dense/tablet-light-alternative-natural-grid.jpg) | [Columns](before-dense/tablet-light-alternative-columns.jpg) | [Rows](after-dense/tablet-light-explore.jpg) |

## Keyboard and measurements

[Visible mobile keyboard focus](after-dense/mobile-light-focus.jpg).

[Before measurements](before/metrics.json), [after measurements](after/metrics.json), [larger before](before-dense/metrics.json), [larger after](after-dense/metrics.json), [contrast and inconclusive selectors](accessibility-review.json), [verification record](verification.json).
