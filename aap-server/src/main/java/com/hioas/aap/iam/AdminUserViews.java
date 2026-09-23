package com.hioas.aap.iam;

/**
 * 运营账号视图（ADM-AUTH02…05；与 `json-schema/models/admin-user.schema.json` 一致）。
 *
 * <p>手机号一律**只出脱敏值** {@code phone_masked}：管理端列表不需要明文手机号，
 * 明文只以 AES-GCM 密文存 `phone_cipher`（见 {@link AdminUserService}）。
 */
public final class AdminUserViews {

    private AdminUserViews() {
    }

    /** 单个运营账号（对外雪花 ID 一律 string，避免 JS 精度丢失）。 */
    public record AdminUser(String id, String admin_user_id, String username, String display_name,
                            String role, String status, String phone_masked, String last_login_at,
                            String created_at) {
    }
}
