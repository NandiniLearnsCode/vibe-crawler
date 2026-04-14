# Matter Intelligence Layer Prototype

Matter-centric prototype for a Harvey next-generation legal workflow surface focused on M&A due diligence.

## Run locally

```bash
npm install
npm run dev
```

Build check:

```bash
npm run build
```

## Prototype story

This app demonstrates why persistent matter context is the missing product layer between disconnected AI tools:

- all AI activity is linked to a matter
- workstreams roll up into matter-level risk synthesis
- internal and client-safe views are intentionally separated
- closed matters generate firm-scoped institutional learning outputs

## Key flows

1. Matters list -> open **Project Falcon Acquisition**
2. Matter dashboard -> open **IP workstream**
3. Matter dashboard -> open **risk detail**
4. Matter dashboard -> switch to **client-facing shared space**
5. Matter dashboard -> open **close & learn**

## Architecture

- `src/types/matter.ts`: typed matter-centric schema
- `src/data/mockMatterData.ts`: realistic linked M&A mock data
- `src/components`: reusable product panels
- `src/pages`: route-level prototype screens
- `src/App.tsx`: navigation and route wiring
