const C = require('./_collaboration.js');

module.exports = async (req, res) => {
  try {
    if (process.env.VERCEL_ENV !== 'preview') {
      res.status(404).json({error: 'not found', code: 'not_found'}); return;
    }
    if (req.method !== 'POST') {
      res.status(405).json({error: 'POST only', code: 'method_not_allowed'}); return;
    }
    C.requireJson(req);
    await C.requireSession(req);
    let cursor = '0'; const keys = [];
    do {
      const page = await C.command('SCAN', cursor, 'MATCH', `${C.NAMESPACE}:*`, 'COUNT', 100);
      cursor = String(page[0]); keys.push(...(page[1] || []));
    } while (cursor !== '0');
    if (keys.length) await C.command('DEL', ...keys);
    res.status(200).json({namespace: `${C.NAMESPACE}:*`, deletedKeys: keys.length, remainingKeys: 0});
  } catch (error) { C.fail(res, error); }
};
