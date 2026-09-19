package com.hioas.aap.file;

import com.hioas.aap.common.ApiEnvelope;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

/**
 * 文件服务（补缺陷2）。
 *
 * <p>真源：{@code docs/backend/json-schema/models/file-asset.schema.json} 定义了文件资产视图；
 * {@code requests/contract-issue.schema.json} 把 {@code file_id} 列为 **required** ——
 * 但此前全仓没有任何途径产生 {@code file_id}（{@code aap_file_asset} 零 INSERT）。
 *
 * <p>端点：
 * <ul>
 *   <li>{@code POST /api/v1/files} —— multipart 上传（字段名 {@code file}），返回 file-asset 视图</li>
 *   <li>{@code GET  /api/v1/files/{id}} —— 下载文件本体</li>
 * </ul>
 *
 * <p>鉴权：需登录（与其余业务接口一致）。归属校验由各业务域自己做
 * （例如合同只能由相关方取自己的合同文件）—— 本控制器只负责「按 id 取文件」。
 */
@RestController
@RequestMapping("/api/v1/files")
public class FileController {

    private final FileService fileService;

    public FileController(FileService fileService) {
        this.fileService = fileService;
    }

    /** 上传。字段名固定 {@code file}；{@code biz_type} 可选（CONTRACT / QUALIFICATION / VOUCHER…）。 */
    @PostMapping
    public ApiEnvelope<FileService.View> upload(@RequestParam("file") MultipartFile file,
                                                @RequestParam(value = "biz_type", required = false) String bizType) {
        if (file == null) {
            throw new IllegalArgumentException("缺少文件字段 file");
        }
        byte[] content;
        try {
            content = file.getBytes();
        } catch (java.io.IOException e) {
            throw new IllegalStateException("读取上传内容失败", e);
        }
        return ApiEnvelope.ok(fileService.upload(content, file.getOriginalFilename(), file.getContentType(), bizType));
    }

    /** 下载：返回二进制流，带原始文件名（Content-Disposition，RFC 5987 编码支持中文名）。 */
    @GetMapping("/{id}")
    public ResponseEntity<byte[]> download(@PathVariable String id) {
        FileService.Loaded loaded = fileService.load(parseId(id));
        FileAssetEntity asset = loaded.asset();
        String fileName = asset.getOriginalName() == null ? "download" : asset.getOriginalName();
        String encoded = URLEncoder.encode(fileName, StandardCharsets.UTF_8).replace("+", "%20");
        MediaType mediaType = asset.getContentType() == null
                ? MediaType.APPLICATION_OCTET_STREAM
                : MediaType.parseMediaType(asset.getContentType());
        return ResponseEntity.ok()
                .contentType(mediaType)
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\"" + encoded + "\"; filename*=UTF-8''" + encoded)
                .contentLength(loaded.content().length)
                .body(loaded.content());
    }

    private Long parseId(String value) {
        try {
            return Long.valueOf(value);
        } catch (NumberFormatException e) {
            throw new com.hioas.aap.common.ApiException(com.hioas.aap.common.ErrorCode.E_1406, "文件不存在：" + value);
        }
    }
}
