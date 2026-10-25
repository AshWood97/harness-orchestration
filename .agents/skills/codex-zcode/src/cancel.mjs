const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

/** Retry only upstream 1.2.7's early Windows identity-snapshot failure. */
export async function cancelTask(manager, store, taskId, { platform = process.platform, waitMs = 5000 } = {}) {
  try {
    return await manager.cancelTask(taskId);
  } catch (error) {
    if (platform !== "win32" || error?.code !== "CANCEL_FAILED" ||
        !error.message.includes("process_tree_root_identity_required")) throw error;
    // The first call already recorded cancellation intent and a cleanup latch.
    // Only worker-persisted, same-attempt identities can authorize the retry;
    // never establish trust from a newly observed PID or remove that latch.
    const attempt = store.readStatus(taskId).attempt;
    const deadline = Date.now() + waitMs;
    while (Date.now() < deadline) {
      const status = store.readStatus(taskId);
      if (status.attempt !== attempt) throw error;
      const identity = store.readExecutorIdentity(taskId, attempt);
      if (identity?.worker?.fingerprint && (!status.zcode_pid || identity?.runtime?.fingerprint)) {
        // Core re-probes identities and verifies the process tree itself.
        return await manager.cancelTask(taskId);
      }
      await delay(50);
    }
    throw error;
  }
}
