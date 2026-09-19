package com.hioas.aap.file;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * 本地盘存储实现（默认后端）。
 *
 * <p>配置：{@code app.storage.local-root}（默认 {@code ./data/files}）。
 * 生产若换对象存储，只需再提供一个 {@link StorageBackend} 实现并标注 {@code @Primary}，
 * 业务代码不动。
 *
 * <p><b>路径穿越防护</b>：key 拼接后必须仍位于 root 之内 ——
 * 即使 key 生成逻辑被改坏，也不能写到 root 之外。
 */
@Component
public class LocalDiskStorage implements StorageBackend {

    private final Path root;

    public LocalDiskStorage(@Value("${app.storage.local-root:./data/files}") String rootDir) {
        this.root = Paths.get(rootDir).toAbsolutePath().normalize();
        try {
            Files.createDirectories(this.root);
        } catch (IOException e) {
            throw new IllegalStateException("无法创建存储根目录: " + this.root, e);
        }
    }

    /** 解析并校验 key 不逃出 root（防 ../ 穿越）。 */
    private Path resolve(String key) {
        if (key == null || key.isBlank()) {
            throw new IllegalArgumentException("storage key 不能为空");
        }
        Path target = root.resolve(key).normalize();
        if (!target.startsWith(root)) {
            throw new IllegalArgumentException("storage key 越界（禁止逃出存储根目录）: " + key);
        }
        return target;
    }

    @Override
    public String put(String key, byte[] content) {
        Path target = resolve(key);
        try {
            Files.createDirectories(target.getParent());
            Files.write(target, content);
            return key;
        } catch (IOException e) {
            throw new IllegalStateException("写入存储失败: " + key, e);
        }
    }

    @Override
    public byte[] get(String key) {
        Path target = resolve(key);
        if (!Files.isRegularFile(target)) {
            throw new StorageObjectNotFoundException("存储对象不存在: " + key);
        }
        try {
            return Files.readAllBytes(target);
        } catch (IOException e) {
            throw new IllegalStateException("读取存储失败: " + key, e);
        }
    }

    @Override
    public boolean exists(String key) {
        return Files.isRegularFile(resolve(key));
    }

    @Override
    public void delete(String key) {
        try {
            Files.deleteIfExists(resolve(key));
        } catch (IOException e) {
            throw new IllegalStateException("删除存储对象失败: " + key, e);
        }
    }

    /** 供诊断/测试查看实际根目录。 */
    public Path rootPath() {
        return root;
    }
}
