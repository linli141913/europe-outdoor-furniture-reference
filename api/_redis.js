const HIDDEN_SET_KEY = process.env.GALLERY_HIDDEN_SET_KEY || "gallery:hidden_ids";
const HIDDEN_META_KEY = process.env.GALLERY_HIDDEN_META_KEY || "gallery:hidden_meta";

function sendJson(res, status, payload) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type,Authorization");
  res.status(status).json(payload);
}

function handleOptions(req, res) {
  if (req.method !== "OPTIONS") return false;
  sendJson(res, 200, { ok: true });
  return true;
}

async function readJsonBody(req) {
  if (Buffer.isBuffer(req.body)) {
    try {
      return JSON.parse(req.body.toString("utf8") || "{}");
    } catch (error) {
      return {};
    }
  }
  if (req.body && typeof req.body === "object") return req.body;
  if (typeof req.body === "string") {
    try {
      return JSON.parse(req.body || "{}");
    } catch (error) {
      return {};
    }
  }

  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  if (!chunks.length) return {};

  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
  } catch (error) {
    return {};
  }
}

function cleanString(value, maxLength = 1000) {
  return String(value || "").trim().slice(0, maxLength);
}

function cleanId(value) {
  const id = cleanString(value, 180);
  if (!id || !/^[a-z0-9][a-z0-9._-]*$/i.test(id)) return "";
  return id;
}

async function redisCommand(command) {
  const url = process.env.UPSTASH_REDIS_REST_URL || process.env.KV_REST_API_URL;
  const token = process.env.UPSTASH_REDIS_REST_TOKEN || process.env.KV_REST_API_TOKEN;
  if (!url || !token) {
    const error = new Error("Missing KV_REST_API_URL/KV_REST_API_TOKEN or UPSTASH_REDIS_REST_URL/UPSTASH_REDIS_REST_TOKEN");
    error.code = "upstash_not_configured";
    throw error;
  }

  const response = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(command),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || payload.error) {
    const error = new Error(payload.error || `Redis command failed with ${response.status}`);
    error.code = "redis_error";
    throw error;
  }
  return payload.result;
}

function parseRedisHash(value) {
  if (!value) return {};
  if (!Array.isArray(value) && typeof value === "object") return value;
  if (!Array.isArray(value)) return {};

  const output = {};
  for (let index = 0; index < value.length; index += 2) {
    const key = value[index];
    if (!key) continue;
    output[String(key)] = value[index + 1];
  }
  return output;
}

function parseRecord(id, raw) {
  if (!raw) return { id };
  if (typeof raw === "object") return { id, ...raw };
  try {
    const parsed = JSON.parse(raw);
    return { id, ...parsed };
  } catch (error) {
    return { id, note: String(raw) };
  }
}

function errorPayload(error) {
  return {
    ok: false,
    error: error.code || "server_error",
    message: error.message || String(error),
  };
}

module.exports = {
  HIDDEN_META_KEY,
  HIDDEN_SET_KEY,
  cleanId,
  cleanString,
  errorPayload,
  handleOptions,
  parseRecord,
  parseRedisHash,
  readJsonBody,
  redisCommand,
  sendJson,
};
