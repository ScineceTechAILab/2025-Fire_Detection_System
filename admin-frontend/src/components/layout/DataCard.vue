<template>
  <el-card class="data-card fd-card" shadow="never">
    <template v-if="title || $slots.headerActions" #header>
      <div class="data-card__header">
        <span class="data-card__title">{{ title }}</span>
        <div v-if="$slots.headerActions" class="data-card__actions">
          <slot name="headerActions" />
        </div>
      </div>
    </template>
    <slot />
  </el-card>
</template>

<script setup lang="ts">
defineProps<{
  title?: string
}>()
</script>

<style scoped>
.data-card {
  margin-bottom: 16px;
}

.data-card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.data-card__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--fd-text);
}

.data-card__actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
