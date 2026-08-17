<template>
  <div class="app-root">
    <div v-if="showSidebar" class="app-layout">
      <NotesSidebar />
      <main class="app-main">
        <router-view />
      </main>
    </div>
    <router-view v-else />
  </div>
  <ConfirmDialog />
  <Toast />
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuth } from '@/composables/useAuth'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import Toast from '@/components/Toast.vue'
import NotesSidebar from '@/components/NotesSidebar.vue'

const auth = useAuth()
const route = useRoute()

// 登录页不显示侧边栏；其余（笔记路由）均显示（布局结构参考 chatbot
// ChatLayout 的 .chat-layout/.chat-main flex 约定）。
const showSidebar = computed(() => {
  return route.name !== 'Login'
})

onMounted(() => {
  auth.initAuth()
})
</script>

<style>
/* 布局壳 — 结构对齐 chatbot ChatLayout.vue（.chat-layout flex row + .chat-main
   flex:1 min-width:0）；笔记页面按 chatbot 约定依赖父级 flex:1 + height:0。 */
.app-root {
  height: 100dvh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-layout {
  display: flex;
  height: 100dvh;
  overflow: hidden;
  flex: 1;
  min-height: 0;
}

.app-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  height: 100%;
}
</style>
