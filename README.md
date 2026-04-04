# PlugPffft

PlugPffft is a tray-first Electron app for macOS and Windows. It watches for AC power events, shows a fart icon in the menu bar or system tray, and plays one custom-generated fart when the charger connects plus another when it disconnects.

## Why this structure

- The app is packaged as a normal desktop product, not a script.
- Installers are configured for macOS (`.dmg`, `.zip`) and Windows (`.exe`, portable).
- All visual and audio assets are generated locally so you are not shipping borrowed media.
- A static `website/` folder is included so the app can be downloaded from a storefront or simple static site.

## Local development

1. Install dependencies:

   ```bash
   npm install
   ```

2. Compile the app and launch it:

   ```bash
   npm run dev
   ```

3. Use the tray menu to run `Test fart` without reconnecting your charger.

## Packaging

Build macOS installers from macOS:

```bash
npm run dist:mac:arm64
```

Build Intel macOS installers from an Intel runner or CI:

```bash
npm run dist:mac:x64
```

Build Windows installers from Windows:

```bash
npm run dist:win
```

Or tag a release and let GitHub Actions build both through `.github/workflows/build-release.yml`.

## Make it downloadable from your website

1. Build your installers.
2. Copy the newest installer files into `website/downloads` with:

   ```bash
   npm run site:bundle
   ```

3. Deploy the `website/` folder to any static host.

The site automatically enables the download buttons when `website/downloads/manifest.json` exists.

## Selling considerations

- For macOS, add Apple code signing and notarization secrets before launch.
- For Windows, sign the `.exe` with your Authenticode certificate to reduce SmartScreen warnings.
- If you want checkout, host the `website/` folder behind Gumroad, Lemon Squeezy, Paddle, Stripe Payment Links, or your own storefront. The app itself is already packaged for direct download delivery.
- The asset generator is pure Python, so both macOS and Windows builders can regenerate the icon set and sound.
