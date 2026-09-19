package com.hioas.aap.file;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.hioas.aap.common.CryptoService;
import com.hioas.aap.common.ErrorCode;
import com.hioas.aap.common.ApiException;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.Locale;
import java.util.Set;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 文件服务（补缺陷2）。
 *
 * <p>职责：把上传的字节写进 {@link StorageBackend}，并在 {@code aap_file_asset} 落一行，
 * 返回对外的 {@code file_id}。此前该表**零 INSERT**，导致：
 * <ul>
 *   <li>{@code POST /admin/contracts/{id}/issue} 的 {@code file_id} 无处可得 → 合同永远签发不了</li>
 *   <li>{@code GET /contracts/{id}/file} 必然 E-1406「合同文件不存在」</li>
 *   <li>资质上传（{@code POST /provider/qualifications}）只能存元数据，取不到文件本体</li>
 * </ul>
 *
 * <p><b>安全边界</b>：扩展名白名单 + 单文件大小上限 + key 由本服务生成（不接受调用方传 key，
 * 避免路径穿越与命名冲突）。
 */
@Service
public class FileService {

    /** 允许的扩展名（与资质上传的白名单一致，避免两处规则打架）。 */
    private static final Set<String> ALLOWED_EXTENSIONS =
            Set.of("jpg", "jpeg", "png", "pdf", "txt", "csv", "xlsx", "docx");

    /** 单文件上限 10MB（与 qualification-create 契约的 maximum: 10485760 一致）。 */
    private static final long MAX_FILE_BYTES = 10L * 1024 * 1024;

    private static final DateTimeFormatter MONTH = DateTimeFormatter.ofPattern("yyyyMM");

    private final StorageBackend storage;
    private final FileAssetMapper mapper;
    private final CryptoService crypto;

    public FileService(StorageBackend storage, FileAssetMapper mapper, CryptoService crypto) {
        this.storage = storage;
        this.mapper = mapper;
        this.crypto = crypto;
    }

    /** 对外视图（字段名对齐 {@code models/file-asset.schema.json}）。 */
    public record View(
            @JsonProperty("file_id") String fileId,
            @JsonProperty("file_name") String fileName,
            @JsonProperty("size") Long size,
            @JsonProperty("size_bytes") Long sizeBytes,
            @JsonProperty("content_type") String contentType,
            @JsonProperty("type") String type,
            @JsonProperty("sha256") String sha256,
            @JsonProperty("uploaded_at") String uploadedAt,
            @JsonProperty("url") String url) {
    }

    /**
     * 上传：写入存储 + 落库 + 返回视图。
     *
     * @param content      文件字节（空 → E-1001）
     * @param originalName 原始文件名（扩展名决定存储键与校验）
     * @param contentType  声明的 MIME（可空，仅作记录）
     * @param bizType      业务类型（CONTRACT / QUALIFICATION / VOUCHER…，可空）
     */
    @Transactional
    public View upload(byte[] content, String originalName, String contentType, String bizType) {
        if (content == null || content.length == 0) {
            throw ApiException.field(ErrorCode.E_1001, "file", "文件内容不能为空");
        }
        if (content.length > MAX_FILE_BYTES) {
            throw ApiException.field(ErrorCode.E_1001, "file", "单个文件不超过 10MB");
        }
        String name = originalName == null || originalName.isBlank() ? "unnamed" : originalName.trim();
        String extension = extensionOf(name);
        if (!ALLOWED_EXTENSIONS.contains(extension)) {
            throw ApiException.field(ErrorCode.E_1001, "file",
                    "不支持的文件类型 ." + extension + "（允许 " + String.join(" / ", ALLOWED_EXTENSIONS) + "）");
        }

        String type = (bizType == null || bizType.isBlank()) ? "OTHER" : bizType.trim().toUpperCase(Locale.ROOT);
        String sha256 = crypto.sha256Hex(content);

        FileAssetEntity entity = new FileAssetEntity();
        // 先落库拿到雪花 id，再据此生成 key —— 保证 key 唯一且可回溯
        entity.setFileKey("pending");
        entity.setBucket("local");
        entity.setOriginalName(name);
        entity.setContentType(contentType);
        entity.setSizeBytes((long) content.length);
        entity.setSha256(sha256);
        entity.setBizType(type);
        entity.setEncrypted(false);
        entity.setStatus("ACTIVE");
        mapper.insert(entity);

        String key = "%s/%s/%d%s".formatted(
                type,
                MONTH.format(OffsetDateTime.now(ZoneOffset.UTC)),
                entity.getId(),
                extension.isEmpty() ? "" : "." + extension);
        storage.put(key, content);

        entity.setFileKey(key);
        mapper.update(entity);

        return toView(entity);
    }

    /** 读取文件本体（不存在 → E-1406，不是 500）。 */
    public Loaded load(Long fileId) {
        FileAssetEntity entity = mapper.selectOneById(fileId);
        if (entity == null || Boolean.TRUE.equals(entity.getDeleted())) {
            throw new ApiException(ErrorCode.E_1406, "文件不存在：" + fileId);
        }
        try {
            byte[] bytes = storage.get(entity.getFileKey());
            return new Loaded(entity, bytes);
        } catch (StorageObjectNotFoundException e) {
            // 元数据在但对象丢了：属数据不一致，仍按「资源不存在」回，且信息可定位
            throw new ApiException(ErrorCode.E_1406, "文件对象缺失（元数据存在但存储无对象）：" + entity.getFileKey());
        }
    }

    /** 文件是否可用（合同签发前的引用校验用）。 */
    public boolean exists(Long fileId) {
        FileAssetEntity entity = fileId == null ? null : mapper.selectOneById(fileId);
        return entity != null && !Boolean.TRUE.equals(entity.getDeleted());
    }

    public record Loaded(FileAssetEntity asset, byte[] content) {
    }

    private View toView(FileAssetEntity e) {
        return new View(
                String.valueOf(e.getId()),
                e.getOriginalName(),
                e.getSizeBytes(),
                e.getSizeBytes(),
                e.getContentType(),
                e.getBizType(),
                e.getSha256(),
                e.getCreatedAt() == null ? null
                        : DateTimeFormatter.ISO_INSTANT.format(e.getCreatedAt().withOffsetSameInstant(ZoneOffset.UTC)),
                "/api/v1/files/" + e.getId());
    }

    private static String extensionOf(String fileName) {
        int dot = fileName.lastIndexOf('.');
        return dot < 0 ? "" : fileName.substring(dot + 1).toLowerCase(Locale.ROOT);
    }
}
