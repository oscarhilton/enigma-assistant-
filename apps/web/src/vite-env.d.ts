/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE?: string;
  readonly VITE_BUILD_COMMIT?: string;
  readonly VITE_ENIGMA_MODE?: string;
  readonly VITE_ENIGMA_API_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
