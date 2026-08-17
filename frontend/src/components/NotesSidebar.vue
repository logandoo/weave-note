<template>
  <!-- 侧边栏笔记本导航 — 模板结构/样式抽取自 chatbot Sidebar.vue 的
       notes-panel-inline 区块（L58-133 模板 + L1391-1560 逻辑 + np-* CSS），
       二级菜单（重命名/删除/移动到）UI 模式取自 NotebooksList.vue /
       NotesList.vue 的 context-menu + inline-editor（chatbot 原版交互）。 -->
  <aside class="notes-sidebar">
    <div class="notes-panel-header">
      <span class="notes-panel-title">笔记本</span>
      <button class="new-note-btn" @click="startNewNote" title="新建笔记">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="12" y1="18" x2="12" y2="12"/>
          <line x1="9" y1="15" x2="15" y2="15"/>
        </svg>
      </button>
    </div>
    <div class="notes-panel-loading" v-if="notesPanelLoading">加载中…</div>
    <div class="notes-panel-list" v-else>
      <div
        class="np-notebook np-home"
        :class="{ active: isOnNotesRoot }"
        @click="goToNotebooksHome"
        role="button"
        tabindex="0"
        @keydown.enter.prevent="goToNotebooksHome"
        @keydown.space.prevent="goToNotebooksHome"
      >
        <div class="np-notebook-row">
          <svg class="np-chevron np-chevron-placeholder" width="13" height="13" viewBox="0 0 24 24" aria-hidden="true"></svg>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 12l2-2 7-7 7 7 2 2"/>
            <path d="M5 10v10a1 1 0 0 0 1 1h3v-6h6v6h3a1 1 0 0 0 1-1V10"/>
          </svg>
          <span class="np-nb-name">首页</span>
        </div>
      </div>
      <div
        class="np-notebook"
        v-for="nb in notesStore.notebooks"
        :key="nb.id"
      >
        <div
          class="np-notebook-row"
          :class="{ active: isActivePanelNotebook(nb.id) }"
          @click="toggleNotesPanelNotebook(nb.id)"
          @dblclick="openNotebookInPanel(nb.id)"
        >
          <svg class="np-chevron" :class="{ expanded: !!notesPanelExpanded[nb.id] }" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 6 15 12 9 18"/>
          </svg>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
          </svg>
          <!-- 内联重命名（NotebooksList inline-editor 模式） -->
          <template v-if="editingNotebookId === nb.id">
            <div class="inline-editor" @click.stop>
              <input
                ref="editingInput"
                v-model="editingName"
                class="notebook-name-input"
                placeholder="笔记本名称"
                @keyup.enter="saveNotebookName(nb.id)"
                @keyup.escape="cancelEditNotebook"
                @click.stop
              />
              <div class="inline-editor-actions">
                <button class="inline-action save" @mousedown.prevent @click.stop="saveNotebookName(nb.id)">保存</button>
                <button class="inline-action cancel" @mousedown.prevent @click.stop="cancelEditNotebook">取消</button>
              </div>
            </div>
          </template>
          <template v-else>
            <span class="np-nb-name">{{ nb.name }}</span>
            <span class="np-count">{{ nb.note_count }}</span>
            <button class="np-menu-btn" @click.stop="openNotebookMenu(nb, $event)" title="更多操作" aria-label="笔记本操作">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                <circle cx="5" cy="12" r="1.8"/><circle cx="12" cy="12" r="1.8"/><circle cx="19" cy="12" r="1.8"/>
              </svg>
            </button>
          </template>
        </div>
        <div class="np-notes-list" v-show="!!notesPanelExpanded[nb.id]">
          <div
            v-for="note in notesStore.notes[nb.id] || []"
            :key="note.id"
            class="np-note-row"
            :class="{ active: isActivePanelNote(nb.id, note.id) }"
            @click="openNoteInPanel(nb.id, note.id)"
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            <!-- 内联重命名（NotesList 同模式） -->
            <template v-if="editingNoteId === note.id">
              <div class="inline-editor" @click.stop>
                <input
                  ref="editingInput"
                  v-model="editingName"
                  class="notebook-name-input"
                  placeholder="笔记标题"
                  @keyup.enter="saveNoteTitle(note.id)"
                  @keyup.escape="cancelEditNote"
                  @click.stop
                />
                <div class="inline-editor-actions">
                  <button class="inline-action save" @mousedown.prevent @click.stop="saveNoteTitle(note.id)">保存</button>
                  <button class="inline-action cancel" @mousedown.prevent @click.stop="cancelEditNote">取消</button>
                </div>
              </div>
            </template>
            <template v-else>
              <span class="np-note-title">{{ note.title || '无标题' }}</span>
              <button class="np-menu-btn" @click.stop="openNoteMenu(note, nb.id, $event)" title="更多操作" aria-label="笔记操作">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                  <circle cx="5" cy="12" r="1.8"/><circle cx="12" cy="12" r="1.8"/><circle cx="19" cy="12" r="1.8"/>
                </svg>
              </button>
            </template>
          </div>
          <div v-if="!!notesPanelNotebookLoading[nb.id]" class="np-note-loading">加载中…</div>
          <div v-else-if="!(notesStore.notes[nb.id] || []).length" class="np-empty">暂无笔记</div>
        </div>
      </div>
      <div v-if="!notesStore.notebooks.length" class="np-empty">暂无笔记本</div>
    </div>

    <!-- 二级操作菜单（NotebooksList/NotesList context-menu 模式） -->
    <Teleport to="body">
      <div v-if="menuVisible" class="context-menu" :style="menuStyle" @click.stop>
        <template v-if="menuKind === 'notebook'">
          <button class="menu-item" @click="handleMenuRenameNotebook">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
            <span>重命名</span>
          </button>
          <button v-if="!menuNotebook?.is_default" class="menu-item delete" @click="handleMenuDeleteNotebook">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
            <span>删除笔记本</span>
          </button>
          <button v-else class="menu-item disabled" disabled>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
            <span>默认笔记本不可删除</span>
          </button>
        </template>
        <template v-else-if="menuKind === 'note'">
          <button class="menu-item" @click="handleMenuRenameNote">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
            <span>重命名</span>
          </button>
          <button class="menu-item" @click="handleMenuMoveNote">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            <span>移动到其他笔记本</span>
          </button>
          <button class="menu-item delete" @click="handleMenuDeleteNote">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
            <span>删除</span>
          </button>
        </template>
      </div>
      <div v-if="menuVisible" class="context-menu-overlay" @click="closeMenu" @contextmenu.prevent="closeMenu"></div>
    </Teleport>

    <NotebookPicker
      v-if="showNewNotePicker"
      @select="handleNewNoteNotebookSelected"
      @close="showNewNotePicker = false"
    />
    <NotebookPicker
      v-if="showMovePicker"
      :exclude-notebook-id="moveSourceNotebookId || undefined"
      @select="handleMoveTargetSelected"
      @close="showMovePicker = false"
    />
  </aside>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useNotesStore } from '@/stores/notes'
import { useConfirmDialog } from '@/composables/useConfirmDialog'
import NotebookPicker from '@/components/NotebookPicker.vue'

const route = useRoute()
const router = useRouter()
const notesStore = useNotesStore()
const showConfirm = useConfirmDialog().confirm

// True when the user is on the notebook-picker page (i.e. /notes exactly,
// no notebook id selected). Used to highlight the "首页" sidebar entry.
const isOnNotesRoot = computed(() => {
  return route.path === '/notes' || route.path === '/notes/'
})

const activeNotebookId = computed(() => {
  return typeof route.params.notebookId === 'string' ? route.params.notebookId : ''
})

const activeNoteId = computed(() => {
  return typeof route.params.noteId === 'string' ? route.params.noteId : ''
})

function goToNotebooksHome() {
  if (isOnNotesRoot.value) return
  notesStore.saveLastNotesPath('/notes')
  void router.push('/notes')
}

// Desktop inline notes panel — driven by route
const notesPanelLoading = ref(false)
const NOTES_PANEL_EXPANDED_KEY = 'chatllm_notes_panel_expanded_v2'
function _loadExpandedFromStorage(): Record<string, boolean> {
  try {
    return JSON.parse(localStorage.getItem(NOTES_PANEL_EXPANDED_KEY) || '{}')
  } catch {
    return {}
  }
}
const notesPanelExpanded = ref<Record<string, boolean>>(_loadExpandedFromStorage())
const notesPanelNotebookLoading = ref<Record<string, boolean>>({})

function _saveExpandedToStorage() {
  localStorage.setItem(NOTES_PANEL_EXPANDED_KEY, JSON.stringify(notesPanelExpanded.value))
}

function setNotesPanelExpanded(notebookId: string, expanded: boolean) {
  if (expanded) {
    notesPanelExpanded.value = { ...notesPanelExpanded.value, [notebookId]: true }
  } else {
    const next = { ...notesPanelExpanded.value }
    delete next[notebookId]
    notesPanelExpanded.value = next
  }
  _saveExpandedToStorage()
}

// When notebooks become available (loaded by NotebooksList or NotesList),
// ensure notes are loaded for expanded notebooks
watch(() => notesStore.notebooks.length, async (len, oldLen) => {
  if (len > 0 && (!oldLen || oldLen === 0)) {
    await _loadNotesPanelData()
  }
})

watch(activeNotebookId, async (notebookId) => {
  if (!notebookId) return
  if (!notesStore.notebooks.length) await _loadNotesPanelData()
  if (!notesPanelExpanded.value[notebookId]) {
    setNotesPanelExpanded(notebookId, true)
  }
  await loadNotesPanelNotebook(notebookId)
})

async function _loadNotesPanelData() {
  if (!notesStore.notebooks.length) {
    await notesStore.loadNotebooks()
    if (!notesStore.notebooks.length) return
  }

  notesPanelLoading.value = true
  try {
    if (Object.keys(notesPanelExpanded.value).length === 0) {
      const firstId = notesStore.notebooks[0].id
      setNotesPanelExpanded(firstId, true)
    }
    const expandedIds = Object.keys(notesPanelExpanded.value).filter(k => notesPanelExpanded.value[k])
    const loadPromises = expandedIds
      .filter(id => !notesStore.notes[id] || notesStore.notes[id].length === 0)
      .map(id => loadNotesPanelNotebook(id))
    if (loadPromises.length > 0) {
      await Promise.all(loadPromises)
    }
  } finally {
    notesPanelLoading.value = false
  }
}

async function loadNotesPanelNotebook(notebookId: string) {
  notesPanelNotebookLoading.value = { ...notesPanelNotebookLoading.value, [notebookId]: true }
  try {
    await notesStore.loadNotes(notebookId)
  } finally {
    const next = { ...notesPanelNotebookLoading.value }
    delete next[notebookId]
    notesPanelNotebookLoading.value = next
  }
}

async function toggleNotesPanelNotebook(notebookId: string) {
  if (notesPanelExpanded.value[notebookId]) {
    setNotesPanelExpanded(notebookId, false)
  } else {
    setNotesPanelExpanded(notebookId, true)
    await loadNotesPanelNotebook(notebookId)
  }
}

function openNotebookInPanel(notebookId: string) {
  const targetPath = `/notes/${notebookId}`
  if (route.path === targetPath) return
  void router.push(targetPath)
}

function openNoteInPanel(notebookId: string, noteId: string) {
  const targetPath = `/notes/${notebookId}/${noteId}`
  if (route.path === targetPath) return
  void router.push(targetPath)
}

function isActivePanelNotebook(notebookId: string) {
  return activeNotebookId.value === notebookId
}

function isActivePanelNote(notebookId: string, noteId: string) {
  return activeNotebookId.value === notebookId && activeNoteId.value === noteId
}

// ─── 新建笔记（NotebookPicker 选择目标笔记本后建空笔记并跳转编辑器）───
const showNewNotePicker = ref(false)

function startNewNote() {
  notesStore.loadNotebooks()
  showNewNotePicker.value = true
}

async function handleNewNoteNotebookSelected(notebookId: string) {
  showNewNotePicker.value = false
  try {
    const note = await notesStore.createNote(notebookId, { content: '' })
    void router.push(`/notes/${notebookId}/${note.id}`)
  } catch (e) {
    console.error('Failed to create note:', e)
  }
}

// ─── 二级操作菜单（context-menu 模式，取自 NotebooksList/NotesList）───
type NotebookLike = { id: string; name: string; is_default?: boolean; note_count?: number }
type NoteLike = { id: string; title?: string | null }

const menuVisible = ref(false)
const menuKind = ref<'notebook' | 'note'>('notebook')
const menuStyle = ref<Record<string, string>>({})
const menuNotebook = ref<NotebookLike | null>(null)
const menuNote = ref<NoteLike | null>(null)
const menuNoteNotebookId = ref<string | null>(null)

function openNotebookMenu(nb: NotebookLike, e: Event) {
  menuKind.value = 'notebook'
  menuNotebook.value = nb
  positionMenu(e)
  menuVisible.value = true
}

function openNoteMenu(note: NoteLike, notebookId: string, e: Event) {
  menuKind.value = 'note'
  menuNote.value = note
  menuNoteNotebookId.value = notebookId
  positionMenu(e)
  menuVisible.value = true
}

function positionMenu(e: Event) {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const menuW = 200
  const left = Math.min(rect.right - menuW, window.innerWidth - menuW - 8)
  menuStyle.value = {
    top: `${Math.min(rect.bottom + 4, window.innerHeight - 160)}px`,
    left: `${Math.max(left, 8)}px`,
  }
}

function closeMenu() {
  menuVisible.value = false
  menuNotebook.value = null
  menuNote.value = null
  menuNoteNotebookId.value = null
}

// ─── 内联重命名 ───
const editingNotebookId = ref<string | null>(null)
const editingNoteId = ref<string | null>(null)
const editingName = ref('')
const editingInput = ref<HTMLInputElement | null>(null)

async function focusEditingInput() {
  await nextTick()
  editingInput.value?.focus()
  editingInput.value?.select()
}

function handleMenuRenameNotebook() {
  if (!menuNotebook.value) return
  const nb = menuNotebook.value
  closeMenu()
  editingNoteId.value = null
  editingNotebookId.value = nb.id
  editingName.value = nb.name
  void focusEditingInput()
}

function handleMenuRenameNote() {
  if (!menuNote.value) return
  const note = menuNote.value
  closeMenu()
  editingNotebookId.value = null
  editingNoteId.value = note.id
  editingName.value = note.title || ''
  void focusEditingInput()
}

function cancelEditNotebook() {
  editingNotebookId.value = null
  editingName.value = ''
}

function cancelEditNote() {
  editingNoteId.value = null
  editingName.value = ''
}

async function saveNotebookName(notebookId: string) {
  const name = editingName.value.trim()
  if (!name) {
    cancelEditNotebook()
    return
  }
  try {
    await notesStore.updateNotebook(notebookId, name)
  } catch (e) {
    console.error('Failed to rename notebook:', e)
  }
  cancelEditNotebook()
}

async function saveNoteTitle(noteId: string) {
  const title = editingName.value.trim()
  try {
    await notesStore.updateNote(noteId, { title })
  } catch (e) {
    console.error('Failed to rename note:', e)
  }
  cancelEditNote()
}

// ─── 删除（ConfirmDialog 确认；笔记本删除提示会连带删除全部笔记）───
async function handleMenuDeleteNotebook() {
  const nb = menuNotebook.value
  closeMenu()
  if (!nb) return
  if (nb.is_default) return

  if (!await showConfirm({
    message: '确定要删除这个笔记本吗？该操作会删除笔记本内的全部笔记。',
    danger: true,
    confirmText: '删除',
  })) {
    return
  }
  try {
    await notesStore.deleteNotebook(nb.id)
  } catch (e) {
    console.error('Failed to delete notebook:', e)
  }
}

async function handleMenuDeleteNote() {
  const note = menuNote.value
  const notebookId = menuNoteNotebookId.value
  closeMenu()
  if (!note || !notebookId) return

  if (!await showConfirm({
    message: '确定要删除这条笔记吗？',
    danger: true,
    confirmText: '删除',
  })) {
    return
  }
  try {
    await notesStore.deleteNote(note.id)
    await loadNotesPanelNotebook(notebookId)
  } catch (e) {
    console.error('Failed to delete note:', e)
  }
}

// ─── 移动到其他笔记本（NotebookPicker）───
const showMovePicker = ref(false)
const moveSourceNotebookId = ref<string | null>(null)
const moveNoteId = ref<string | null>(null)

function handleMenuMoveNote() {
  const note = menuNote.value
  const notebookId = menuNoteNotebookId.value
  closeMenu()
  if (!note || !notebookId) return
  moveSourceNotebookId.value = notebookId
  moveNoteId.value = note.id
  showMovePicker.value = true
}

async function handleMoveTargetSelected(targetNotebookId: string) {
  const noteId = moveNoteId.value
  const notebookId = moveSourceNotebookId.value
  showMovePicker.value = false
  moveNoteId.value = null
  if (!noteId || !notebookId || targetNotebookId === notebookId) {
    moveSourceNotebookId.value = null
    return
  }
  try {
    await notesStore.moveNote(noteId, targetNotebookId)
    await loadNotesPanelNotebook(notebookId)
    await notesStore.loadNotebooks()
  } catch (e) {
    console.error('Failed to move note:', e)
  }
  moveSourceNotebookId.value = null
}

onMounted(() => {
  void _loadNotesPanelData()
})
</script>

<style scoped>
/* CSS 抽取自 chatbot Sidebar.vue L4011-4203（notes-panel/np-* 全段）+
   NotebooksList.vue（context-menu/menu-item/inline-editor 段） */
.notes-sidebar {
  display: flex;
  flex-direction: column;
  width: 280px;
  flex-shrink: 0;
  min-height: 0;
  overflow-y: auto;
  background-color: var(--surface-panel-strong);
  border-right: 1px solid var(--color-border);
}

.notes-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px 6px;
  position: sticky;
  top: 0;
  background: var(--color-white);
  z-index: 1;
  border-bottom: 1px solid var(--color-border);
}

.notes-panel-title {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-light);
}

.new-note-btn {
  padding: 8px;
  color: var(--color-text-light);
  border-radius: var(--radius-sm);
  transition: color var(--transition-fast), background-color var(--transition-fast), transform var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
}
.new-note-btn:hover { color: var(--color-primary); background-color: var(--color-hover); }
.new-note-btn:active { transform: scale(0.96); }

.notes-panel-loading {
  padding: 12px 14px;
  font-size: 12px;
  color: var(--color-text-light);
}

.notes-panel-list {
  padding: 4px 0;
}

.np-notebook { }

/* Desktop-only "首页" row — same visual hierarchy as a notebook row. */
.np-home {
  outline: none;
}
/* Ensure the home row stretches to the full sidebar width so the active
  background reads like the rest of the notebook tree. */
.np-notebook.np-home {
  display: block;
}
.np-home {
  margin: 0 8px 8px;
}
.np-home:focus-visible .np-notebook-row {
  background-color: var(--color-hover);
}
.np-home.active .np-notebook-row {
  background-color: color-mix(in srgb, var(--color-primary) 14%, var(--surface-panel-subtle));
  box-shadow: inset 0 0 0 1px var(--panel-border-strong);
  font-weight: 600;
}
.np-chevron-placeholder {
  visibility: hidden;
}

.np-notebook-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  margin: 0 8px;
  border-radius: var(--shell-workbench-radius);
  cursor: pointer;
  user-select: none;
}
.np-notebook-row:hover { background-color: var(--color-hover); }
.np-notebook-row.active {
  background-color: color-mix(in srgb, var(--color-primary) 14%, var(--surface-panel-subtle));
  box-shadow: inset 0 0 0 1px var(--panel-border-strong);
}
.np-notebook-row.active .np-nb-name {
  color: var(--color-primary);
}
.np-notebook-row.active .np-count {
  background: color-mix(in srgb, var(--color-primary) 16%, var(--surface-panel-strong));
  color: var(--color-primary);
}

.np-chevron {
  transition: transform var(--transition-fast);
  color: var(--color-text-light);
  flex-shrink: 0;
}
.np-chevron.expanded { transform: rotate(90deg); }

.np-nb-name {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.np-count {
  font-size: 11px;
  color: var(--color-text-light);
  background: var(--color-bg);
  padding: 1px 6px;
  border-radius: 10px;
  font-variant-numeric: tabular-nums;
  min-width: 18px;
  text-align: center;
}

.np-notes-list { padding-left: 18px; }

.np-note-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  cursor: pointer;
  border-radius: var(--shell-workbench-radius);
  margin: 5px 8px;
}
.np-note-row:hover { background-color: var(--color-hover); }
.np-note-row svg { flex-shrink: 0; color: var(--color-text-light); }
.np-note-row.active {
  background-color: color-mix(in srgb, var(--color-primary) 18%, var(--surface-panel-strong));
  box-shadow: inset 0 0 0 1px var(--panel-border-strong);
}
.np-note-row.active svg,
.np-note-row.active .np-note-title {
  color: var(--color-primary);
}
.np-note-row.active .np-note-title {
  font-weight: 600;
}

.np-note-title {
  font-size: 13px;
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.np-note-loading, .np-empty {
  padding: 6px 12px;
  font-size: 12px;
  color: var(--color-text-light);
}

/* ⋯ 菜单触发按钮：hover 显示（NotebooksList .menu-btn 模式） */
.np-menu-btn {
  opacity: 0;
  padding: 4px 6px;
  color: var(--color-text-light);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  flex-shrink: 0;
  background: transparent;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}
.np-notebook-row:hover .np-menu-btn,
.np-note-row:hover .np-menu-btn,
.np-menu-btn:focus-visible {
  opacity: 1;
}
.np-menu-btn:hover {
  color: var(--color-primary);
  background-color: var(--color-hover);
}

/* 二级操作菜单（NotebooksList/NotesList context-menu 段） */
.context-menu {
  position: fixed;
  background: var(--surface-panel-strong);
  border: 1px solid var(--panel-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  z-index: 1001;
  min-width: 160px;
  padding: 4px 0;
}
.context-menu-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
}
.menu-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  color: var(--color-text);
  font-size: 13px;
  text-align: left;
  transition: background-color var(--transition-fast);
  background: transparent;
  border: none;
  cursor: pointer;
}
.menu-item:hover:not(.disabled) {
  background-color: var(--color-hover);
}
.menu-item.delete {
  color: var(--color-error);
}
.menu-item.delete:hover {
  background-color: color-mix(in srgb, var(--color-error) 8%, transparent);
}
.menu-item.disabled {
  color: var(--color-text-light);
  cursor: default;
}

/* 内联重命名（NotebooksList inline-editor 段） */
.inline-editor {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.notebook-name-input {
  flex: 1;
  min-width: 0;
  padding: 6px 8px;
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--color-text);
  background: var(--surface-panel-subtle);
  outline: none;
  box-shadow: 0 0 0 3px rgba(53, 133, 197, 0.10);
}
.inline-editor-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}
.inline-action {
  padding: 5px 9px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
}
.inline-action.save {
  background: var(--color-primary);
  color: white;
}
.inline-action.cancel {
  background-color: var(--surface-panel-subtle);
  color: var(--color-text);
  border: 1px solid var(--panel-border);
}
</style>
