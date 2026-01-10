# Vite Migration Plan for RackPlane OSS

## Overview
This document outlines the migration plan for converting the RackPlane OSS frontend from Create React App (CRA) to Vite. This is a stripped-down version of the main RackPlane repo, so the migration will be simpler but follow the same patterns.

## Current State Analysis

### Current Setup
- **Build Tool**: Create React App (`react-scripts` 5.0.1)
- **TypeScript**: 4.9.5
- **React**: 18.3.1
- **Test Framework**: Jest (via react-scripts)
- **Environment Variables**: `process.env.REACT_APP_*`
- **Build Output**: `build/` directory
- **HTML Entry**: `public/index.html`

### Key Differences from Main Repo
- Simpler structure (OSS version)
- Fewer premium features
- Same core dependencies (React, TypeScript, Tailwind)
- Same test files structure (App.test.tsx, LoginModal.test.tsx)

## Migration Phases

### Phase 1: Preparation & Safety ✅
**Goal**: Create a safe migration environment

**Tasks**:
1. ✅ Create a new branch: `vite-migration`
2. ✅ Review current dependencies in `package.json`
3. ✅ Document current environment variable usage
4. ✅ Identify all test files (2 found: App.test.tsx, LoginModal.test.tsx)
5. ✅ Backup current configuration files

**Files to Review**:
- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/public/index.html`
- `frontend/src/config/api.ts` (uses `process.env.REACT_APP_API_URL`)
- `frontend/src/components/LoginModal.tsx` (uses `process.env.REACT_APP_DEMO_MODE`, etc.)

---

### Phase 2: Dependency Updates 🔄
**Goal**: Replace CRA dependencies with Vite equivalents

**Tasks**:
1. **Uninstall CRA dependencies**:
   ```bash
   npm uninstall react-scripts
   ```

2. **Install Vite and plugins**:
   ```bash
   npm install --save-dev vite@^5.4.21 @vitejs/plugin-react@^4.7.0 vite-plugin-env-compatible@^2.0.1
   ```

3. **Install Vitest for testing**:
   ```bash
   npm install --save-dev vitest@^1.6.1 @vitest/ui@^1.6.1 happy-dom@^20.1.0
   ```

4. **Install testing dependencies** (if not already present):
   ```bash
   npm install --save-dev @testing-library/jest-dom@^6.9.1
   ```

5. **Update package.json scripts**:
   ```json
   {
     "scripts": {
       "start": "vite",
       "build": "tsc && vite build",
       "test": "vitest"
     }
   }
   ```

**Files to Modify**:
- `frontend/package.json`

---

### Phase 3: Configuration Files 📝
**Goal**: Create Vite configuration and update TypeScript configs

**Tasks**:
1. **Create `vite.config.ts`**:
   ```typescript
   import { defineConfig } from 'vite';
   import react from '@vitejs/plugin-react';
   import envCompatible from 'vite-plugin-env-compatible';

   export default defineConfig({
     plugins: [
       react(),
       envCompatible({
         mappedEnvPrefix: 'REACT_APP_',
       }),
     ],
     server: {
       port: 3000,
       host: true,
       proxy: {
         '/api': {
           target: 'http://localhost:8000',
           changeOrigin: true,
           secure: false,
         },
       },
     },
     build: {
       outDir: 'dist',
       sourcemap: true,
     },
     test: {
       globals: true,
       environment: 'happy-dom',
       setupFiles: './src/setupTests.ts',
       css: true,
     },
   });
   ```

2. **Create `tsconfig.node.json`**:
   ```json
   {
     "compilerOptions": {
       "composite": true,
       "esModuleInterop": true,
       "module": "esnext",
       "moduleResolution": "bundler",
       "skipLibCheck": true,
       "strict": true,
       "types": ["node"]
     },
     "include": ["vite.config.ts"]
   }
   ```

3. **Update `tsconfig.json`**:
   - Change `moduleResolution` from `"node"` to `"bundler"`
   - Change `jsx` from `"react"` to `"react-jsx"`
   - Add `types: ["node", "vitest/globals", "@testing-library/jest-dom"]`
   - Add `vite.config.ts` to `include`
   - Add reference to `tsconfig.node.json`
   - Set `noUnusedLocals: false` and `noUnusedParameters: false` (to allow build with warnings)

4. **Create `postcss.config.js`** (for Tailwind CSS):
   ```javascript
   module.exports = {
     plugins: {
       tailwindcss: {},
       autoprefixer: {},
     },
   };
   ```

5. **Install PostCSS dependencies**:
   ```bash
   npm install --save-dev autoprefixer
   ```

**Files to Create**:
- `frontend/vite.config.ts`
- `frontend/tsconfig.node.json`
- `frontend/postcss.config.js`

**Files to Modify**:
- `frontend/tsconfig.json`

---

### Phase 4: Codebase Adaptation 🔧
**Goal**: Update code to work with Vite

**Tasks**:
1. **Move `index.html`**:
   - Move `frontend/public/index.html` → `frontend/index.html`
   - Remove `%PUBLIC_URL%` references (if any)
   - Add Vite entry script: `<script type="module" src="/src/index.tsx"></script>`

2. **Create `src/vite-env.d.ts`**:
   ```typescript
   /// <reference types="vite/client" />
   /// <reference types="vite-plugin-env-compatible/client" />
   ```

3. **Create `src/setupTests.ts`**:
   ```typescript
   import '@testing-library/jest-dom/vitest';
   ```

4. **Update environment variable usage** (if needed):
   - `vite-plugin-env-compatible` handles `REACT_APP_*` → `import.meta.env.VITE_*` mapping
   - No code changes needed for `process.env.REACT_APP_*` usage
   - Files using env vars:
     - `src/config/api.ts`
     - `src/components/LoginModal.tsx`

5. **Update test files**:
   - **`src/App.test.tsx`**: Migrate from Jest to Vitest
     - Replace `jest` with `vi` for mocking
     - Replace `jest.mock` with `vi.mock`
     - Replace `jest.useFakeTimers` with `vi.useFakeTimers`
   
   - **`src/components/LoginModal.test.tsx`**: Migrate from Jest to Vitest
     - Same replacements as above
     - Wrap component in `BrowserRouter` if using `useNavigate`

**Files to Create**:
- `frontend/src/vite-env.d.ts`
- `frontend/src/setupTests.ts`

**Files to Modify**:
- `frontend/index.html` (moved from public/)
- `frontend/src/App.test.tsx`
- `frontend/src/components/LoginModal.test.tsx`

---

### Phase 5: Infrastructure 🐳
**Goal**: Update Docker and deployment configuration

**Tasks**:
1. **Update `Dockerfile`**:
   - Change build command from `npm run build` (which now uses Vite)
   - Ensure `dist` directory is served (not `build`)

2. **Update `docker-entrypoint.sh`**:
   - Change from serving `build/` to `dist/`
   - Update dependency check from `react-scripts` to `vite`
   - Update serve command: `serve -s dist -l 3000`

3. **Update `.gitignore`**:
   - Change `frontend/build/` to `frontend/dist/`
   - Add `.vite` (Vite cache directory)
   - Add `coverage` (for Vitest coverage reports)
   - Note: `.gitignore` already has `frontend/build/` on line 57, update to `frontend/dist/`

**Files to Modify**:
- `frontend/Dockerfile`
- `frontend/docker-entrypoint.sh`
- `.gitignore` (if exists in root)

---

### Phase 6: Verification ✅
**Goal**: Ensure everything works correctly

**Tasks**:
1. **Test development server**:
   ```bash
   cd frontend
   npm start
   ```
   - Verify app loads at `http://localhost:3000`
   - Check browser console for errors
   - Verify API proxy works

2. **Test production build**:
   ```bash
   npm run build
   ```
   - Verify `dist/` directory is created
   - Check for build errors/warnings
   - Verify source maps are generated

3. **Run tests**:
   ```bash
   npm test
   ```
   - Verify all tests pass
   - Check test coverage (if configured)

4. **Test Docker build**:
   ```bash
   docker build -t rackplane-oss-frontend ./frontend
   docker run -p 3000:3000 rackplane-oss-frontend
   ```
   - Verify container starts
   - Verify app is accessible

5. **Verify environment variables**:
   - Test with `REACT_APP_API_URL` set
   - Test with `REACT_APP_DEMO_MODE` set
   - Verify they work in both dev and production

**Test Checklist**:
- [ ] Development server starts
- [ ] Hot module replacement works
- [ ] Production build succeeds
- [ ] All tests pass
- [ ] Docker build works
- [ ] Environment variables work
- [ ] API proxy works
- [ ] Tailwind CSS styles load correctly
- [ ] No console errors

---

## Key Differences from Main Repo Migration

### Simpler Structure
- Fewer test files (2 vs many)
- No secondary application
- Simpler feature set

### Same Core Changes
- Same Vite configuration pattern
- Same test migration approach
- Same Docker updates
- Same environment variable handling

### Potential Issues to Watch For
1. **Node.js version**: Ensure Node 18+ (Vite 5.4.21 requires Node 20.19+ or 22.12+, but we're using 5.4.21 which should work with Node 18)
2. **TypeScript compatibility**: Current tsconfig uses `moduleResolution: "node"` - needs to change to `"bundler"`
3. **Test environment**: Need to ensure `happy-dom` works with all tests

---

## Rollback Plan

If issues arise:
1. Keep the `vite-migration` branch
2. Revert to main branch
3. Document issues encountered
4. Fix issues and retry

---

## Post-Migration Tasks

1. **Update documentation**:
   - Update README with new build commands
   - Update development setup instructions

2. **CI/CD updates** (if applicable):
   - Update build scripts in CI
   - Update test commands

3. **Performance monitoring**:
   - Compare build times (should be faster)
   - Compare bundle sizes
   - Monitor runtime performance

---

## Estimated Timeline

- **Phase 1**: 30 minutes (preparation)
- **Phase 2**: 15 minutes (dependencies)
- **Phase 3**: 30 minutes (configuration)
- **Phase 4**: 45 minutes (code adaptation)
- **Phase 5**: 20 minutes (infrastructure)
- **Phase 6**: 60 minutes (verification)

**Total**: ~3 hours

---

## Notes

- This is a simpler migration than the main repo (fewer files, simpler structure)
- Most patterns can be copied from the main repo migration
- Focus on ensuring OSS-specific features still work
- Test thoroughly before merging
