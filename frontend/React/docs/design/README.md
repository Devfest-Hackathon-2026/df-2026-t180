# UI design notes

Status: v3. Visitor screens: map and search, with pin details and the regional guide in one sheet over the map. Resident and admin screens follow.
Figma: [DevFest Local Guide — UI Design](https://www.figma.com/design/ctPaGb5iH6U3wCt648823f). It holds flows, wireframes, components, screens, motion, and `06 — Evolution`.
How the design got here: [evolution/README.md](evolution/README.md).

| Home                                         | Pin selected (half sheet)                           | Regional guide (full sheet)                 |
| -------------------------------------------- | --------------------------------------------------- | ------------------------------------------- |
| ![Home](screenshots/home-mobile-default.jpg) | ![Half sheet](screenshots/home-mobile-selected.jpg) | ![Full sheet](screenshots/guide-mobile.jpg) |

| Desktop, pin selected (English)                            | Desktop, guide panel (English)                  |
| ---------------------------------------------------------- | ----------------------------------------------- |
| ![Desktop selected](screenshots/home-desktop-selected.jpg) | ![Desktop guide](screenshots/guide-desktop.jpg) |

## Direction

Google's own visual language, as used on the DevFest GDGoC Japan Hackathon site: light grey ground, white surfaces with 2px ink outlines, Google blue, red, yellow and green, pill shapes, small monospace tags and bold Google Sans headlines. Hover states are playful: outlined things lift with a hard offset shadow, arrows turn, dots hop.

The home screen is only a search bar and the map. Nothing opens a new page: as in Google Maps, a pin raises a sheet over the map. Half height shows the statement; dragging up (or the arrow) expands the same sheet into the regional guide, a readable document split into Manners, Transport and Living tabs. Dragging down or × returns to the map.

| Source                       | Pattern used                                                                                              | Not used                                               |
| ---------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| Google colour sheet          | Blue, red, yellow, green and their light tints; light grey and near-black                                 | Deep and orange tones beyond status use                |
| Google Sans Flex             | Latin UI and display type, with Google Sans Code for tags and dates                                       | Shipping the 3.9 MB TTF; Fontsource woff2 is used      |
| DevFest hackathon site video | Outlined pills and cards, round black arrow buttons, mono tags, JA/EN pill switch, hover lifts, dot trios | Countdown, marquee strip, photography, Google branding |
| Team review (2026-11-08)     | Simpler home, statement-only preview, icon action, tabs in the guide, clearer language switch, mascot     | —                                                      |

## Team review applied

| Feedback                                              | Change                                                                                                             |
| ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| SpotPreview should not show the reason field          | Preview shows category tag, place name and the statement only                                                      |
| Open the regional guide as a web page after a pin     | The guide opens in the same sheet over the map (v3.1). `/regions/:id` links still work and redirect into the sheet |
| "View Details" was unclear                            | One round arrow button (`aria-label` "ガイドを開く" / "Open guide")                                                |
| No category chips on home                             | Removed. Home is search + map                                                                                      |
| Switch categories with tabs inside the guide          | Manners / 交通 Transport / 暮らし Living tabs, sticky under the hero, with counts                                  |
| EN/JP switch hard to understand; reachable everywhere | JA \| EN segmented switch with a sliding thumb, top-right on every screen; keeps screen and state                  |
| Minimise text; no tagline                             | No tagline or helper copy; states are one line                                                                     |
| Mascot                                                | One-head-tall lime sprout with a tour flag; appears on the guide hero, holding and empty states                    |

## Wireframes

Mobile, the primary layout:

```
Home                              Pin · half sheet                  Guide · full sheet (same sheet)
+-------------------------------+ +-------------------------------+ +-------------------------------+
| ( Search an area )   (JA|EN)  | | ( Search an area )   (JA|EN)  | | ( Search an area )   (JA|EN)  |
|                               | |                               | |                               |
|            MAP                | |        (● Place name)         | | Region name          (mascot) |
|     (●)       (●)             | |    (●)                        | | 10 rules · Updated 2026.11.07 |
|          (●)                  | | [Sample]                 (◎)  | | (Manners 4)(Transport 3)(Living 3)
|   (●)            (●)          | | +---------------------------+ | | +---------------------------+ |
| [Sample]                 (◎)  | | | [MANNERS]             ×   | | | | 01  Statement            | |
|                               | | | Place name                | | | |     2026.11.06 (⌖ place) | |
|                               | | | Statement only.      (↗)  | | | +---------------------------+ |
|    ( Explore | Residents )    | | +---------------------------+ | | | 02  Statement            | |
+-------------------------------+ |    ( Explore | Residents )    | | +---------------------------+ |
                                  +-------------------------------+ +-------------------------------+
```

Desktop, 900px and wider: one outlined header pill across the top (brand, search, Explore | Residents, JA | EN). The sheet becomes a left panel, as in Google Maps on the web: a card at half height, full height when expanded. Location sits bottom-right.

## Components

| Component        | Purpose                                                | Variants and states                          | Accessibility                                                                              |
| ---------------- | ------------------------------------------------------ | -------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `AppNav`         | Visitor and resident areas                             | current item                                 | `aria-current="page"`, 44px items                                                          |
| `BrandMark`      | Product name, home link                                | —                                            | `h1` on home; dots are decorative                                                          |
| `SearchBar`      | Find an area                                           | focus                                        | labelled input in a search landmark                                                        |
| `LanguageSwitch` | JA/EN from any screen                                  | ja, en                                       | nav landmark; options named 日本語 / English, 44px                                         |
| `MapMarker`      | Opens a pin                                            | category × default, hover, selected, dimmed  | link with the full name, 44px target                                                       |
| `MapPlaceholder` | Stands in for Google Maps                              | ready, loading                               | hidden from assistive tech                                                                 |
| `LocationButton` | Current-location access                                | default, denied                              | named button                                                                               |
| `PlaceSheet`     | Pin detail and regional guide over the map             | half, full; dragging (phones)                | section labelled by the title; handle is a button with `aria-expanded`; × and Escape close |
| `Tag`            | Small mono label                                       | plain, manners, transport, living, highlight | text label                                                                                 |
| `PillLink`       | Primary or back action                                 | highlight, plain                             | text link                                                                                  |
| `StateCard`      | Empty, error and holding states                        | plain, warning                               | `role="status"`                                                                            |
| `Mascot`         | Character                                              | guide, puzzled                               | `aria-hidden`                                                                              |
| `GuideContent`   | Region intro, category tabs and rules inside the sheet | category tab; focused rule                   | tabs are a nav with `aria-current`, 48px; rules are an ordered list                        |
| Rule card        | One published statement                                | default, hover, focused                      | ordered list; pin chip named "Show on map: place", 44px hit area                           |

## Review states

Every state is reachable by URL, so reviewers need no backend.

| State                      | URL                                                                         |
| -------------------------- | --------------------------------------------------------------------------- |
| Home                       | `/`                                                                         |
| English                    | `/?lang=en`                                                                 |
| Pin selected (half sheet)  | `/?spot=rule_001`                                                           |
| Search results             | `/?q=緑`                                                                    |
| Empty search               | `/?q=tokyo` or `/?state=empty`                                              |
| Location denied            | `/?state=denied`                                                            |
| Loading                    | `/?state=loading`                                                           |
| Error                      | `/?state=error`                                                             |
| Full sheet, tab and focus  | `/?spot=rule_005&sheet=full&tab=transport`                                  |
| Guide from search (no pin) | `/?region=midorigawa&sheet=full` (old `/regions/midorigawa` redirects here) |
| Holding page               | `/contribute`                                                               |

## Data shape

Sample rules follow the team's public JSON format in `docs/詳細設計.md`: `id`, `region`, `statement` (ja/en), `updated_at`. The UI adds `category` (for the tabs) and an optional `pin` (map position). The reason field residents may enter is not shown to visitors. These two additions need agreeing with the backend.

## Tokens

Source of truth: `src/styles/tokens.css`. Figma variables in the `Tokens` collection carry the same values and `var(--…)` code syntax.

- Colour: Google palette (`--g-blue`, `--g-red`, `--g-yellow`, `--g-green` and light tints), light grey ground `#f1f3f4`, ink `#202124`, soft ink `#5f6368`. Categories: Manners red, Transport blue, Living green. Yellow marks what is selected or primary. Lime `#c6f36d` is the mascot only.
- Type: Google Sans Flex (Latin), Noto Sans JP (Japanese), Google Sans Code (tags, dates, counts). All via Fontsource variable woff2 with unicode-range subsets; about 60 KB of gzipped CSS.
- Shape: 2px ink outlines; radius 12, 20, 28, full; hard shadow `4px 4px 0` ink.
- Spacing: 4, 8, 12, 16, 20, 24, 32, 40.

## Numerals

Outlined numbers (rule numbers and any future step numbers) must show one clean outline per glyph. Some Google Sans Flex glyphs, such as 4, are built from overlapping shapes, so a plain text stroke draws lines inside them.

- Code: `-webkit-text-stroke: 3px` with `paint-order: stroke fill`, filled with the card colour. The fill hides the inner lines and leaves a 1.5px outline. Hover and focus fill with the category colour.
- Figma: two stacked layers in a `Number` frame, `Outline` (3px stroke) under `Fill` (card colour).

## Motion

| Trigger                       | Elements          | Behaviour                                                                                                                                                                | Duration                                |
| ----------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------- |
| Select marker                 | Map canvas        | Pans to centre the pin above the preview                                                                                                                                 | 480ms                                   |
| Select marker                 | Marker            | Drops in, turns yellow, name expands, hard shadow                                                                                                                        | 320ms spring                            |
| Tap a pin                     | Place sheet       | Rises to half height; desktop card rises 24px                                                                                                                            | 380ms                                   |
| Hover marker                  | Pin               | Hops 4px with an ink shadow underneath                                                                                                                                   | 200ms spring                            |
| Hover pill, card, search      | Outlined surfaces | Lifts 2px with a 4px hard offset shadow                                                                                                                                  | 200ms                                   |
| Hover arrow action            | Round ink arrow   | Turns 45° to point forward                                                                                                                                               | 320ms spring                            |
| Switch language               | Thumb             | Slides between JA and EN; screen stays put                                                                                                                               | 320ms spring                            |
| Switch area (探す / 地元の方) | AppNav thumb      | Slides from the previous item; labels swap colour; page content switches instantly. Overshoot scaled to the same ~4px as the language switch so it stays inside the pill | 320ms, cubic-bezier(0.34, 1.3, 0.64, 1) |
| Hover rule card               | Outlined numeral  | Fills with the category colour                                                                                                                                           | 200ms                                   |
| Drag sheet / tap arrow        | Place sheet       | Follows the finger, then snaps to full, half or closed by distance and speed; guide rules rise 40ms apart                                                                | 380ms                                   |
| Hover brand                   | Four dots         | Hop in sequence, 60ms apart                                                                                                                                              | 480ms                                   |
| Idle                          | Mascot            | Bob, blink, flag sway; sprout tilts on hover                                                                                                                             | 3.2s / 4.6s / 2.4s                      |
| Loading                       | Four dots         | Hop in sequence                                                                                                                                                          | 900ms loop                              |

All motion stops under `prefers-reduced-motion: reduce`.

## Decisions

| Decision                                         | Why                                                                                     | Rejected                                        |
| ------------------------------------------------ | --------------------------------------------------------------------------------------- | ----------------------------------------------- |
| Google palette and outlined "sticker" surfaces   | Fits a Google event, reads as designed rather than templated, playful on hover          | v2 monochrome with a lime accent                |
| Category colours on pins, tags and tabs          | One colour per category links the map, preview and guide                                | Monochrome pins                                 |
| Home is search + map only                        | Team review: keep the first screen simple                                               | Category chips in the header                    |
| Guide in a sheet over the map, as in Google Maps | Fewer page changes; the map and context stay put; drag is familiar to Google Maps users | A separate guide page (v3.0)                    |
| Statement only in the preview                    | Public data has a statement; the reason is resident input for admins                    | Note / Why / Checked rows                       |
| Arrow icon instead of "詳しく見る"               | One obvious action; the label lives in `aria-label`                                     | A text button that did not say where it goes    |
| Segmented JA \| EN switch, top-right everywhere  | Both options visible, current one obvious                                               | A single toggle showing only the other language |
| Own brand mark (four dots)                       | Google colours without using Google or GDG logos                                        | Any Google logo                                 |
| State held in the URL                            | Keeps this PR free of application logic and makes states reviewable                     | Component state                                 |
| Fictional sample town                            | Avoids inventing rules for a real place; demo region is Sakai                           | Rules for a real municipality                   |

## Open questions

- Product name: 「マナビ」 / "Manabi" is a placeholder, used for the brand, the map wordmark (bottom-left, level with the location button, white halo like the Google Maps mark) and the page title.
- Mascot name.
- Whether the backend can return `category` and a map position per rule.
- Swap the sample town for Sakai data once the API returns real rules.

## Mocked

Search matching, location, map and all rules are static sample data. No control connects to a service. `/contribute` shows a holding page until the resident form is built.
