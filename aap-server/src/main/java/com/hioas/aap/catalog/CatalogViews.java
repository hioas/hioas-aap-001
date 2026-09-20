package com.hioas.aap.catalog;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.math.BigDecimal;
import java.util.List;

/**
 * 模型目录对外视图（Calicat page-3 / 3.1 / 3.2 的字段一一对应）。
 *
 * <p>⚠️ <b>雪花 ID 必须序列化为字符串</b>（{@code @JsonFormat(shape = STRING)}）——
 * 契约原文见 {@code docs/backend/json-schema/models/audit-log.schema.json}：
 * 「雪花 ID（对外 string，避免 JS 精度丢失）」。本项目 ID 是 18 位雪花
 * （实测 459074703791419392），超过 JS 安全整数上限 2^53，
 * 若按 JSON number 下发，任何 JS 客户端（浏览器 / 小程序）解析后再回传都会打到**错的 ID**上。
 * 这个缺陷 Java 侧测试完全发现不了（Java 的 Long 没有精度问题），
 * 是运行态验收里「建完厂商紧接着用它的 id 建模型」才暴露出来的。
 *
 * <p><b>两条边界，写在这里而不是散在控制器里：</b>
 * <ol>
 *   <li>API Key 一律**不回传**：出参只有 {@code apiKeyMask}（脱敏尾号）。设计稿写的就是
 *       「加密存储，仅管理员可见」「加密存储，可在单模型覆盖」——「可见」指可覆盖写入，不是可读回明文。</li>
 *   <li>{@code priceUnit} 显式带出单位口径，避免前端按错量纲渲染 ——
 *       设计标「元/1K tokens」而 H5 报价链用「$/1M token」（见 V9 迁移头部 D-ADM-4，待裁定）。</li>
 * </ol>
 */
public final class CatalogViews {

    private CatalogViews() {
    }

    /** 厂商（管理端列表 / 新增模型抽屉的厂商下拉）。 */
    public record Vendor(@JsonFormat(shape = JsonFormat.Shape.STRING) Long id,
                         String name,
                         String vendorKey,
                         String vendorType,
                         String region,
                         String website,
                         String baseUrl,
                         String apiKeyMask,
                         Integer defaultQps,
                         String currency,
                         Boolean enabled,
                         String description,
                         long modelCount) {
    }

    /** 模型（管理端列表 / H5 凭证页下拉）。 */
    public record Model(@JsonFormat(shape = JsonFormat.Shape.STRING) Long id,
                        @JsonFormat(shape = JsonFormat.Shape.STRING) Long vendorId,
                        String vendorName,
                        String vendorKey,
                        String modelName,
                        String modelUid,
                        String modelType,
                        Integer contextWindow,
                        Integer maxOutput,
                        BigDecimal inputPrice,
                        BigDecimal outputPrice,
                        String priceUnit,
                        List<String> capabilities,
                        String baseUrl,
                        Boolean enabled,
                        String remark) {
    }

    /** 按厂商分组（设计 page-3 是「按厂商分组（浅色）」列表）。 */
    public record VendorGroup(Vendor vendor, List<Model> models) {
    }

    /** 新增模型的入参。 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record ModelRequest(String vendorId,
                              String modelName,
                              String modelUid,
                              String modelType,
                              Integer contextWindow,
                              Integer maxOutput,
                              BigDecimal inputPrice,
                              BigDecimal outputPrice,
                              List<String> capabilities,
                              String baseUrl,
                              String apiKey,
                              Boolean enabled,
                              String remark) {
    }

    /** 新增厂商的入参。 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record VendorRequest(String name,
                                String vendorKey,
                                String vendorType,
                                String region,
                                String website,
                                String baseUrl,
                                String apiKey,
                                Integer defaultQps,
                                String currency,
                                Boolean enabled,
                                String description) {
    }
}
