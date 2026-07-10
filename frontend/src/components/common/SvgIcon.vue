<script setup lang="ts">
defineProps<{
  name: string
  size?: number | string
}>()

const sizePx = (val?: number | string): string => {
  if (!val) return '20'
  if (typeof val === 'number') return `${val}px`
  return val
}
</script>

<template>
  <!-- Snowflake -->
  <svg v-if="name === 'snowflake'"
    :width="sizePx(size)" :height="sizePx(size)"
    viewBox="0 0 40 40" fill="none"
    xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="sg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#60a5fa"/>
        <stop offset="100%" stop-color="#06b6d4"/>
      </linearGradient>
    </defs>
    <g stroke="url(#sg)" stroke-width="1.8" stroke-linecap="round">
      <line x1="20" y1="2" x2="20" y2="38"/>
      <line x1="5" y1="11" x2="35" y2="29"/>
      <line x1="5" y1="29" x2="35" y2="11"/>
      <line x1="20" y1="8" x2="16" y2="15"/><line x1="20" y1="8" x2="24" y2="15"/>
      <line x1="20" y1="32" x2="16" y2="25"/><line x1="20" y1="32" x2="24" y2="25"/>
      <line x1="12" y1="14" x2="17" y2="17"/>
      <line x1="23" y1="23" x2="28" y2="26"/>
    </g>
    <circle cx="20" cy="20" r="2.5" fill="url(#sg)"/>
  </svg>

  <!-- Flask (Design Lab) -->
  <svg v-else-if="name === 'flask'"
    :width="sizePx(size)" :height="sizePx(size)"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M9 3h6"/>
    <path d="M10 3v6.5L4 19c-.6.9 0 2 1 2h14c1 0 1.6-1.1 1-2l-6-9.5V3"/>
    <path d="M8 14h8"/>
    <path d="M10 10h4"/>
  </svg>

  <!-- Book (Knowledge Base) -->
  <svg v-else-if="name === 'book'"
    :width="sizePx(size)" :height="sizePx(size)"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
    <line x1="8" y1="7" x2="16" y2="7"/>
    <line x1="8" y1="11" x2="14" y2="11"/>
  </svg>

  <!-- History -->
  <svg v-else-if="name === 'history'"
    :width="sizePx(size)" :height="sizePx(size)"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <polyline points="12 6 12 12 16 14"/>
  </svg>

  <!-- Brain (Skills) -->
  <svg v-else-if="name === 'brain'"
    :width="sizePx(size)" :height="sizePx(size)"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M9.5 2A2.5 2.5 0 0112 4.5v15a2.5 2.5 0 01-4.96.44 2.5 2.5 0 01-2.65-2.64A2.5 2.5 0 015 12.5a2.5 2.5 0 01-.6-4.8A2.5 2.5 0 019.5 2z"/>
    <path d="M14.5 2A2.5 2.5 0 0012 4.5v15a2.5 2.5 0 004.96.44 2.5 2.5 0 012.65-2.64A2.5 2.5 0 0019 12.5a2.5 2.5 0 01.6-4.8A2.5 2.5 0 0014.5 2z"/>
  </svg>

  <!-- Chart (Results) -->
  <svg v-else-if="name === 'chart'"
    :width="sizePx(size)" :height="sizePx(size)"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <line x1="18" y1="20" x2="18" y2="10"/>
    <line x1="12" y1="20" x2="12" y2="4"/>
    <line x1="6" y1="20" x2="6" y2="14"/>
    <line x1="2" y1="20" x2="22" y2="20"/>
  </svg>

  <!-- Play -->
  <svg v-else-if="name === 'play'"
    :width="sizePx(size)" :height="sizePx(size)"
    viewBox="0 0 24 24" fill="currentColor" stroke="none">
    <polygon points="6,3 20,12 6,21"/>
  </svg>

  <!-- Ice crystal -->
  <svg v-else-if="name === 'ice'"
    :width="sizePx(size)" :height="sizePx(size)"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.6" stroke-linecap="round">
    <path d="M12 2v20M4.93 4.93l14.14 14.14M2 12h20M4.93 19.07L19.07 4.93"/>
    <circle cx="12" cy="12" r="3"/>
  </svg>

  <!-- DNA -->
  <svg v-else-if="name === 'dna'"
    :width="sizePx(size)" :height="sizePx(size)"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M4 6c0 3 4 5 8 5s8-2 8-5"/>
    <path d="M4 18c0-3 4-5 8-5s8 2 8 5"/>
    <path d="M4 6v12"/>
    <path d="M20 6v12"/>
    <path d="M12 1v5"/>
    <path d="M12 18v5"/>
  </svg>

  <!-- Target -->
  <svg v-else-if="name === 'target'"
    :width="sizePx(size)" :height="sizePx(size)"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <circle cx="12" cy="12" r="6"/>
    <circle cx="12" cy="12" r="2"/>
  </svg>

  <!-- Shield -->
  <svg v-else-if="name === 'shield'"
    :width="sizePx(size)" :height="sizePx(size)"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    <path d="M9 12l2 2 4-4"/>
  </svg>

  <!-- Check -->
  <svg v-else-if="name === 'check'"
    :width="sizePx(size)" :height="sizePx(size)"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>

  <!-- X / Close -->
  <svg v-else-if="name === 'x'"
    :width="sizePx(size)" :height="sizePx(size)"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/>
    <line x1="6" y1="6" x2="18" y2="18"/>
  </svg>

  <!-- Search -->
  <svg v-else-if="name === 'search'"
    :width="sizePx(size)" :height="sizePx(size)"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="11" cy="11" r="8"/>
    <line x1="21" y1="21" x2="16.65" y2="16.65"/>
  </svg>

  <!-- Refresh -->
  <svg v-else-if="name === 'refresh'"
    :width="sizePx(size)" :height="sizePx(size)"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="23 4 23 10 17 10"/>
    <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
  </svg>

  <!-- Send -->
  <svg v-else-if="name === 'send'"
    :width="sizePx(size)" :height="sizePx(size)"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <line x1="22" y1="2" x2="11" y2="13"/>
    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
  </svg>

  <!-- Default fallback -->
  <svg v-else
    :width="sizePx(size)" :height="sizePx(size)"
    viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <line x1="12" y1="8" x2="12" y2="16"/>
    <line x1="8" y1="12" x2="16" y2="12"/>
  </svg>
</template>
