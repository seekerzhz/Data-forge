# DataForge Docs Site

A production-ready static docs site built with Next.js + TypeScript, tailored for GitHub Pages.

## Local Development

```bash
cd docs-site
npm install
npm run dev
```

## Build & Export

```bash
npm run build
npm run export
```

Static output will be in `docs-site/out`.

## Deploy to GitHub Pages

1. Push this repository to GitHub.
2. Enable **GitHub Pages** with **GitHub Actions** as source.
3. Ensure default branch is `main`.
4. The workflow at `.github/workflows/deploy.yml` will build and deploy on push.

## Structure

- `src/pages`: docs pages (Homepage, Quick Start, Architecture, Prompt System, CLI, Roadmap)
- `src/components`: reusable UI components
- `src/styles/globals.css`: glassmorphism styling and animations
- `.github/workflows/deploy.yml`: GitHub Pages deployment
