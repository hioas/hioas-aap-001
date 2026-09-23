package com.hioas.aap.coverage;

import static org.assertj.core.api.Assertions.assertThat;

import com.hioas.aap.support.ApiTestBase;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.method.HandlerMethod;
import org.springframework.web.servlet.mvc.method.RequestMappingInfo;
import org.springframework.web.servlet.mvc.method.annotation.RequestMappingHandlerMapping;

/**
 * 全接口覆盖测试 —— 真源 `docs/backend/endpoints.json`（由 `tools/gen-backend-models.py` 从冻结清单 PATHS 生成，90 条）。
 *
 * <p><b>为什么用「路由注册表」而不是 HTTP 探测</b>：认证/鉴权发生在 **路由匹配之前**，
 * 未认证访问不存在的 `/api/**` 同样会返回 401 信封，于是「受保护但未实现」的路由会被误判成已实现
 * （本测试前两版都踩了这个假绿）。改为直接读 Spring 的 {@link RequestMappingHandlerMapping}，
 * 得到进程内**真实注册**的 (方法, 路径) 集合，与清单做集合比对——精确、与票据无关。
 *
 * <p>产出 `.agents/state/evidence/coverage-report.json`：总数 / 已实现 / 缺失（按任务分组）+ 缺失明细，
 * 供定时任务反复取证，追踪「90 条接口还剩多少没落地」。
 */
class EndpointCoverageTest extends ApiTestBase {

    @Autowired
    @org.springframework.beans.factory.annotation.Qualifier("requestMappingHandlerMapping")
    private RequestMappingHandlerMapping handlerMapping;

    /** 路径变量名归一：`/quotes/{quoteId}` 与 `/quotes/{id}` 视为同一路由。 */
    private static String normalize(String path) {
        return path.replaceAll("\\{[^}]+\\}", "{}");
    }

    private record Endpoint(String id, String method, String path, String tag, String task) {
    }

    private static List<Endpoint> loadManifest() throws Exception {
        Path manifest = Path.of("..", "docs", "backend", "endpoints.json");
        assertThat(Files.exists(manifest))
                .as("清单缺失：%s（先跑 python tools/gen-backend-models.py）", manifest.toAbsolutePath())
                .isTrue();
        var root = MAPPER.readTree(Files.readString(manifest, StandardCharsets.UTF_8));
        List<Endpoint> endpoints = new ArrayList<>();
        for (var node : root.path("endpoints")) {
            endpoints.add(new Endpoint(node.path("id").asText(), node.path("method").asText(),
                    node.path("path").asText(), node.path("tag").asText(), node.path("task").asText()));
        }
        return endpoints;
    }

    /** 进程中真实注册的 (METHOD 归一路径) 集合。 */
    private Set<String> registeredRoutes() {
        Set<String> routes = new TreeSet<>();
        for (Map.Entry<RequestMappingInfo, HandlerMethod> entry : handlerMapping.getHandlerMethods().entrySet()) {
            Set<String> patterns = new TreeSet<>();
            var info = entry.getKey();
            if (info.getPathPatternsCondition() != null) {
                info.getPathPatternsCondition().getPatterns().forEach(p -> patterns.add(p.getPatternString()));
            } else if (info.getPatternsCondition() != null) {
                patterns.addAll(info.getPatternsCondition().getPatterns());
            }
            Set<org.springframework.web.bind.annotation.RequestMethod> methods =
                    info.getMethodsCondition().getMethods();
            for (String pattern : patterns) {
                if (!pattern.startsWith("/api/")) {
                    continue;   // 只比对业务接口（actuator 等不在清单里）
                }
                if (methods.isEmpty()) {
                    routes.add("ANY " + normalize(pattern));
                } else {
                    methods.forEach(m -> routes.add(m.name() + " " + normalize(pattern)));
                }
            }
        }
        return routes;
    }

    @Test
    @DisplayName("接口覆盖：冻结清单 93 条必须全部已注册（缺失即红，明细落 coverage-report.json）")
    void everyListedEndpointIsRegistered() throws Exception {
        List<Endpoint> endpoints = loadManifest();
        assertThat(endpoints).as("清单接口数与冻结清单(93)不一致").hasSize(93);

        Set<String> registered = registeredRoutes();
        List<Map<String, Object>> missing = new ArrayList<>();
        Map<String, int[]> byTask = new TreeMap<>();
        int implemented = 0;
        for (Endpoint endpoint : endpoints) {
            String key = endpoint.method().toUpperCase() + " " + normalize(endpoint.path());
            boolean ok = registered.contains(key) || registered.contains("ANY " + normalize(endpoint.path()));
            int[] counter = byTask.computeIfAbsent(endpoint.task(), k -> new int[2]);
            counter[1]++;
            if (ok) {
                implemented++;
                counter[0]++;
            } else {
                Map<String, Object> row = new LinkedHashMap<>();
                row.put("id", endpoint.id());
                row.put("task", endpoint.task());
                row.put("method", endpoint.method());
                row.put("path", endpoint.path());
                missing.add(row);
            }
        }

        Map<String, Object> report = new LinkedHashMap<>();
        report.put("total", endpoints.size());
        report.put("implemented", implemented);
        report.put("missing", missing.size());
        Map<String, Object> byTaskOut = new TreeMap<>();
        byTask.forEach((task, counter) -> byTaskOut.put(task,
                Map.of("implemented", counter[0], "total", counter[1])));
        report.put("by_task", byTaskOut);
        report.put("registered_routes", registered.size());
        report.put("not_registered", missing);
        Path out = Path.of("..", ".agents", "state", "evidence", "coverage-report.json");
        Files.createDirectories(out.getParent());
        Files.writeString(out, MAPPER.writerWithDefaultPrettyPrinter().writeValueAsString(report),
                StandardCharsets.UTF_8);

        System.out.println("=== 接口覆盖（真源 docs/backend/endpoints.json · 进程内路由注册表比对） ===");
        System.out.println("清单 " + endpoints.size() + " 条 · 已注册 " + implemented
                + " · 未注册 " + missing.size() + " · 进程内业务路由 " + registered.size() + " 条");
        byTask.forEach((task, counter) -> System.out.printf("  %-4s %2d/%-2d%n", task, counter[0], counter[1]));
        if (!missing.isEmpty()) {
            System.out.println("--- 未注册明细（按任务） ---");
            missing.forEach(m -> System.out.printf("  %-10s %-6s %s%n", m.get("id"), m.get("method"), m.get("path")));
        }

        assertThat(missing)
                .as("以下接口在冻结清单中但未注册（明细见 .agents/state/evidence/coverage-report.json）")
                .isEmpty();
    }
}
