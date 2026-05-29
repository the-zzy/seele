<template>
  <div class="agent-view">
    <AgentChat mode="page" />
  </div>
</template>

<script setup>
import AgentChat from '@/components/agent/AgentChat.vue'
</script>

<style lang="scss" scoped>
.agent-view {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
</style>
