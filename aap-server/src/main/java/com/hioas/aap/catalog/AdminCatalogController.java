package com.hioas.aap.catalog;

import com.hioas.aap.common.ApiEnvelope;
import com.hioas.aap.catalog.CatalogViews.Model;
import com.hioas.aap.catalog.CatalogViews.ModelRequest;
import com.hioas.aap.catalog.CatalogViews.Vendor;
import com.hioas.aap.catalog.CatalogViews.VendorGroup;
import com.hioas.aap.catalog.CatalogViews.VendorRequest;
import java.util.List;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * 管理端模型目录（Calicat page-3「模型管理」/ 3.1「新增厂商」/ 3.2「新增模型」）。
 *
 * <p><b>为什么会有这个控制器</b>：此前管理端「新增模型」整页**后端零能力**
 * （全仓只有 {@code GET /admin/sync/models/upstream}，实测 E-1501），前端只能标注
 * 「后端未提供接口，本次未发出任何请求」。本控制器补上缺口（D-ADM-3）。
 *
 * <p>权限：与其它管理端写接口一致 —— 读放开给技术运营（只读角色），写仅超管 + 运营商务。
 * 理由同 `13-管理端PRD.md` §5：配置类写入会影响供应商可见的模型池，必须收权。
 */
@RestController
@RequestMapping("/api/v1/admin/catalog")
@PreAuthorize("hasAnyRole('BIZ_OPERATOR','TECH_OPS','SUPER_ADMIN')")
public class AdminCatalogController {

    private final CatalogService catalogService;

    public AdminCatalogController(CatalogService catalogService) {
        this.catalogService = catalogService;
    }

    /** ADM-M01 厂商列表（含停用项，供恢复）；设计 page-3-1。 */
    @GetMapping("/vendors")
    public ApiEnvelope<List<Vendor>> vendors() {
        return ApiEnvelope.ok(catalogService.listVendors());
    }

    /** ADM-M02 新增厂商（设计 page-3-1 抽屉）。 */
    @PostMapping("/vendors")
    @PreAuthorize("hasAnyRole('BIZ_OPERATOR','SUPER_ADMIN')")
    public ApiEnvelope<Vendor> createVendor(@RequestBody VendorRequest request) {
        return ApiEnvelope.ok(catalogService.createVendor(request));
    }

    /** ADM-M03 模型列表（`vendorId` 可选过滤）；设计 page-3 主列表。 */
    @GetMapping("/models")
    public ApiEnvelope<List<Model>> models(@RequestParam(required = false) String vendorId) {
        return ApiEnvelope.ok(catalogService.listModels(vendorId));
    }

    /** ADM-M04 按厂商分组（设计 page-3 是分组列表；避免前端重复拼装）。 */
    @GetMapping("/models/grouped")
    public ApiEnvelope<List<VendorGroup>> grouped() {
        return ApiEnvelope.ok(catalogService.listGroupedByVendor());
    }

    /** ADM-M05 新增模型（设计 page-3-2 抽屉）。 */
    @PostMapping("/models")
    @PreAuthorize("hasAnyRole('BIZ_OPERATOR','SUPER_ADMIN')")
    public ApiEnvelope<Model> createModel(@RequestBody ModelRequest request) {
        return ApiEnvelope.ok(catalogService.createModel(request));
    }

    /** ADM-M06 修改模型（含启用/停用；`api_key` 留空表示不改动现有密钥）。 */
    @PutMapping("/models/{id}")
    @PreAuthorize("hasAnyRole('BIZ_OPERATOR','SUPER_ADMIN')")
    public ApiEnvelope<Model> updateModel(@PathVariable String id,
                                          @RequestBody ModelRequest request) {
        return ApiEnvelope.ok(catalogService.updateModel(id, request));
    }
}
