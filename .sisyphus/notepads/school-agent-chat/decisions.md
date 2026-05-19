## Task 11 - Page Integration

- **Clear button visibility**: Only show when there are user or assistant messages (not system-only). This prevents showing the clear button when only a system prompt has been loaded.
- **Error banner**: Uses `role="alert"` for accessibility and SVG icons from Heroicons (x-mark + exclamation-circle).
- **Auto-scroll**: Uses `useEffect` with `scrollIntoView({ behavior: "smooth" })` on a bottom ref, triggered by `messages` array changes.
- **Body height**: Changed from `min-h-full` to `h-full` to ensure the page's `h-full` children resolve their heights correctly in flex layouts.
