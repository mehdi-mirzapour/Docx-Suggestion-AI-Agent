import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    // Inline all assets for single HTML file
    assetsInlineLimit: 100000000,
    rollupOptions: {
      output: {
        // Generate single HTML file with inlined JS/CSS
        inlineDynamicImports: true,
        manualChunks: undefined,
      },
    },
  },
})
