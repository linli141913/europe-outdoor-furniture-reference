const {
  HIDDEN_META_KEY,
  HIDDEN_SET_KEY,
  cleanId,
  errorPayload,
  handleOptions,
  readJsonBody,
  redisCommand,
  sendJson,
} = require("./_redis");

function isAuthorized(req, body) {
  const token = process.env.GALLERY_ADMIN_TOKEN;
  if (!token) return true;

  const header = req.headers.authorization || "";
  const bearer = header.startsWith("Bearer ") ? header.slice(7).trim() : "";
  const queryToken = req.query && req.query.token ? String(req.query.token) : "";
  const bodyToken = body && body.token ? String(body.token) : "";
  return bearer === token || queryToken === token || bodyToken === token;
}

module.exports = async function handler(req, res) {
  if (handleOptions(req, res)) return;
  if (req.method !== "POST") {
    sendJson(res, 405, { ok: false, error: "method_not_allowed" });
    return;
  }

  try {
    const body = await readJsonBody(req);
    if (!isAuthorized(req, body)) {
      sendJson(res, 401, { ok: false, error: "unauthorized" });
      return;
    }

    const id = cleanId(body.id);
    if (!id) {
      sendJson(res, 400, { ok: false, error: "missing_id" });
      return;
    }

    await redisCommand(["SREM", HIDDEN_SET_KEY, id]);
    await redisCommand(["HDEL", HIDDEN_META_KEY, id]);

    sendJson(res, 200, {
      ok: true,
      id,
      restored: true,
    });
  } catch (error) {
    sendJson(res, 500, errorPayload(error));
  }
};
