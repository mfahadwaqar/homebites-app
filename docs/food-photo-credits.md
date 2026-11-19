# Dish images

All 50 dishes use **AI-generated illustrations** made for HomeBites on 17 and 18 November 2026 with Canva's image generator and Codex image generation. They are generated from text prompts (see `docs/image-prompts.md` and `docs/codex-image-prompts.md`) and are not photographs of real dishes or of any seller's food. Each country has its own visual style (Thailand: marble, Pakistan: dark slate, Bangladesh: warm wood and red checked cloth, Nepal: weathered wood and brass, India: light stone and steel thali).

- Files are bundled locally in `static/catalog/food/real/`, resized to at most 1200 px wide and saved as JPEG.
- The site labels them "AI-generated illustration" on cards and dish pages. A seller's own uploaded photo always replaces the illustration for that offer.
- Where the picture shows meat or fish, vegetarian and vegan offers do not use it; the `diet` field in `catalog/data/photo_sources.json` records which pictures are meat-free.
- Machine-readable record: `catalog/data/photo_sources.json`.
- The earlier Wikimedia Commons photographs (CC BY / CC BY-SA / public domain) are no longer used. They are not in the repository, so no attribution is required.
