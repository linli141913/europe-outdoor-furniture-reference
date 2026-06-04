const {
  HIDDEN_META_KEY,
  HIDDEN_SET_KEY,
  cleanId,
  cleanString,
  errorPayload,
  handleOptions,
  readJsonBody,
  redisCommand,
  sendJson,
} = require("./_redis");

module.exports = async function handler(req, res) {
  if (handleOptions(req, res)) return;
  if (req.method !== "POST") {
    sendJson(res, 405, { ok: false, error: "method_not_allowed" });
    return;
  }

  try {
    const body = await readJsonBody(req);
    const id = cleanId(body.id);
    if (!id) {
      sendJson(res, 400, { ok: false, error: "missing_id" });
      return;
    }

    const record = {
      id,
      title: cleanString(body.title, 300),
      source: cleanString(body.source, 200),
      category: cleanString(body.category, 200),
      thumb_url: cleanString(body.thumb_url, 1000),
      product_url: cleanString(body.product_url, 1000),
      image_url: cleanString(body.image_url, 1000),
      page_url: cleanString(body.page_url, 1000),
      deleted_at: new Date().toISOString(),
      user_agent: cleanString(req.headers["user-agent"], 500),
    };

    await redisCommand(["SADD", HIDDEN_SET_KEY, id]);
    await redisCommand(["HSET", HIDDEN_META_KEY, id, JSON.stringify(record)]);

    sendJson(res, 200, {
      ok: true,
      id,
      record,
    });
  } catch (error) {
    sendJson(res, 500, errorPayload(error));
  }
};
