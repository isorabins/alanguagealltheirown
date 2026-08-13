module.exports = async (_req, res) => {
  res.status(404).json({
    error: "Try It is unavailable for this release.",
    code: "try_it_disabled",
  });
};
