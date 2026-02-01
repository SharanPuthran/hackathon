import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '');

  return {
    server: {
      port: 3000,
      host: '0.0.0.0',
    },
    plugins: [react()],
    build: {
      // Output directory for production build
      outDir: 'dist',

      // Enable minification for production
      minify: mode === 'production' ? 'esbuild' : false,

      // Disable source maps for production (smaller bundle size)
      sourcemap: mode !== 'production',

      // Target modern browsers for optimal output
      target: 'es2015',

      // Configure chunk splitting for better caching
      rollupOptions: {
        output: {
          // Manual chunk splitting for vendor code
          manualChunks: {
            'vendor': ['react', 'react-dom'],
            'icons': ['lucide-react']
          },
          // Content hash in filenames for cache busting
          entryFileNames: 'assets/[name]-[hash].js',
          chunkFileNames: 'assets/[name]-[hash].js',
          assetFileNames: 'assets/[name]-[hash].[ext]'
        }
      },

      // Chunk size warnings
      chunkSizeWarningLimit: 1000,

      // Asset inline threshold (smaller assets inlined as base64)
      assetsInlineLimit: 4096
    },
    define: {
      // Properly handle environment variables with VITE_ prefix
      'import.meta.env.VITE_GEMINI_API_KEY': JSON.stringify(env.VITE_GEMINI_API_KEY || env.GEMINI_API_KEY),
      // Legacy support for process.env
      'process.env.API_KEY': JSON.stringify(env.VITE_GEMINI_API_KEY || env.GEMINI_API_KEY),
      'process.env.GEMINI_API_KEY': JSON.stringify(env.VITE_GEMINI_API_KEY || env.GEMINI_API_KEY)
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      }
    }
  };
});
