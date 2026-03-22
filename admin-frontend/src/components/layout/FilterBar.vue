<template>
  <el-card class="filter-bar fd-card" shadow="never">
    <slot />
  </el-card>
</template>

<style scoped>
.filter-bar {
  margin-bottom: 16px;
  background: var(--fd-surface-soft);
}
</style>
