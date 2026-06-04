const {
  HIDDEN_META_KEY,
  HIDDEN_SET_KEY,
  errorPayload,
  handleOptions,
  parseRecord,
  parseRedisHash,
  redisCommand,
  sendJson,
} = require("./_redis");

module.exports = async function handler(req, res) {
  if (handleOptions(req, res)) return;
  if (req.method !== "GET") {
    sendJson(res, 405, { ok: false, error: "method_not_allowed" });
    return;
  }

  try {
    const ids = (await redisCommand(["SMEMBERS", HIDDEN_SET_KEY])) || [];
    const meta = parseRedisHash(await redisCommand(["HGETALL", HIDDEN_META_KEY]));
    const sortedIds = ids.map(String).sort();
    const records = sortedIds.map((id) => parseRecord(id, meta[id]));

    sendJson(res, 200, {
      ok: true,
      count: sortedIds.length,
      ids: sortedIds,
      records,
    });
  } catch (error) {
    sendJson(res, 500, errorPayload(error));
  }
};
