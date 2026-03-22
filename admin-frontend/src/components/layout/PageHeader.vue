<template>
  <div class="page-header">
    <div class="page-header__main">
      <h1 class="page-header__title">{{ title }}</h1>
      <p v-if="description" class="page-header__desc">{{ description }}</p>
      <div v-if="$slots.meta" class="page-header__meta">
        <slot name="meta" />
      </div>
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}

.page-header__main {
  min-width: 0;
}

.page-header__title {
  margin: 0;
  font-size: 24px;
  line-height: 1.25;
  color: var(--fd-text);
}

.page-header__desc {
  margin: 8px 0 0;
  color: var(--fd-text-secondary);
  font-size: 14px;
}

.page-header__meta {
  margin-top: 8px;
}

.page-header__actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
</style>
