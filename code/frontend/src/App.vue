<template>
  <div class="app-layout">
    <header class="app-header">
      <div class="logo">迁移管家 MigOps</div>
      <nav class="nav">
        <router-link to="/">概览</router-link>
        <router-link to="/b01/spaces">项目空间</router-link>
      </nav>
    </header>
    <main class="app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts"></script>

<style>
.app-layout { font-family: system-ui, sans-serif; }
.app-header {
  display: flex; align-items: center; gap: 24px;
  padding: 0 24px; height: 56px; background: #001529; color: #fff;
}
.app-header .logo { font-weight: 600; }
.app-header .nav a { color: #ccc; margin-right: 16px; text-decoration: none; }
.app-header .nav a.router-link-active { color: #fff; }
.app-main { padding: 24px; }
</style>
