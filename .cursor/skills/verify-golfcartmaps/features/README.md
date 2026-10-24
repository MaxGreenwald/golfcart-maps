# Feature map — Golf Cart Maps (web)

Index of user-facing features this skill can drive. Each file is written for an agent that has never seen the app.

| Feature | File | Harness entry |
|---------|------|---------------|
| Town / region map pages | [town-map-pages.md](town-map-pages.md) | `test_town_pages`, `test_city_chip`, `test_regions` |
| Route search | [route-search.md](route-search.md) | `test_ui`, `test_vehicle`, `test_road_labels` (route assert) |
| Road popups & legal labels | [road-popups-legal-labels.md](road-popups-legal-labels.md) | `test_road_labels`, `test_safety_caution`, `test_vehicle` |
| Offline + service worker | [offline-service-worker.md](offline-service-worker.md) | `test_sw` |
| Vehicle mode (golf cart / LSV) | [vehicle-mode.md](vehicle-mode.md) | `test_vehicle` |
