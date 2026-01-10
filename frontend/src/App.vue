<template>
  <router-view />
</template>

<script setup lang="ts">
</script>

<style>
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
}

.el-textarea__inner::-webkit-scrollbar {
  width: 14px;
}
.el-textarea__inner::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 4px;
  border: 4px solid transparent;
  background-clip: padding-box;
}
.el-textarea__inner::-webkit-scrollbar-track {
  background: transparent;
}
</style>
