package com.hioas.aap.sync;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * 渠道配置校验器（T-M4-06）—— 供给单元 → 渠道配置的合法性闸门。
 *
 * <p>规格：`specs/001-intake-automation/spec.md` §6 `R-56`（PER_MODEL 下 models 必须恰为一个模型）、
 * `R-54`（命名确定性）、`R-55`（长度上限）、`R-36`（tag）与 §7 `AC-20`。
 *
 * <p>设计为**纯函数**：返回违规清单而非抛异常 —— 便于单测、便于把每一条违规定位到具体字段
 * （与既有 `QuoteConflictValidator` 的「定位到字段」口径一致）。
 *
 * <p>为什么硬拦多模型：`aap_channel_binding.models` 是 jsonb 数组，历史上承载多模型（合并渠道）。
 * 一模型一渠道之后若仍写入多元素数组，网关会把该渠道同时用于多个模型，
 * 「模型级调度（priority/weight/auto_ban 按模型生效）」的前提直接失效。
 */
public final class ChannelConfigValidator {

    /** 模型级粒度。 */
    public static final String PER_MODEL = "PER_MODEL";

    /** 供应商级（合并）粒度 —— DR-03 保留的既有能力。 */
    public static final String PER_PROVIDER = "PER_PROVIDER";

    private ChannelConfigValidator() {
    }

    /**
     * 校验渠道配置草稿。
     *
     * @return 违规清单（空表示合法）；每条含规则编号与可读原因
     */
    public static List<String> validate(Draft draft) {
        List<String> violations = new ArrayList<>();
        if (draft == null) {
            violations.add("R-56 渠道配置为空");
            return violations;
        }
        String granularity = draft.granularity() == null ? "" : draft.granularity().trim().toUpperCase(Locale.ROOT);
        if (!PER_MODEL.equals(granularity) && !PER_PROVIDER.equals(granularity)) {
            violations.add("granularity 非法：" + draft.granularity() + "（仅允许 PER_MODEL / PER_PROVIDER）");
            return violations;
        }

        List<String> models = draft.models() == null ? List.of() : draft.models();
        if (models.isEmpty()) {
            violations.add("R-56 models 不得为空：至少一个模型");
        }
        boolean hasBlank = false;
        for (String model : models) {
            if (model == null || model.isBlank()) {
                hasBlank = true;
            }
        }
        if (hasBlank) {
            violations.add("R-56 models 含空元素");
        }

        List<String> cleaned = models.stream()
                .filter(m -> m != null && !m.isBlank())
                .map(String::trim)
                .toList();

        if (PER_MODEL.equals(granularity)) {
            if (cleaned.size() != 1) {
                violations.add("R-56 PER_MODEL 渠道的 models 必须恰好 1 个模型，实际 " + cleaned.size() + " 个");
            } else {
                String only = cleaned.get(0);
                String modelName = draft.modelName() == null ? null : draft.modelName().trim();
                if (modelName == null || !only.equals(modelName)) {
                    violations.add("R-56 models[" + only + "] 与 model_name[" + draft.modelName() + "] 不一致");
                }
            }
        }

        validateBaseUrl(draft.baseUrl(), violations);

        if (draft.tag() == null || draft.tag().isBlank()) {
            violations.add("R-36 tag 必填（按供应商打标，批量启停的基础）");
        }

        if (draft.weight() != null && draft.weight() < 0) {
            violations.add("weight 不得为负：" + draft.weight());
        }

        validateChannelName(draft, granularity, violations);
        return violations;
    }

    private static void validateBaseUrl(String baseUrl, List<String> violations) {
        if (baseUrl == null || baseUrl.isBlank()) {
            violations.add("base_url 必填");
            return;
        }
        String lower = baseUrl.trim().toLowerCase(Locale.ROOT);
        if (!lower.startsWith("http://") && !lower.startsWith("https://")) {
            violations.add("base_url 必须为 http/https：" + baseUrl);
        }
    }

    private static void validateChannelName(Draft draft, String granularity, List<String> violations) {
        String name = draft.channelName();
        if (name == null || name.isBlank()) {
            violations.add("R-54 channel_name 必填");
            return;
        }
        if (name.length() > ChannelNameGenerator.MAX_LENGTH) {
            violations.add("R-55 channel_name 长度 " + name.length()
                    + " 超过上限 " + ChannelNameGenerator.MAX_LENGTH);
        }
        if (PER_MODEL.equals(granularity)) {
            String expected = ChannelNameGenerator.forModel(draft.providerShortCode(), draft.modelName());
            if (!expected.equals(name)) {
                violations.add("R-54 channel_name[" + name + "] 与命名规则不一致，应为 " + expected);
            }
        } else {
            // 合并渠道沿用 AAP-{short}-{seq}：只校验前缀与短码，避免与模型级渠道混淆
            String prefix = ChannelNameGenerator.PREFIX
                    + ChannelNameGenerator.normalizeShort(draft.providerShortCode()) + "-";
            if (!name.startsWith(prefix)) {
                violations.add("R-54 合并渠道 channel_name[" + name + "] 必须以 " + prefix + " 开头");
            }
        }
    }

    /**
     * 渠道配置草稿。
     *
     * @param providerShortCode 供应商短码
     * @param modelName         平台模型名（PER_PROVIDER 合并模式下为 null）
     * @param models            该渠道覆盖的模型清单（PER_MODEL 下必须恰好 1 个）
     * @param baseUrl           上游地址
     * @param tag               渠道标签（R-36：= provider_code）
     * @param granularity       PER_MODEL / PER_PROVIDER
     * @param weight            同优先级随机权重
     * @param channelName       渠道名（必须与命名器输出一致）
     */
    public record Draft(String providerShortCode,
                        String modelName,
                        List<String> models,
                        String baseUrl,
                        String tag,
                        String granularity,
                        Integer weight,
                        String channelName) {
    }
}
