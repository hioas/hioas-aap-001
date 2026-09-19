import { computed, ref } from 'vue';
import type { AdminRole } from '@/config/nav';

/**
 * 会话状态（当前登录管理员的姓名/角色）。
 *
 * 真源：`GET /auth/me`。**角色只用于前端渲染过滤**，后端对每个接口二次校验
 * （PRD 13 §1：「权限模型 RBAC，后端下发 allowed_actions[] 并二次校验」）。
 * 未登录/未取到时回落到最小权限角色，宁可少渲染也不越权渲染。
 */
const userName = ref('');
const role = ref<AdminRole>('BIZ_OPERATOR');

export function useSession() {
  return {
    userName: computed(() => userName.value),
    role: computed(() => role.value),
    set(name: string, r: AdminRole) {
      userName.value = name;
      role.value = r;
    },
    clear() {
      userName.value = '';
      role.value = 'BIZ_OPERATOR';
    }
  };
}
