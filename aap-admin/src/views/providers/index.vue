<template>
  <div class="stub">
    <div class="aap-card stub__card">
      <div class="stub__head">
        <span class="stub__title">供应商管理</span>
        <span class="aap-badge aap-badge--warn">待实现</span>
      </div>
      <p class="stub__sub">进件主体与凭证</p>
      <el-descriptions :column="1" border size="small" class="stub__src">
        <el-descriptions-item label="设计真源（Calicat）">
          页码 <code>page-4-pc</code> · layer_id <code>b94a8daa-cdd8-40bc-86b7-1d351b1ff500</code>
        </el-descriptions-item>
        <el-descriptions-item label="业务真源（PRD）">PRD 13 §2 供应商管理（<code>.calicat/prd/13-管理端PRD.md</code>）</el-descriptions-item>
        <el-descriptions-item label="本地设计数据">
          <code>.calicat-admin/raw/pages/page-4-pc/design.json</code>
        </el-descriptions-item>
      </el-descriptions>
      <p class="stub__note">
        本页尚未按设计真源实现。骨架先保证路由/外壳可验证；实现时逐元素对照
        <code>tools/calicat-outline.mjs page-4-pc --all --depth 9</code> 的输出。
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
// 骨架：无逻辑。实现时替换为真实的取数与交互。
</script>

<style scoped>
.stub { display: flex; }
.stub__card { flex: 1; padding: 22px 24px; }
.stub__head { display: flex; align-items: center; gap: 10px; }
.stub__title { font-size: var(--fs-2xl); font-weight: 600; }
.stub__sub { font-size: var(--fs-base); color: var(--c-text-muted); margin: 6px 0 18px; }
.stub__src { margin-bottom: 16px; }
.stub__note { font-size: var(--fs-base); color: var(--c-text-sub); line-height: 1.7; }
code { background: var(--c-surface-alt); padding: 1px 5px; border-radius: var(--r-sm); font-size: var(--fs-sm); }
</style>
