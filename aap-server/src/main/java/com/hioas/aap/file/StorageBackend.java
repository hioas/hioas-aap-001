package com.hioas.aap.file;

/**
 * 存储后端抽象。
 *
 * <p>为什么要有这层：文件本体不落数据库，落哪里是可替换的运维决策
 * （本地盘 / S3 / 腾讯 COS / MinIO）。业务层只认 key，不认实现，
 * 这样换存储不用改 {@code FileService} 与合同/资质等调用方。
 *
 * <p>约定：{@code key} 是**相对路径**（如 {@code CONTRACT/202609/4589xxx.pdf}），
 * 不带 root 前缀；实现负责拼 root。key 由 {@link FileService} 统一生成，
 * 调用方不得自行拼 key（避免路径穿越与命名冲突）。
 */
public interface StorageBackend {

    /** 写入并返回实际使用的 key（幂等：同 key 覆盖）。 */
    String put(String key, byte[] content);

    /** 读取；对象不存在时抛 {@link StorageObjectNotFoundException}。 */
    byte[] get(String key);

    boolean exists(String key);

    /** 逻辑删除底层对象（实现可选择软删或真删）。 */
    void delete(String key);
}
