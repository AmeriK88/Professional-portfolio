// Dummy Service Worker to satisfy Pi Browser
self.addEventListener('install', () => {
  self.skipWaiting();
});

self.addEventListener('activate', () => {
  // Nothing special, just activate
});

self.addEventListener('fetch', event => {
  // Pass through all requests without caching
});
