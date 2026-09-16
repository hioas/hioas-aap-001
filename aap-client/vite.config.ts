import { defineConfig } from "vite";
import uni from "@dcloudio/vite-plugin-uni";

// H5 联调假后端（仅 dev server 生效，不进产物）：
// aap-server 尚未实现，/api/v1/auth/* 会 404，这里在 dev server 层拦截返回固定响应。
// 短信验证码固定 123456；任意合法手机号 + 非空图形验证码即可「发送」，登录返回固定 token。
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
export default defineConfig({
  plugins: [uni(), devAuthMock()],
});
