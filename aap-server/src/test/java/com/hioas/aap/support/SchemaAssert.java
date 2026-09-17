package com.hioas.aap.support;

import com.networknt.schema.InputFormat;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * 契约断言：用 {@code docs/backend/json-schema/**} 里的 JSON Schema 校验**真实响应体文本**。
 *
 * <p>这是「接口模型驱动开发」的落地手段：文档里的模型不是装饰，而是测试断言的真源。
 * 一旦实现偷偷改名/去字段/换类型，契约测试先红。
 *
 * <p>注意：校验器（networknt）内部基于 Jackson 2，服务端序列化用的是 Spring Boot 4 的 Jackson 3
 * （{@code tools.jackson}）——这里直接传 JSON 文本，两个世界不交叉。
 */
public final class SchemaAssert {

    private static final Path SCHEMA_ROOT = Path.of("..", "docs", "backend", "json-schema");
    private static final JsonSchemaFactory FACTORY =
            JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012);

    private SchemaAssert() {
    }

    /** 校验 JSON 文本符合 {@code <group>/<name>.schema.json}。 */
    public static void assertMatches(String group, String name, String json) {
        Path file = SCHEMA_ROOT.resolve(group).resolve(name + ".schema.json");
        if (!Files.exists(file)) {
            throw new IllegalStateException("契约模型缺失: " + file.toAbsolutePath());
        }
        JsonSchema schema;
        try {
            // ★ 必须用**文件 URI**装载：模型之间用相对 $ref（如 "model-entry.schema.json"），
            //   只有拿到文档的绝对基准 URI 才能解析；用 InputStream 装载会报
            //   "URI is not absolute"（实测）。
            schema = FACTORY.getSchema(file.toAbsolutePath().normalize().toUri());
        } catch (Exception e) {
            throw new IllegalStateException("契约模型读取失败: " + file, e);
        }
        Set<ValidationMessage> errors = schema.validate(json, InputFormat.JSON);
        if (!errors.isEmpty()) {
            String detail = errors.stream().map(ValidationMessage::getMessage).collect(Collectors.joining("\n  "));
            throw new AssertionError("响应不符合契约 " + group + "/" + name + ":\n  " + detail + "\n响应体: " + json);
        }
    }

    /** 校验响应包体（envelope 层）。 */
    public static void assertEnvelope(String json) {
        assertMatches("common", "envelope", json);
    }

    /** 校验错误响应（code != 0）。 */
    public static void assertError(String json) {
        assertMatches("common", "error", json);
    }

    /** 校验分页响应。 */
    public static void assertPageMeta(String json) {
        assertMatches("common", "page", json);
    }

    /** 校验 data 段（model 名对应 {@code models/<name>.schema.json}）。 */
    public static void assertModel(String name, String json) {
        assertMatches("models", name, json);
    }
}
