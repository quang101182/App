# Loto - Online Bingo Game

## Project Overview

Real-time multiplayer Bingo/Loto web application using Firebase Realtime Database for synchronization. Three standalone HTML files, zero build step.

## Architecture

```
loto-config.html   → Game setup: players, cards, session creation
loto-croupier.html → Host/Dealer: draw numbers, monitor players, verify cards
loto-joueur.html   → Player: mark numbers, track progress, win detection
```

### Tech Stack
- **HTML/CSS/JS** — Single-file architecture, no bundler
- **Tailwind CSS** via CDN (`cdn.tailwindcss.com`)
- **Firebase Realtime Database** (SDK 10.8.0 via ES modules)
- **Google Fonts** — Quicksand
- **Web Speech API** — Number announcements
- **Web Animation API** — Confetti effects

### Firebase Structure
```
loto/{sessionId}/
  ├── players/[]     → { id, name, cards }
  ├── cards/[]       → { id, playerId, playerName, cardNumber, grid[3][9], marked[27] }
  ├── drawing/       → { drawn[], available[], spinning: bool }
  └── chat/[]        → { name, text, ts }
```

Database URL: `https://weighty-country-411214-default-rtdb.firebaseio.com`

## Key Conventions

### Card Generation (`genCard()`)
- 3 rows x 9 columns grid
- 5 numbers per row (randomly positioned)
- Column ranges: col 0 → 1-9, col 1 → 10-19, ..., col 8 → 80-90
- No duplicate numbers within a card

### Ball Colors by Range
Numbers are color-coded in both croupier and player views:
- 1-9: Red, 10-19: Orange, 20-29: Yellow, 30-39: Green
- 40-49: Cyan, 50-59: Blue, 60-69: Indigo, 70-79: Purple, 80-90: Pink

### Multilingual Support
11 languages: FR, EN, ES, DE, IT, PT, RU, TR, AR, ZH, JA
- Config uses `loto_lang` localStorage key
- Croupier/Player use `lotoLang` localStorage key
- Arabic has RTL support via `document.body.dir`

### Theme
- Light/Dark mode via `dark` class on `<body>`
- Persisted in `loto_theme` (config) or `lotoTheme` (croupier/player) localStorage keys

### Real-time Sync
- Firebase `onValue()` for game state
- Firebase `onChildAdded()` with `limitToLast(50)` for chat
- Sync status indicator: green (synced), yellow (saving), red (error)

## Development Notes

### Security
- Chat messages are escaped with `esc()` function (prevents XSS)
- Firebase credentials are in the client code (this is a Realtime Database public app)

### Croupier Features
- Space bar keyboard shortcut to draw
- Verification mode: green=correct mark, red=wrong mark, amber=missed number
- Option to reset card markings when resetting the game
- Sound toggle with text-to-speech

### Player Features
- Auto-login via `sessionStorage` (per session ID)
- Haptic feedback via `navigator.vibrate()` on mobile
- Ripple effect on cell tap
- Win detection triggers confetti overlay
- Win shown only once per card via `winShown` map

### Testing
No automated tests. Manual testing:
1. Open `loto-config.html`, add players, start session
2. Open croupier link in one tab, player link in another
3. Draw numbers and verify real-time sync
4. Mark numbers on player side, verify on croupier monitor
5. Test verification mode on croupier
