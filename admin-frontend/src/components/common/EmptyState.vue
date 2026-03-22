<template>
  <div class="empty-state">
    <el-icon class="empty-state__icon"><Files /></el-icon>
    <h3 class="empty-state__title">{{ title }}</h3>
    <p v-if="description" class="empty-state__description">{{ description }}</p>
    <div v-if="$slots.actions" class="empty-state__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Files } from '@element-plus/icons-vue'

withDefaults(
  defineProps<{
    title: string
    description?: string
  }>(),
  {
    description: ''
  }
)
</script>

<style scoped>
.empty-state {
  display: grid;
  place-items: center;
  text-align: center;
  padding: 48px 16px;
  color: var(--fd-text-secondary);
}

.empty-state__icon {
  font-size: 44px;
  color: var(--fd-primary);
  margin-bottom: 12px;
}

.empty-state__title {
  margin: 0;
  font-size: 18px;
  color: var(--fd-text);
}

.empty-state__description {
  margin: 8px 0 0;
}

.empty-state__actions {
  margin-top: 16px;
}
</style>
