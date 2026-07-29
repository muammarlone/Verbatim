# Verbatim Design System

## Intent

The interface should feel calm, accountable, and legible in a security-conscious workplace. The primary workflow is obvious without a tour: choose a file, confirm authority, transcribe, review, export or delete.

## Tokens

- Ink: `#17201D`; soft ink: `#35433E`
- Paper: `#F4F2EC`; surface: `#FFFEF9`; muted surface: `#EBE9E1`
- Action: `#176B54`; action dark: `#0D533F`; action tint: `#DCEBE5`
- Warning: `#B66B1A`; destructive: `#A43C32`
- UI font: system `Inter/Aptos/Segoe UI`; display font: system `Georgia`
- Spacing: 4, 8, 12, 16, 24, 32, 48 px
- Radii: 8, 14, 20 px; minimum interactive target: 44 px

No font, icon, analytics, or layout asset is loaded from a CDN. The vendored Pretext engine is used only for local responsive text measurement. Native controls and semantic HTML remain the accessibility baseline.

## Components and states

- Persistent desktop navigation; off-canvas mobile navigation.
- Readiness chip and setup dialog.
- Drag/drop upload with file, language, and authority confirmation.
- Explicit queued, validating, extracting, transcribing, analyzing, complete, and failed states.
- Local media player, linked transcript rows, search, four analysis tabs, export menu, and destructive confirmation dialog.
- Empty, degraded, error, focus, reduced-motion, mobile, and dark color-scheme treatments.
