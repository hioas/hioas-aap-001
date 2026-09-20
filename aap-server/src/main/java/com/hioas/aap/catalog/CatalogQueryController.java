package com.hioas.aap.catalog;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.catalog.CatalogViews.Model;
import java.util.List;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 供应商侧：可用模型清单 —— <b>H5 端「接入凭证」页的模型下拉数据源</b>。
 *
 * <p>这是整套模型目录接口存在的**真正目的**（用户 2026-09-20 指令原文：
 * 「改接口就是为 h5 端接入凭证时，提供下拉选择的模型列表」）。
 *
 * <p>与 {@link AdminCatalogController} 的区别，刻意分成两个控制器：
 * <ul>
 *   <li>权限面不同：这里供应商即可读；管理端那些接口供应商一律 403</li>
 *   <li>可见范围不同：这里只出「厂商启用 + 模型启用」，停用项不外泄；
 *       管理端要能看到停用项以便恢复</li>
 *   <li>出参剥掉管理信息：不含 {@code apiKeyMask} 等管理端字段</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/v1/catalog")
@PreAuthorize("hasAnyRole('SUPPLIER','PROVIDER','BIZ_OPERATOR','TECH_OPS','SUPER_ADMIN')")
public class CatalogQueryController {

    private final CatalogService catalogService;

    public CatalogQueryController(CatalogService catalogService) {
        this.catalogService = catalogService;
    }

    /**
     * 可用模型清单（仅启用项）。
     *
     * <p>前端用法：凭证页把返回项的 {@code modelUid} 作为可选项，
     * 选中后写进凭证的 {@code model_list}（契约要求**对象数组**，
     * 见 {@code docs/backend/json-schema/models/model-entry.schema.json}）。
     */
    @GetMapping("/models")
    public ApiEnvelope<List<Model>> availableModels() {
        return ApiEnvelope.ok(catalogService.availableModels());
    }
}
