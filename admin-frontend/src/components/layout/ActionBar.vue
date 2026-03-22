<template>
  <div class="action-bar">
    <slot />
  </div>
</template>

<style scoped>
.action-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
</style>
