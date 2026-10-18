import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  base: './',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    watch: {
      ignored: [
        '**/backend/**',
        '**/electron/**',
        '**/dist/**',
        '**/plugins_storage/**',
        '**/*.json',
        '**/*.log',
        '**/*.py',
        '**/*.pyc',
        '**/__pycache__/**'
      ]
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
});
