# HomeBites completion week 9 to 15 November 2026

Target: working feature-complete version Friday 13 November, fixes and submission handover by Sunday 15 November (Bangkok time).

## Current execution checklist

- [x] Inspect existing design pass and confirm the calorie placeholder is not functional storage.
- [x] Add optional, validated seller-specific kcal, serving size, source and review fields.
- [x] Display complete reviewed nutrition on dish details and catalogue cards, with an honest missing state.
- [x] Invalidate old nutrition after recipe ingredient changes; preserve seller values on seed reruns.
- [x] Verify migration and nutrition/seller/catalogue regression checks against PostgreSQL (74 tests passed; 50 listings and 1 existing order preserved).
- [x] Full PostgreSQL regression suite: 184/184 passed on 9 November 2026; system check, migration check and migration-drift check passed.
- [ ] Source and visually verify 50 real dish photographs with original source and reuse licence records.
- [ ] Populate 50 reviewed recipe-specific nutrition estimates with serving sizes and sources. Never derive values from a dish name, cuisine, photograph or an unquantified ingredient list.
- [ ] Finish consistent mobile/desktop layouts across discovery, kitchen, cart, checkout and account screens.
- [ ] Verify customer, seller and administrator journeys, including failure and unavailable states.
- [ ] Freeze features Friday; fix blocking defects and rehearse Saturday.
- [ ] Refresh screenshots and submission documents; verify local setup and backup Sunday.

## Scope and content rules

First photo batch implemented: PK01 Chicken Biryani and PK04 Chicken Karahi (2/50). See `food-photo-credits.md`. Desktop review confirms the real biryani photograph and attribution render correctly. The remaining 48 dish images and all 50 sourced nutrition estimates remain pending.

Keep five countries and 50 dishes, standard orders and pre-orders, pickup and distance-based delivery. No live payment/courier integration or public deployment.

Use Google/search as discovery, not as a licence. Verify the original photograph's source, author and reuse terms. Bundle permitted image assets locally; do not hotlink. Record modifications and attribution. Never substitute a different dish for an unavailable photograph. Seller uploads remain higher priority than representative catalogue images.

Nutrition entry is optional while researched values remain pending. All four fields form one set. A recipe change clears the old set, requiring a newly reviewed estimate. Values entered only in automated tests must not be seeded into the demonstration database.

## Migration safety

The nutrition migration expands existing listings with nullable/empty fields; no dishes, orders or ingredients are replaced. Before migrating record listing and order counts, migrate and compare those counts afterward. Reversing to catalog migration 0002 drops the new nutrition fields and loses any newly entered nutrition; export those values before considering rollback. Do not reverse an applied migration as part of routine verification.
