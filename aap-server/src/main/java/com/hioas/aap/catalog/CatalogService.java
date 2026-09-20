package com.hioas.aap.catalog;

import com.hioas.aap.common.CryptoService;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.JsonCodec;
import com.hioas.aap.common.ApiException;
import com.mybatisflex.core.query.QueryWrapper;
import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 模型目录服务 —— 解开 D-ADM-3。
 *
 * <p><b>它服务两个消费方，职责要分清：</b>
 * <ul>
 *   <li><b>管理端</b>：厂商 / 模型的增删改查（Calicat page-3、3.1、3.2）</li>
 *   <li><b>H5 供应商端</b>：{@link #availableModels()} 给「接入凭证」页提供模型下拉
 *       —— 这是这套接口存在的**真正目的**（用户 2026-09-20 指令）</li>
 * </ul>
 *
 * <p><b>不静默选边的三处（都显式暴露，不猜）：</b>
 * <ol>
 *   <li>价格单位：设计标「元/1K tokens」、H5 报价链用「$/1M token」→ 出参带 {@code priceUnit}
 *       原样透出设计口径，**不做换算**（D-ADM-4 待裁定）。</li>
 *   <li>API Key：只存密文、只回脱敏串。设计写「仅管理员可见」指的是**可写入/可覆盖**，不是可读回明文。</li>
 *   <li>{@code enabled=false} 的厂商/模型不进 H5 可用清单，但管理端列表**仍全部可见**
 *       （否则停用后就再也找不回来）。</li>
 * </ol>
 */
@Service
public class CatalogService {

    /** 设计 page-3-2 标注的价格单位（元 / 1K tokens）—— 原样透出，不做换算。 */
    static final String PRICE_UNIT = "CNY/1K";

    private final VendorMapper vendorMapper;
    private final ModelCatalogMapper modelMapper;
    private final CryptoService crypto;

    public CatalogService(VendorMapper vendorMapper, ModelCatalogMapper modelMapper,
                          CryptoService crypto) {
        this.vendorMapper = vendorMapper;
        this.modelMapper = modelMapper;
        this.crypto = crypto;
    }

    /* ------------------------------------------------------------------ 读（管理端） */

    /** 管理端厂商列表 —— 含停用项（停用也要能看到并恢复），带各厂商的模型数。 */
    public List<CatalogViews.Vendor> listVendors() {
        List<VendorEntity> vendors = vendorMapper.selectListByQuery(
                QueryWrapper.create().orderBy("created_at", false));
        List<ModelCatalogEntity> models = modelMapper.selectListByQuery(QueryWrapper.create());
        Map<Long, Long> counts = new LinkedHashMap<>();
        for (ModelCatalogEntity m : models) {
            counts.merge(m.getVendorId(), 1L, Long::sum);
        }
        List<CatalogViews.Vendor> out = new ArrayList<>();
        for (VendorEntity v : vendors) {
            out.add(toVendor(v, counts.getOrDefault(v.getId(), 0L)));
        }
        return out;
    }

    /** 管理端模型列表（可按厂商过滤）。 */
    public List<CatalogViews.Model> listModels(String vendorId) {
        QueryWrapper q = QueryWrapper.create();
        if (vendorId != null && !vendorId.isBlank()) {
            q.and("vendor_id = ?", parseId(vendorId, "vendorId"));
        }
        q.orderBy("created_at", false);
        Map<Long, VendorEntity> vendors = vendorIndex();
        List<CatalogViews.Model> out = new ArrayList<>();
        for (ModelCatalogEntity m : modelMapper.selectListByQuery(q)) {
            out.add(toModel(m, vendors.get(m.getVendorId())));
        }
        return out;
    }

    /** 设计 page-3 是「按厂商分组」列表 → 直接按组返回，省得前端再拼。 */
    public List<CatalogViews.VendorGroup> listGroupedByVendor() {
        Map<Long, VendorEntity> vendors = vendorIndex();
        Map<Long, List<CatalogViews.Model>> byVendor = new LinkedHashMap<>();
        for (ModelCatalogEntity m : modelMapper.selectListByQuery(
                QueryWrapper.create().orderBy("created_at", false))) {
            byVendor.computeIfAbsent(m.getVendorId(), k -> new ArrayList<>())
                    .add(toModel(m, vendors.get(m.getVendorId())));
        }
        List<CatalogViews.VendorGroup> out = new ArrayList<>();
        for (CatalogViews.Vendor v : listVendors()) {
            out.add(new CatalogViews.VendorGroup(v, byVendor.getOrDefault(v.id(), List.of())));
        }
        return out;
    }

    /* ------------------------------------------------------- 读（H5 供应商端 · 关键） */

    /**
     * <b>可用模型清单 —— H5 端「接入凭证」页的模型下拉数据源。</b>
     *
     * <p>只返回「厂商启用 **且** 模型启用」的项：停用的模型不该出现在供应商的可选列表里
     * （设计 page-3-2 原文「启用后该模型将加入可用模型池」）。
     *
     * <p>返回的 {@code modelUid} 就是最终进凭证 {@code model_list} 的标识。
     */
    public List<CatalogViews.Model> availableModels() {
        Map<Long, VendorEntity> vendors = vendorIndex();
        List<CatalogViews.Model> out = new ArrayList<>();
        for (ModelCatalogEntity m : modelMapper.selectListByQuery(
                QueryWrapper.create().orderBy("model_uid", true))) {
            VendorEntity v = vendors.get(m.getVendorId());
            if (v == null || !Boolean.TRUE.equals(v.getEnabled())) {
                continue; // 厂商停用 → 其模型一并不可选
            }
            if (!Boolean.TRUE.equals(m.getEnabled())) {
                continue; // 模型未启用 → 不进可用池
            }
            out.add(toModel(m, v));
        }
        out.sort(Comparator.comparing(CatalogViews.Model::vendorName,
                Comparator.nullsLast(Comparator.naturalOrder()))
                .thenComparing(CatalogViews.Model::modelUid,
                        Comparator.nullsLast(Comparator.naturalOrder())));
        return out;
    }

    /* ------------------------------------------------------------------ 写（管理端） */

    @Transactional
    public CatalogViews.Vendor createVendor(CatalogViews.VendorRequest req) {
        requireText(req.name(), "厂商名称", "V1");
        requireText(req.vendorKey(), "厂商标识", "V2");
        requireText(req.vendorType(), "厂商类型", "V3");
        requireText(req.baseUrl(), "API Base URL", "V4");
        if (!vendorMapper.selectListByQuery(
                QueryWrapper.create().and("vendor_key = ?", req.vendorKey())).isEmpty()) {
            throw new ApiException(ErrorCode.E_1001, "厂商标识已存在：" + req.vendorKey());
        }
        VendorEntity v = new VendorEntity();
        v.setName(req.name());
        v.setVendorKey(req.vendorKey());
        v.setVendorType(req.vendorType());
        v.setRegion(req.region());
        v.setWebsite(req.website());
        v.setBaseUrl(req.baseUrl());
        v.setApiKeyCipher(cipher(req.apiKey()));
        v.setDefaultQps(req.defaultQps());
        v.setCurrency(req.currency());
        v.setEnabled(req.enabled() == null || req.enabled());
        v.setDescription(req.description());
        vendorMapper.insert(v);
        return toVendor(v, 0L);
    }

    @Transactional
    public CatalogViews.Model createModel(CatalogViews.ModelRequest req) {
        requireText(req.vendorId(), "所属厂商", "V1");
        requireText(req.modelName(), "模型名称", "V2");
        requireText(req.modelUid(), "模型标识", "V3");
        requireText(req.modelType(), "模型类型", "V4");
        long vendorId = parseId(req.vendorId(), "vendorId");
        VendorEntity vendor = vendorMapper.selectOneById(vendorId);
        if (vendor == null) {
            throw new ApiException(ErrorCode.E_1406, "所属厂商不存在");
        }
        if (!Boolean.TRUE.equals(vendor.getEnabled())) {
            throw new ApiException(ErrorCode.E_1001,
                    "该厂商已停用，无法在其下新增模型（设计：启用后可在新增模型时选择该厂商）");
        }
        if (!modelMapper.selectListByQuery(
                QueryWrapper.create().and("model_uid = ?", req.modelUid())).isEmpty()) {
            throw new ApiException(ErrorCode.E_1001, "模型标识已存在：" + req.modelUid());
        }
        ModelCatalogEntity m = new ModelCatalogEntity();
        m.setVendorId(vendorId);
        m.setModelName(req.modelName());
        m.setModelUid(req.modelUid());
        m.setModelType(req.modelType());
        m.setContextWindow(req.contextWindow());
        m.setMaxOutput(req.maxOutput());
        m.setInputPrice(req.inputPrice());
        m.setOutputPrice(req.outputPrice());
        m.setCapabilities(writeCaps(req.capabilities()));
        m.setBaseUrl(req.baseUrl());
        m.setApiKeyCipher(cipher(req.apiKey()));
        m.setEnabled(req.enabled() == null || req.enabled());
        m.setRemark(req.remark());
        modelMapper.insert(m);
        return toModel(m, vendor);
    }

    @Transactional
    public CatalogViews.Model updateModel(String id, CatalogViews.ModelRequest req) {
        ModelCatalogEntity m = modelMapper.selectOneById(parseId(id, "id"));
        if (m == null) {
            throw new ApiException(ErrorCode.E_1406, "模型不存在");
        }
        if (req.modelName() != null) {
            m.setModelName(req.modelName());
        }
        if (req.modelType() != null) {
            m.setModelType(req.modelType());
        }
        if (req.contextWindow() != null) {
            m.setContextWindow(req.contextWindow());
        }
        if (req.maxOutput() != null) {
            m.setMaxOutput(req.maxOutput());
        }
        if (req.inputPrice() != null) {
            m.setInputPrice(req.inputPrice());
        }
        if (req.outputPrice() != null) {
            m.setOutputPrice(req.outputPrice());
        }
        if (req.capabilities() != null) {
            m.setCapabilities(writeCaps(req.capabilities()));
        }
        if (req.baseUrl() != null) {
            m.setBaseUrl(req.baseUrl());
        }
        if (req.apiKey() != null && !req.apiKey().isBlank()) {
            m.setApiKeyCipher(cipher(req.apiKey())); // 留空 = 不改动现有密钥
        }
        if (req.enabled() != null) {
            m.setEnabled(req.enabled());
        }
        if (req.remark() != null) {
            m.setRemark(req.remark());
        }
        modelMapper.update(m);
        return toModel(m, vendorMapper.selectOneById(m.getVendorId()));
    }

    /* ------------------------------------------------------------------ 内部 */

    private Map<Long, VendorEntity> vendorIndex() {
        Map<Long, VendorEntity> idx = new LinkedHashMap<>();
        for (VendorEntity v : vendorMapper.selectListByQuery(QueryWrapper.create())) {
            idx.put(v.getId(), v);
        }
        return idx;
    }

    private CatalogViews.Vendor toVendor(VendorEntity v, long modelCount) {
        return new CatalogViews.Vendor(v.getId(), v.getName(), v.getVendorKey(), v.getVendorType(),
                v.getRegion(), v.getWebsite(), v.getBaseUrl(), mask(v.getApiKeyCipher()),
                v.getDefaultQps(), v.getCurrency(), v.getEnabled(), v.getDescription(), modelCount);
    }

    private CatalogViews.Model toModel(ModelCatalogEntity m, VendorEntity v) {
        return new CatalogViews.Model(m.getId(), m.getVendorId(),
                v == null ? null : v.getName(), v == null ? null : v.getVendorKey(),
                m.getModelName(), m.getModelUid(), m.getModelType(), m.getContextWindow(),
                m.getMaxOutput(), m.getInputPrice(), m.getOutputPrice(), PRICE_UNIT,
                readCaps(m.getCapabilities()), m.getBaseUrl(), m.getEnabled(), m.getRemark());
    }

    /** 密文 → 脱敏串；无密钥时回 null（而不是空串，避免前端渲染出空「••••」）。 */
    private String mask(String cipher) {
        if (cipher == null || cipher.isBlank()) {
            return null;
        }
        try {
            return crypto.maskApiKey(crypto.decrypt(cipher));
        } catch (RuntimeException e) {
            // 密钥轮换 / 历史脏数据：脱敏失败不能把整个列表打挂，退化为固定占位
            return "••••••••";
        }
    }

    private String cipher(String plain) {
        return plain == null || plain.isBlank() ? null : crypto.encrypt(plain);
    }

    private String writeCaps(List<String> caps) {
        if (caps == null || caps.isEmpty()) {
            return null;
        }
        try {
            return JsonCodec.toJson(caps);
        } catch (RuntimeException e) {
            throw new ApiException(ErrorCode.E_1001, "能力标签格式不合法");
        }
    }

    private List<String> readCaps(String raw) {
        if (raw == null || raw.isBlank()) {
            return List.of();
        }
        try {
            return JsonCodec.toStringList(raw);
        } catch (RuntimeException e) {
            return List.of();
        }
    }

    private void requireText(String v, String label, String rule) {
        if (v == null || v.isBlank()) {
            throw new ApiException(ErrorCode.E_1001, label + "必填（" + rule + "）");
        }
    }

    private long parseId(String raw, String label) {
        try {
            return Long.parseLong(raw);
        } catch (RuntimeException e) {
            throw new ApiException(ErrorCode.E_1001, label + " 不是合法 id：" + raw);
        }
    }
}
