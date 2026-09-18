import { defineConfig, loadEnv } from "vite";
import uni from "@dcloudio/vite-plugin-uni";

// H5 联调假后端（仅 dev server 生效，不进产物）：
// aap-server 未就绪时，/api/v1/auth/* 会 404，可在 dev server 层拦截返回固定响应。
// 短信验证码固定 123456；任意合法手机号 + 非空图形验证码即可「发送」，登录返回固定 token。
//
// ⚠️ 2026-09-18 起**默认关闭**：aap-server 已实现真实登录链路（T03 AUTH-01…06），
//    dev 默认走真实后端（下面 server.proxy 把 /api 反代到 aap-server:8084）。
//    需要脱机跑页面（后端没起）时再打开：`VITE_DEV_AUTH_MOCK=true npm run dev:h5`。
const DEV_SMS_CODE = "123456";

function devAuthMock() {
  const reply = (res: any, body: unknown) => {
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(JSON.stringify({ code: "0", message: "ok", data: body }));
  };
  const reject = (res: any, code: string, message: string) => {
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(JSON.stringify({ code, message, data: {} }));
  };

  return {
    name: "dev-auth-mock",
    configureServer(server: any) {
      server.middlewares.use("/api/v1/auth", (req: any, res: any, next: any) => {
        const readBody = (onDone: (data: Record<string, unknown>) => void) => {
          let raw = "";
          req.on("data", (chunk: Buffer) => (raw += chunk));
          req.on("end", () => {
            try {
              onDone(JSON.parse(raw || "{}"));
            } catch {
              onDone({});
            }
          });
        };

        if (req.method === "POST" && req.url === "/sms/send") {
          reply(res, { ttl: 300 });
          return;
        }
        if (req.method === "POST" && req.url === "/sms/login") {
          readBody((body) => {
            const smsCode = String(body.smsCode ?? "");
            if (smsCode !== DEV_SMS_CODE) {
              reject(res, "E-1002", `短信验证码错误（联调固定 ${DEV_SMS_CODE}）`);
            } else {
              reply(res, {
                token: "dev-jwt",
                role: "PROVIDER",
                providerId: "AAP-P-000001",
              });
            }
          });
          return;
        }
        next();
      });
    },
  };
}

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiTarget = env.VITE_API_TARGET || "http://127.0.0.1:8084";
  const useAuthMock = env.VITE_DEV_AUTH_MOCK === "true";

  return {
    // 真实后端优先：未显式开启 mock 时，才挂 dev-auth-mock 插件
    plugins: useAuthMock ? [uni(), devAuthMock()] : [uni()],
    server: {
      port: Number(env.VITE_DEV_PORT || 5173),
      // 监听排除：.mp-e2e-full-sandbox 是其他 e2e 套件复制出来的沙箱目录，
      // 其中的文件会被外部进程短暂锁定（Windows 下表现为 EBUSY: resource busy or locked,
      // watch '...\.mp-e2e-full-sandbox\api\http.js'），会让 dev server 直接崩溃退出。
      // 该目录不参与前端构建，直接不监听即可（不删除它 —— 可能正被别的套件使用）。
      watch: {
        ignored: ["**/.mp-e2e-full-sandbox/**", "**/dist/**"],
      },
      // 前端与 aap-server 不同源 → 由 dev server 反代，浏览器侧同源、无 CORS 问题。
      // 这是「浏览器走真实主链路」的前提：uni.request 用的相对路径 /api/v1 会被代理到后端。
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
