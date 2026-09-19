package com.hioas.aap.common;

import static java.nio.charset.StandardCharsets.UTF_8;

import com.hioas.aap.config.AppProperties;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.HexFormat;
import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.stereotype.Component;

/**
 * 加解密与脱敏（真源：17-spec R-05/R-06/R-48 · §10 安全）。
 *
 * <ul>
 *   <li>凭证/手机号落库：AES-256-GCM，密文格式 {@code base64(iv ‖ ciphertext ‖ tag)}（12 字节 IV、128 位 tag）</li>
 *   <li>检索：SHA-256（{@code phone_hash} / {@code api_key_fingerprint}），密文不可检索</li>
 *   <li>脱敏：手机号 {@code 前3****后4}（R-48）、api_key {@code 前4***后4}（R-05）</li>
 * </ul>
 *
 * <p>密钥与库分离（R-06）：密钥只来自环境变量，不落库、不出现在响应与日志。
 */
@Component
public class CryptoService {

    private static final String AES_GCM = "AES/GCM/NoPadding";
    private static final int IV_LENGTH = 12;
    private static final int TAG_BITS = 128;
    private static final SecureRandom RANDOM = new SecureRandom();

    private final SecretKeySpec key;

    public CryptoService(AppProperties properties) {
        byte[] raw;
        try {
            raw = Base64.getDecoder().decode(properties.credential().aesKey());
        } catch (RuntimeException e) {
            throw new IllegalStateException("app.credential.aes-key 不是合法 base64（见 E:\\env\\aap-server.env）", e);
        }
        if (raw.length != 32) {
            throw new IllegalStateException(
                    "app.credential.aes-key 必须是 32 字节（AES-256）的 base64，当前长度=" + raw.length
                            + "；请在 E:\\env\\aap-server.env 重新生成（openssl rand -base64 32）");
        }
        this.key = new SecretKeySpec(raw, "AES");
    }

    /** AES-256-GCM 加密 → base64(iv‖ct‖tag)。 */
    public String encrypt(String plain) {
        if (plain == null) {
            return null;
        }
        try {
            byte[] iv = new byte[IV_LENGTH];
            RANDOM.nextBytes(iv);
            Cipher cipher = Cipher.getInstance(AES_GCM);
            cipher.init(Cipher.ENCRYPT_MODE, key, new GCMParameterSpec(TAG_BITS, iv));
            byte[] ct = cipher.doFinal(plain.getBytes(UTF_8));
            byte[] out = new byte[iv.length + ct.length];
            System.arraycopy(iv, 0, out, 0, iv.length);
            System.arraycopy(ct, 0, out, iv.length, ct.length);
            return Base64.getEncoder().encodeToString(out);
        } catch (Exception e) {
            throw new IllegalStateException("加密失败", e);
        }
    }

    /** 解密 {@code base64(iv‖ct‖tag)}。 */
    public String decrypt(String cipherText) {
        if (cipherText == null) {
            return null;
        }
        try {
            byte[] all = Base64.getDecoder().decode(cipherText);
            byte[] iv = new byte[IV_LENGTH];
            System.arraycopy(all, 0, iv, 0, IV_LENGTH);
            Cipher cipher = Cipher.getInstance(AES_GCM);
            cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(TAG_BITS, iv));
            byte[] plain = cipher.doFinal(all, IV_LENGTH, all.length - IV_LENGTH);
            return new String(plain, UTF_8);
        } catch (Exception e) {
            throw new IllegalStateException("解密失败（密钥不符或密文损坏）", e);
        }
    }

    public String sha256Hex(String value) {
        if (value == null) {
            return null;
        }
        return sha256Hex(value.getBytes(UTF_8));
    }

    /**
     * 字节内容摘要（文件完整性校验用）。
     *
     * <p>与 {@link #sha256Hex(String)} 同一套算法，避免「字符串摘要」与「文件摘要」
     * 两套实现产生不可比的结果。
     */
    public String sha256Hex(byte[] content) {
        if (content == null) {
            return null;
        }
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(content));
        } catch (Exception e) {
            throw new IllegalStateException("SHA-256 计算失败", e);
        }
    }

    /** 手机号脱敏：{@code 138****5678}（R-48）。 */
    public String maskPhone(String phone) {
        if (phone == null || phone.length() < 7) {
            return phone;
        }
        return phone.substring(0, 3) + "****" + phone.substring(phone.length() - 4);
    }

    /** api_key 脱敏：{@code sk-a***5678}（前 4 + *** + 后 4，R-05）。 */
    public String maskApiKey(String apiKey) {
        if (apiKey == null || apiKey.length() < 9) {
            return "***";
        }
        return apiKey.substring(0, 4) + "***" + apiKey.substring(apiKey.length() - 4);
    }

    /** 随机数字验证码（默认 6 位）。 */
    public String randomNumericCode(int digits) {
        StringBuilder sb = new StringBuilder(digits);
        for (int i = 0; i < digits; i++) {
            sb.append(RANDOM.nextInt(10));
        }
        return sb.toString();
    }

    /** 随机不透明令牌（refresh token）。 */
    public String randomToken() {
        byte[] bytes = new byte[32];
        RANDOM.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }
}
