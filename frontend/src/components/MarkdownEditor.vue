<template>
  <div class="md-editor">
    <div class="md-bar">
      <span class="md-label">MARKDOWN / 笔记正文</span>

      <div v-if="mode === 'edit'" class="md-tools">
        <button type="button" title="标题" @click="insertLine('## ')">H</button>
        <button type="button" title="加粗" @click="wrap('**', '**')">B</button>
        <button type="button" title="斜体" @click="wrap('*', '*')">I</button>
        <button type="button" title="列表" @click="insertLine('- ')">≡</button>
        <button type="button" title="引用" @click="insertLine('> ')">”</button>
        <button type="button" title="行内代码" @click="wrap('`', '`')">&lt;/&gt;</button>
      </div>

      <div class="md-switch">
        <button type="button" :class="{ active: mode === 'edit' }" @click="mode = 'edit'">
          编辑
        </button>
        <button type="button" :class="{ active: mode === 'preview' }" @click="mode = 'preview'">
          预览
        </button>
      </div>
    </div>

    <textarea
      v-if="mode === 'edit'"
      ref="textareaEl"
      class="md-input"
      :value="modelValue"
      placeholder="在这里写笔记，支持 Markdown…"
      @input="$emit('update:modelValue', $event.target.value)"
    />
    <div v-else class="md-preview" v-html="rendered"></div>

    <div class="md-foot">
      <span>{{ count }} 字</span>
      <span class="md-hint">单栏编辑 · 可切换预览</span>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { marked } from 'marked'

marked.setOptions({ gfm: true, breaks: true })

const props = defineProps({
  modelValue: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const mode = ref('edit')
const textareaEl = ref(null)

const count = computed(() => (props.modelValue || '').length)
const rendered = computed(() => marked.parse(props.modelValue || ''))

const apply = (before, after = '', lineStart = false) => {
  const el = textareaEl.value
  if (!el) return

  const text = props.modelValue || ''
  const start = el.selectionStart
  const end = el.selectionEnd
  const selected = text.slice(start, end)
  let next
  let caret

  if (lineStart) {
    const lineStartPos = text.lastIndexOf('\n', start - 1) + 1
    next = text.slice(0, lineStartPos) + before + text.slice(lineStartPos)
    caret = start + before.length
  } else {
    next = text.slice(0, start) + before + selected + after + text.slice(end)
    caret = start + before.length + selected.length
  }

  emit('update:modelValue', next)
  nextTick(() => {
    el.focus()
    el.setSelectionRange(caret, caret)
  })
}

const wrap = (before, after) => apply(before, after, false)
const insertLine = (prefix) => apply(prefix, '', true)
</script>

<style scoped>
.md-editor {
  width: 100%;
  flex: 1 1 100%;
  border: 1px solid var(--qf-line);
  border-radius: 3px;
  background: var(--qf-surface);
  overflow: hidden;
}

.md-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 9px 14px;
  border-bottom: 1px solid var(--qf-line);
  background: #f7f9f6;
}

.md-label {
  font-family: var(--qf-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.12em;
  color: var(--qf-muted);
}

.md-tools {
  display: flex;
  gap: 2px;
  margin-left: auto;
}

.md-tools button {
  width: 28px;
  height: 28px;
  border: 1px solid transparent;
  border-radius: 2px;
  background: transparent;
  color: var(--qf-ink-soft);
  font-family: var(--qf-mono);
  font-size: 12px;
  cursor: pointer;
}

.md-tools button:hover {
  border-color: var(--qf-line);
  background: var(--qf-surface);
  color: var(--qf-primary);
}

.md-switch {
  display: flex;
  border: 1px solid var(--qf-line);
  border-radius: 2px;
  overflow: hidden;
}

.md-switch button {
  padding: 4px 11px;
  border: 0;
  background: transparent;
  color: var(--qf-muted);
  font-size: 12px;
  cursor: pointer;
}

.md-switch button.active {
  background: var(--qf-primary);
  color: #fff;
}

.md-input {
  display: block;
  width: 100%;
  min-height: 460px;
  padding: 22px 24px;
  border: 0;
  outline: none;
  resize: vertical;
  background: var(--qf-surface);
  color: var(--qf-ink);
  font-family: var(--qf-mono);
  font-size: 14px;
  line-height: 1.85;
}

.md-input::placeholder {
  color: #9aa59e;
}

.md-preview {
  min-height: 460px;
  max-height: 620px;
  overflow-y: auto;
  padding: 22px 24px;
  color: var(--qf-ink-soft);
  font-size: 15px;
  line-height: 1.85;
}

.md-preview :deep(h1),
.md-preview :deep(h2),
.md-preview :deep(h3) {
  margin: 1.2em 0 0.5em;
  color: var(--qf-ink);
  font-weight: 800;
  letter-spacing: -0.02em;
}

.md-preview :deep(p) {
  margin: 0 0 1em;
}

.md-preview :deep(ul),
.md-preview :deep(ol) {
  margin: 0 0 1em;
  padding-left: 1.4em;
}

.md-preview :deep(code) {
  padding: 1px 5px;
  background: var(--qf-paper);
  font-family: var(--qf-mono);
  font-size: 0.92em;
}

.md-preview :deep(pre) {
  padding: 14px;
  background: var(--qf-paper);
  overflow-x: auto;
}

.md-preview :deep(blockquote) {
  margin: 0 0 1em;
  padding-left: 14px;
  border-left: 3px solid var(--qf-accent);
  color: var(--qf-muted);
}

.md-preview :deep(img) {
  max-width: 100%;
}

.md-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  border-top: 1px solid var(--qf-line);
  background: #f7f9f6;
  color: var(--qf-muted);
  font-family: var(--qf-mono);
  font-size: 10px;
  letter-spacing: 0.06em;
}

.md-hint {
  opacity: 0.8;
}
</style>
