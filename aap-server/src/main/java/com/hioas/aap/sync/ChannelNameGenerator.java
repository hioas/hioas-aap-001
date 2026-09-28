package com.hioas.aap.sync;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Locale;
import java.util.Optional;

/**
 * 渠道命名器（T-M4-05）—— 供给单元的渠道名生成与反解。
 *
 * <p>规格：`specs/001-intake-automation/spec.md` §3.3（渠道命名规则）+ §6 `R-54`/`R-55`。
 *
 * <p>硬约束（据实，非设计假设）：
 * <ul>
 *   <li>{@code aap_channel_binding.channel_name} 为 {@code varchar(64)}（真实 DDL 实测），
 *       故 {@link #MAX_LENGTH} = 64 —— 超长必须截断，不能靠「模型名通常很短」的假设；</li>
 *   <li>渠道名会被写入外部网关，必须落在安全字符集内（输出仅 {@code [a-z0-9_-]}）；</li>
 *   <li>反解必须无歧义 ⇒ shortCode 中的 {@code -} 一并归一为 {@code _}，
 *       使第一个 {@code -} 之后即 slug 起点。</li>
 * </ul>
 *
 * <p>归一规则：保留 {@code -}（模型名常见分隔符，如 {@code gpt-4o}、{@code claude-3-5-sonnet}）；
 * 其余字符（含 {@code /}、{@code .}、空格、Unicode）一律压成单个 {@code _}；去除首尾 {@code _}。
 * 例：{@code anthropic/claude-3-5-sonnet → anthropic_claude-3-5-sonnet}、
 * {@code Qwen 2.5 Max → qwen_2_5_max}。
 *
 * <p>约定：命名是**确定性纯函数** —— 同输入必同输出（幂等的前提，见 `R-54`）。
 */
public final class ChannelNameGenerator {

    /** 渠道名前缀。 */
    public static final String PREFIX = "AAP-";

    /** 渠道名长度上限 = `aap_channel_binding.channel_name` 的列宽。 */
    public static final int MAX_LENGTH = 64;

    /** 截断时附加的哈希后缀长度。 */
    public static final int HASH_SUFFIX_LENGTH = 4;

    /** 归一后的占位 slug（空/纯符号模型名）。 */
    static final String FALLBACK_SLUG = "model";

    /** 保留字符判定（{@code keepDash} 控制是否保留连字符）。 */
    private static boolean isKeepable(char c, boolean keepDash) {
        return (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || (keepDash && c == '-');
    }

    private ChannelNameGenerator() {
    }

    /**
     * 生成模型级渠道名：{@code AAP-{shortCode}-{modelSlug}}。
     *
     * @param shortCode 供应商短码（可空/可含非法字符，本方法负责归一）
     * @param modelName 平台模型名（可含 {@code /}、空格、大写、Unicode 或超长）
     * @return 长度 ≤ {@link #MAX_LENGTH} 且字符集安全的确定性渠道名
     */
    public static String forModel(String shortCode, String modelName) {
        String shortPart = normalizeShort(shortCode);
        String slugPart = slug(modelName);
        String prefix = PREFIX + shortPart + "-";
        String full = prefix + slugPart;
        if (full.length() <= MAX_LENGTH) {
            return full;
        }
        // 超长：截断 slug 并附模型名哈希后缀，保证唯一性与确定性（R-55）
        String suffix = "-" + hashSuffix(modelName);
        int room = MAX_LENGTH - prefix.length() - suffix.length();
        if (room < 1) {
            // shortCode 本身过长：退化为「前缀 + 截断短码」，仍保留哈希后缀
            int keep = MAX_LENGTH - suffix.length() - PREFIX.length();
            if (keep < 1) {
                String minimal = PREFIX + hashSuffix(modelName);
                return minimal.length() <= MAX_LENGTH ? minimal : minimal.substring(0, MAX_LENGTH);
            }
            String cutShort = normalizeShort(shortCode);
            if (cutShort.length() > keep) {
                cutShort = cutShort.substring(0, keep);
            }
            return PREFIX + cutShort + suffix;
        }
        return prefix + slugPart.substring(0, room) + suffix;
    }

    /**
     * 归一化为 slug：转小写，保留 {@code [a-z0-9-]}，其余字符段落压成单个 {@code _}，
     * 去除首尾 {@code _}；结果为空时回落 {@link #FALLBACK_SLUG}。
     */
    static String slug(String raw) {
        return normalizeWith(raw, FALLBACK_SLUG, true);
    }

    /**
     * shortCode 归一：**不保留** {@code -}（归一为 {@code _}）—— 否则
     * {@code AAP-a-b-model} 无法确定切分点，反解会有歧义。
     */
    static String normalizeShort(String raw) {
        return normalizeWith(raw, "provider", false);
    }

    private static String normalizeWith(String raw, String fallback, boolean keepDash) {
        if (raw == null) {
            return fallback;
        }
        String lower = raw.toLowerCase(Locale.ROOT);
        StringBuilder sb = new StringBuilder(lower.length());
        boolean lastWasSeparator = false;
        for (int i = 0; i < lower.length(); i++) {
            char c = lower.charAt(i);
            if (isKeepable(c, keepDash)) {
                sb.append(c);
                lastWasSeparator = false;
            } else if (!lastWasSeparator) {
                sb.append('_');
                lastWasSeparator = true;
            }
        }
        String trimmed = trimUnderscores(sb.toString());
        return trimmed.isEmpty() ? fallback : trimmed;
    }

    private static String trimUnderscores(String s) {
        int start = 0;
        int end = s.length();
        while (start < end && s.charAt(start) == '_') {
            start++;
        }
        while (end > start && s.charAt(end - 1) == '_') {
            end--;
        }
        return s.substring(start, end);
    }

    /** 模型名的 4 位 SHA-256 十六进制前缀（确定性、抗碰撞）。 */
    private static String hashSuffix(String modelName) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(String.valueOf(modelName).getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash).substring(0, HASH_SUFFIX_LENGTH);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 不可用", e);
        }
    }

    /**
     * 反解渠道名。
     *
     * <p>注意：若原模型名超长被截断，slug 含哈希后缀，**不等于**原模型名 ——
     * 模型名的权威来源是 {@code aap_supply_unit.model_name}，本反解只保证
     * shortCode 可还原、slug 可定位（`R-55` 已声明该边界）。
     *
     * @return 解析成功返回 shortCode 与 slug；不符合命名规则返回 {@link Optional#empty()}
     */
    public static Optional<Parsed> parse(String channelName) {
        if (channelName == null || channelName.isBlank() || !channelName.startsWith(PREFIX)) {
            return Optional.empty();
        }
        String body = channelName.substring(PREFIX.length());
        int sep = body.indexOf('-');
        if (sep <= 0 || sep == body.length() - 1) {
            return Optional.empty();
        }
        String shortCode = body.substring(0, sep);
        String slug = body.substring(sep + 1);
        if (shortCode.isEmpty() || slug.isEmpty()) {
            return Optional.empty();
        }
        return Optional.of(new Parsed(shortCode, slug));
    }

    /** 反解结果。 */
    public record Parsed(String shortCode, String modelSlug) {
    }
}
